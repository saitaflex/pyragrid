"""security.py — rate limiting, security headers, request ids and error containment.

Threat model for this service: a public HTTPS API, bearer-token auth, no cookies, one
Postgres database shared by every tenant. What we defend against here, in order of how
likely it is to actually happen:

1. **Credential stuffing on /auth/login.** The demo accounts are published in the README, so
   the interesting target is a real customer's account. Answer: a strict per-IP and
   per-account limit, plus constant-time login in `auth.py` so unknown accounts cannot be
   told apart from real ones by response time.
2. **Cost exhaustion on /advisor.** Every call spends money at Groq. An unauthenticated
   attacker cannot reach it, but a logged-in tenant could run the bill up by accident or on
   purpose. Answer: a much tighter limit on that route class than on reads.
3. **Cross-tenant data access.** Every query is scoped by `customer_id` from the token and
   every company endpoint refuses partner roles; `tests/test_auth_tenancy.py` covers it.
4. **Response-based information leakage.** Unhandled exceptions must not return internals.
   Answer: one handler that logs with a request id and returns that id, nothing else.

**Honest limit of the rate limiter:** it is in-process. On Vercel each function instance has
its own counters, so the effective limit is (limit x instances). It is a real speed bump
against a single attacker on a single connection, and it is not a distributed rate limit.
Doing this properly needs Redis or Vercel's own firewall; `docs/SECURITY.md` says so and
names the upgrade. Nothing here is presented as more than it is.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from collections import deque

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

log = logging.getLogger("pyragrid.security")

# Requests allowed per window, per client, by route class. Reads are generous because the
# console makes many of them per page; writes and paid calls are not.
LIMITS: dict[str, tuple[int, int]] = {
    "auth": (10, 60),        # 10 login attempts a minute per IP
    "expensive": (15, 60),   # advisor generation and drill creation: these cost money
    "write": (60, 60),
    "read": (240, 60),
}
MAX_BODY_BYTES = 1 * 1024 * 1024   # 1 MiB: the largest legitimate request is a CSV import


def classify(method: str, path: str) -> str:
    if "/auth/login" in path:
        return "auth"
    if "/advisor/incidents/" in path and method == "POST":
        return "expensive"
    if path.endswith("/drills") and method == "POST":
        return "expensive"
    return "read" if method in ("GET", "HEAD", "OPTIONS") else "write"


def client_ip(request: Request) -> str:
    """The caller's address behind Vercel's proxy.

    `x-forwarded-for` is attacker-controllable except for the entries the platform itself
    appends, so we prefer `x-real-ip`, which Vercel sets, and fall back to the *last* hop of
    the forwarded chain rather than the first: the first entry is whatever the client claimed.
    """
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        parts = [p.strip() for p in fwd.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return request.client.host if request.client else "unknown"


class SlidingWindow:
    """Per-key request timestamps, trimmed to the window. Bounded: keys are dropped once
    their window empties, so a flood of distinct IPs cannot grow this without limit."""

    def __init__(self, max_keys: int = 8192) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def check(self, key: str, limit: int, window_s: int) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > self._max_keys:
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] > window_s]:
                    self._hits.pop(k, None)
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] > window_s:
                q.popleft()
            if len(q) >= limit:
                return False, int(window_s - (now - q[0])) + 1
            q.append(now)
            if not q:
                self._hits.pop(key, None)
            return True, 0


_window = SlidingWindow()


def check_rate(request: Request) -> None:
    """Raise 429 with Retry-After when the caller is over the limit for this route class."""
    cls = classify(request.method, request.url.path)
    limit, window_s = LIMITS[cls]
    ok, retry = _window.check(f"{cls}:{client_ip(request)}", limit, window_s)
    if not ok:
        raise HTTPException(status_code=429, detail="too many requests",
                            headers={"Retry-After": str(retry)})


def login_guard(email: str, ip: str) -> None:
    """A second, per-account limit so one attacker cannot spread attempts across IPs, nor
    lock a victim out by hammering their account from one IP."""
    ok, retry = _window.check(f"login-account:{email.lower()}", 10, 300)
    if not ok:
        raise HTTPException(status_code=429, detail="too many attempts for this account",
                            headers={"Retry-After": str(retry)})


SECURITY_HEADERS = {
    # the API serves JSON only; never let a browser sniff it into something executable
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # the console is a separate static deployment; the API itself needs no scripts at all
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    # nothing this API returns should ever be cached by a shared proxy: it is all tenant data
    "Cache-Control": "no-store",
}


def install(app) -> None:
    """Wire the middleware and handlers onto the FastAPI app."""

    @app.middleware("http")
    async def _security_mw(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]

        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "request body too large", "request_id": rid},
                                status_code=413)
        try:
            check_rate(request)
        except HTTPException as e:
            return JSONResponse({"detail": e.detail, "request_id": rid},
                                status_code=e.status_code, headers=e.headers)

        try:
            response = await call_next(request)
        except HTTPException:
            raise
        except Exception:
            # log the detail, return only the id: an error message is an information leak
            log.exception("unhandled error rid=%s %s %s", rid, request.method,
                          request.url.path)
            return JSONResponse(
                {"detail": "internal error", "request_id": rid}, status_code=500,
                headers={**SECURITY_HEADERS, "X-Request-Id": rid})

        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        response.headers["X-Request-Id"] = rid
        return response


def allowed_origins() -> list[str]:
    """CORS origins from ALLOWED_ORIGINS (comma-separated).

    Unset means "*", which is safe only because this API uses bearer tokens and never
    cookies, so a hostile page cannot ride a browser session. Production should still pin it;
    a warning is logged when it is not set so the gap is visible in the logs.
    """
    raw = os.environ.get("ALLOWED_ORIGINS", "").strip()
    if not raw:
        if os.environ.get("VERCEL_ENV") == "production":
            log.warning("ALLOWED_ORIGINS is not set in production; allowing all origins")
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]
