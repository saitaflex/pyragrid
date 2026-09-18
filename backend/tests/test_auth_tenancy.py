"""test_auth_tenancy.py — auth and tenant isolation (TEAM_PLAN.md §5.12 T1-M4)."""
from tests.conftest import auth


def test_wrong_password_401(client):
    r = client.post("/api/auth/login", json={"email": "admin@demo.eu", "password": "nope"})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid credentials"


def test_no_token_and_garbage_token_401(client):
    assert client.get("/api/sites").status_code == 401
    r = client.get("/api/sites", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


def test_operator_import_forbidden(client):
    files = {"file": ("a.csv", b"header\n", "text/csv")}
    r = client.post("/api/assets/import", files=files, headers=auth(client, email="operator@demo.eu"))
    assert r.status_code == 403
    assert r.json()["detail"] == "forbidden"


def test_tenant_isolation(client):
    h = auth(client, email="other@othercorp.eu")
    sites = client.get("/api/sites", headers=h).json()
    assert [s["site_id"] for s in sites] == ["OC-001"]
    assert client.get("/api/sites/ES-OU-001/status", headers=h).status_code == 404


def test_audit_records_login(client):
    r = client.get("/api/audit", headers=auth(client))
    actions = {e["action"] for e in r.json()}
    assert "login" in actions
