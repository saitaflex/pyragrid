"""test_security.py — the guarantees in app/security.py, asserted rather than claimed.

Each test names the attack it blocks. If one of these fails, a real hole has opened.
"""
import time

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_mod
from app import security
from app.main import app
from tests.conftest import auth


def test_security_headers_on_every_response(client):
    r = client.get("/api/health")
    for header, expected in [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Cache-Control", "no-store"),           # tenant data must never sit in a shared cache
    ]:
        assert r.headers.get(header) == expected
    assert "default-src 'none'" in r.headers.get("Content-Security-Policy", "")
    assert r.headers.get("X-Request-Id")


def test_login_is_rate_limited(client):
    """Credential stuffing: the 11th attempt in a minute is refused, with Retry-After."""
    codes = [client.post("/api/auth/login",
                         json={"email": "nobody@demo.eu", "password": "wrong"}).status_code
             for _ in range(12)]
    assert codes.count(401) == 10
    assert codes[-1] == 429
    r = client.post("/api/auth/login", json={"email": "nobody@demo.eu", "password": "wrong"})
    assert r.headers.get("Retry-After")


def test_unknown_account_costs_the_same_as_a_real_one(client):
    """User enumeration by timing: a missing account must not answer faster than a real one
    with a wrong password, so both paths run the same PBKDF2 work."""
    def timed(email):
        t = time.perf_counter()
        client.post("/api/auth/login", json={"email": email, "password": "definitely-wrong"})
        return time.perf_counter() - t

    unknown = min(timed("no-such-user@demo.eu") for _ in range(3))
    known = min(timed("admin@demo.eu") for _ in range(3))
    # within 3x of each other: enough to catch a fast-path return, tolerant of CI jitter
    assert unknown > known / 3, f"unknown={unknown:.3f}s known={known:.3f}s"


def test_advisor_has_a_tighter_limit_than_reads():
    """Cost exhaustion: the paid endpoint must not share the generous read budget."""
    assert security.classify("POST", "/api/advisor/incidents/X") == "expensive"
    assert security.classify("GET", "/api/portfolio") == "read"
    assert security.LIMITS["expensive"][0] < security.LIMITS["read"][0]
    assert security.LIMITS["auth"][0] <= security.LIMITS["expensive"][0]


def test_oversized_body_is_refused(client):
    r = client.post("/api/auth/login", content=b"x" * 16,
                    headers={"Content-Length": str(security.MAX_BODY_BYTES + 1),
                             "Content-Type": "application/json"})
    assert r.status_code == 413


def test_forwarded_for_cannot_be_spoofed_to_dodge_the_limit():
    """x-forwarded-for is client-controllable, so the limiter must not key on the first hop:
    otherwise an attacker rotates that header and gets unlimited attempts."""
    class Req:
        def __init__(self, headers):
            self.headers = headers
            self.client = type("C", (), {"host": "10.0.0.1"})()

    assert security.client_ip(Req({"x-real-ip": "203.0.113.9"})) == "203.0.113.9"
    # last hop wins, because the client can prepend anything it likes
    assert security.client_ip(
        Req({"x-forwarded-for": "1.2.3.4, 203.0.113.9"})) == "203.0.113.9"
    assert security.client_ip(Req({})) == "10.0.0.1"


def test_token_pins_the_algorithm_and_requires_its_claims():
    """An `alg: none` token, or one missing the claims we authorise on, must be rejected."""
    import jwt

    good = auth_mod.make_token("admin@demo.eu", "demo", "admin")
    assert auth_mod.decode_token(good)["cid"] == "demo"

    unsigned = jwt.encode({"sub": "a@b.c", "cid": "demo", "role": "admin", "exp": 9e9},
                          key="", algorithm="none")
    with pytest.raises(jwt.PyJWTError):
        auth_mod.decode_token(unsigned)

    missing_cid = jwt.encode({"sub": "a@b.c", "role": "admin", "exp": 9999999999},
                             auth_mod._secret(), algorithm="HS256")
    with pytest.raises(jwt.PyJWTError):
        auth_mod.decode_token(missing_cid)


def test_production_refuses_a_missing_signing_secret(monkeypatch):
    """Signing with the published dev default would let anyone mint a token for any tenant,
    so a missing secret is fatal in production. A short one only warns: see auth.py."""
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET is not set"):
        auth_mod._secret()

    # a short but real secret warns rather than killing a running deployment
    monkeypatch.setenv("JWT_SECRET", "short")
    assert auth_mod._secret() == "short"

    monkeypatch.setenv("JWT_SECRET", "k" * 40)
    assert auth_mod._secret() == "k" * 40


def test_unhandled_errors_return_an_id_and_nothing_else(client, monkeypatch):
    """A stack trace or an exception message in a response body is an information leak."""
    def boom(*a, **k):
        raise ValueError("secret internal detail: postgres://user:password@host/db")

    monkeypatch.setattr("app.routes.risk.service.portfolio", boom)
    r = client.get("/api/portfolio", headers=auth(client))
    assert r.status_code == 500
    body = r.text
    assert "postgres://" not in body and "secret internal detail" not in body
    assert r.json()["detail"] == "internal error"
    assert r.json()["request_id"]


def test_partner_roles_cannot_read_company_data(client):
    """Cross-role leakage: asset values must never reach a partner account."""
    tok = client.post("/api/auth/login",
                      json={"email": "fire@demo.eu", "password": "demo1234"}).json()
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    for path in ("/api/portfolio", "/api/sites", "/api/replay/summary",
                 "/api/sites/TN-JN-001/forecast", "/api/sites/TN-JN-001/status",
                 "/api/sites/TN-JN-001/timeline", "/api/sites/TN-JN-001/weather/live",
                 "/api/alerts"):
        assert client.get(path, headers=h).status_code == 403, path

    # Deliberately allowed: raw satellite detections are public NASA FIRMS data with no site,
    # asset or personnel information in them, and a partner's whole job is to see the fire.
    # Locking this would break the partner situation view. See docs/SECURITY.md.
    pub = client.get("/api/detections", headers=h)
    assert pub.status_code == 200
    assert all(set(d) <= {"id", "source", "external_id", "lat", "lon", "observed_at",
                          "received_at", "satellite", "confidence", "intensity_frp"}
               for d in pub.json()[:5]), "a detection must never carry site or asset fields"
