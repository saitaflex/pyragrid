"""test_simulate.py — AI response plan for the "fire reported now" simulator."""
from app.advisor import TACTICS
from tests.conftest import auth

BODY = {
    "site_id": "ES-OU-001",
    "conditions": {"wind_kmh": 35, "wind_from_deg": 225, "temp_c": 38, "rh_pct": 14,
                   "fuel": "very_high", "ignition_km": 4.0, "ignition_bearing_deg": 225},
    "state": {"minutes": 90, "level": "CRITICAL", "front_km": 0.8, "eta_min": 25,
              "head_ros_m_min": 32, "burned_ha": 310, "fire_moving_toward_site": True,
              "sensors_fire": 2, "sensors_warm": 3, "sensors_offline": 1},
}


def test_plan_is_grounded_and_urgent_first(client, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = client.post("/api/simulate/advice", json=BODY, headers=auth(client, email="operator@demo.eu"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["generated_by"] == "template" and d["suggestions"]
    first = d["suggestions"][0]
    assert first["priority"] == 1 and "sim:eta" in first["evidence"]
    assert "25 min" in first["detail"]
    assert d["access_routes"]["Primary access"] in ("available", "potentially_exposed")
    assert d["protocol_actions"]                       # CRITICAL rules matched
    for s in d["suggestions"]:
        assert set(s["evidence"]) <= set(d["evidence_keys"])
        assert not TACTICS.search(s["title"] + " " + s["detail"])


def test_route_facing_the_fire_is_exposed(client, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    h = auth(client)
    site = next(s for s in client.get("/api/sites", headers=h).json() if s["site_id"] == "ES-OU-001")
    body = {**BODY, "conditions": {**BODY["conditions"], "ignition_bearing_deg": site["primary_access_bearing_deg"]}}
    d = client.post("/api/simulate/advice", json=body, headers=h).json()
    assert d["access_routes"] == {"Primary access": "potentially_exposed", "Secondary access": "available"}


def test_simulation_is_staff_only_and_logged(client):
    assert client.post("/api/simulate/advice", json=BODY,
                       headers=auth(client, email="fire@demo.eu")).status_code == 403
    h = auth(client)
    r = client.post("/api/simulate/complete", headers=h, json={
        "site_id": "ES-OU-001", "summary": "front stopped 0.8 km out", "actions_done": ["a", "b"],
        "actions_total": 5, "duration_s": 240})
    assert r.status_code == 201
    audit = client.get("/api/audit", headers=h).json()
    assert any(e["action"] == "simulation_response" and "2/5 actions" in e["details"] for e in audit)
