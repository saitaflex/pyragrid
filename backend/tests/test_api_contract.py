"""test_api_contract.py — every endpoint, shapes, sorting, snapping (§5.12 T1-M5)."""
from app.models import (
    Alert, AuditEntry, Detection, Health, Incident, IngestionRun, OutboxEmail,
    Portfolio, ReplaySummary, Site, SiteStatus, SopRule, SourceStatus, TimelinePoint,
)
from app.sop import RANK
from tests.conftest import auth


def test_health(client):
    Health.model_validate(client.get("/api/health").json())


def test_portfolio_shape_and_sorting(client):
    r = client.get("/api/portfolio?at=2025-08-14T15:00:00Z", headers=auth(client))
    p = Portfolio.model_validate(r.json())
    assert len(p.sites) == 20
    keys = [(-RANK[s.level], -s.score, s.site_id) for s in p.sites]
    assert keys == sorted(keys)


def test_at_snapping_and_clamping(client):
    h = auth(client)
    snapped = client.get("/api/portfolio?at=2025-08-14T16:40:00Z", headers=h).json()["at"]
    assert snapped == "2025-08-14T15:00:00Z"
    high = client.get("/api/portfolio?at=2030-01-01T00:00:00Z", headers=h).json()["at"]
    assert high == "2025-08-25T21:00:00Z"
    low = client.get("/api/portfolio?at=2000-01-01T00:00:00Z", headers=h).json()["at"]
    assert low == "2025-08-08T00:00:00Z"


def test_sites_and_status(client):
    h = auth(client)
    sites = [Site.model_validate(s) for s in client.get("/api/sites", headers=h).json()]
    assert [s.site_id for s in sites] == sorted(s.site_id for s in sites)
    st = client.get("/api/sites/ES-OU-001/status?at=2025-08-14T15:00:00Z", headers=h)
    SiteStatus.model_validate(st.json())
    assert client.get("/api/sites/NOPE/status", headers=h).json()["detail"] == "site not found"


def test_timeline_has_144(client):
    r = client.get("/api/sites/ES-OU-001/timeline", headers=auth(client))
    pts = [TimelinePoint.model_validate(p) for p in r.json()]
    assert len(pts) == 144


def test_detections_and_summary(client):
    h = auth(client)
    for d in client.get("/api/detections?at=2025-08-14T15:00:00Z", headers=h).json():
        Detection.model_validate(d)
    ReplaySummary.model_validate(client.get("/api/replay/summary", headers=h).json())


def test_alerts_ack_idempotent(client):
    h_op = auth(client, email="operator@demo.eu")
    alerts = [Alert.model_validate(a) for a in
              client.get("/api/alerts?at=2025-08-20T00:00:00Z", headers=h_op).json()]
    assert alerts, "expected some alerts in the demo replay"
    aid = alerts[-1].alert_id  # oldest, definitely <= at
    first = client.post(f"/api/alerts/{aid}/acknowledge", headers=h_op).json()
    assert first["acknowledged_by"] == "operator@demo.eu"
    again = client.post(f"/api/alerts/{aid}/acknowledge", headers=auth(client)).json()
    assert again["acknowledged_by"] == "operator@demo.eu"  # first ack wins
    assert client.post("/api/alerts/NOPE/acknowledge", headers=h_op).json()["detail"] == "alert not found"


def test_incidents(client):
    h = auth(client)
    for inc in client.get("/api/incidents/history", headers=h).json():
        Incident.model_validate(inc)
    assert client.get("/api/incidents/NOPE_20250101T0000", headers=h).json()["detail"] \
        == "incident not found"


def test_sop_crud(client):
    h = auth(client)
    body = {"name": "Test rule", "enabled": True, "priority": 99,
            "conditions": {"min_level": "HIGH", "asset_types": [], "min_criticality": 1,
                           "wind_toward_site": None},
            "actions": ["Do the thing"]}
    created = client.post("/api/sop/rules", json=body, headers=h)
    assert created.status_code == 201
    rid = SopRule.model_validate(created.json()).rule_id
    body["name"] = "Edited"
    assert client.put(f"/api/sop/rules/{rid}", json=body, headers=h).json()["name"] == "Edited"
    assert client.put("/api/sop/rules/R-999", json=body, headers=h).json()["detail"] == "rule not found"
    assert client.delete(f"/api/sop/rules/{rid}", headers=h).status_code == 204


def test_system_endpoints(client):
    h = auth(client)
    sources = [SourceStatus.model_validate(s) for s in
               client.get("/api/status/sources", headers=h).json()]
    assert [s.name for s in sources] == ["FIRMS", "Weather", "Vegetation",
                                         "Notification", "Database", "AI Advisor"]
    for run in client.get("/api/ingestion/runs", headers=h).json():
        IngestionRun.model_validate(run)
    for m in client.get("/api/notifications/outbox?at=2025-08-20T00:00:00Z", headers=h).json():
        OutboxEmail.model_validate(m)
    for e in client.get("/api/audit", headers=h).json():
        AuditEntry.model_validate(e)
    # audit is admin-only
    assert client.get("/api/audit", headers=auth(client, email="operator@demo.eu")).status_code == 403
