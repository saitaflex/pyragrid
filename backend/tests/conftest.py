"""Shared fixtures: a fresh seeded SQLite DB and a TestClient per test."""
import pytest
from fastapi.testclient import TestClient

from app import db, security, state


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The rate limiter is process-global and stays ENABLED for every test, so the production
    path is the tested path. Each test just starts with a fresh budget instead of inheriting
    the previous test's requests."""
    security._window = security.SlidingWindow()
    yield
    security._window = security.SlidingWindow()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("ASSUMED_WEATHER", "true")
    db.configure(sqlite_path=str(tmp_path / "test.db"))
    db.get_db().seed_if_empty()
    state.clear()
    from app.main import app
    return TestClient(app)


def token(client, email="admin@demo.eu", password="demo1234"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(client, **kw):
    return {"Authorization": f"Bearer {token(client, **kw)}"}
