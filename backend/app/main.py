"""main.py — FastAPI app named `app` (Vercel entrypoint). TEAM_PLAN.md §5.9.

No startup work: every route calls ensure_ready() first (idempotent, guarded by a
lock, runs once per server instance).
"""
from __future__ import annotations

import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import security
from app.routes import (
    advisor, alerts, assets, auth, drills, risk, sensors, simulate, situation, sop, system,
)

app = FastAPI(title="Wildfire Asset Intelligence — Engine", version="2.1.0")

# CORS: origins from ALLOWED_ORIGINS, "*" when unset. Safe to be permissive only because
# auth is a bearer token and there are no cookies, so no hostile page can ride a session.
app.add_middleware(
    CORSMiddleware,
    allow_origins=security.allowed_origins(),
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
    allow_credentials=False,
    max_age=600,
)

# Rate limiting, security headers, request ids and error containment. See app/security.py
# for the threat model and for the honest limits of an in-process rate limiter.
security.install(app)

_ready_lock = threading.Lock()
_ready = False


def ensure_ready() -> None:
    """Create schema, seed and load data once per instance (§5.9). No-op for now."""
    global _ready
    if _ready:
        return
    with _ready_lock:
        if _ready:
            return
        from app.db import get_db
        get_db().seed_if_empty()  # schema is created on connect
        _ready = True


for _r in (system, auth, assets, risk, alerts, sop, advisor, sensors, situation, drills,
           simulate):
    app.include_router(_r.router, prefix="/api")


@app.middleware("http")
async def _ensure_ready_mw(request, call_next):
    ensure_ready()
    return await call_next(request)
