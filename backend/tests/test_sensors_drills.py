"""test_sensors_drills.py — ground-sensor mesh, partner sharing policy, training drills."""
from datetime import datetime, timedelta, timezone

from app import drills
from app.defaults import DEMO_SENSOR_SITES
from tests.conftest import auth

AT = "2025-08-20T00:00:00Z"


def test_sensor_mesh_is_hexagonal_and_seeded(client):
    r = client.get(f"/api/sensors?at={AT}", headers=auth(client))
    assert r.status_code == 200
    body = r.json()
    assert sorted(m["site_id"] for m in body["meshes"]) == sorted(DEMO_SENSOR_SITES)
    assert all(m["nodes"] == 37 for m in body["meshes"])
    node = body["nodes"][0]
    assert len(node["hex"]) == 7 and node["hex"][0] == node["hex"][-1]
    assert {n["state"] for n in body["nodes"]} <= {"ok", "warm", "fire", "offline", "dropped"}
    kinds = {e["kind"] for e in body["events"]}
    assert "fire" in kinds and "offline" in kinds   # fire reached meshes and destroyed nodes


def test_sensor_install_admin_only(client):
    op = auth(client, email="operator@demo.eu")
    assert client.post("/api/sensors/install", json={"site_id": "ES-OU-002"},
                       headers=op).status_code == 403
    h = auth(client)
    assert client.post("/api/sensors/install", json={"site_id": "ES-OU-002"},
                       headers=h).status_code == 201
    r = client.get(f"/api/sensors?at={AT}&site_id=ES-OU-002", headers=h).json()
    assert [m["site_id"] for m in r["meshes"]] == ["ES-OU-002"]
    assert client.delete("/api/sensors/install/ES-OU-002", headers=h).status_code == 204


def test_partner_views_are_filtered(client):
    fire = auth(client, email="fire@demo.eu")
    s = client.get(f"/api/situation?at={AT}", headers=fire).json()
    site = s["sites"][0]
    assert s["policy"]["role"] == "firefighter"
    assert site["value_eur"] is None and site["personnel_on_site"] is not None
    assert site["access_routes"] is not None
    assert client.get("/api/sites/ES-OU-001/handoff", headers=fire).status_code == 200

    ngo = auth(client, email="ngo@demo.eu")
    site = client.get(f"/api/situation?at={AT}", headers=ngo).json()["sites"][0]
    assert site["personnel_on_site"] is None and site["value_eur"] is None
    assert client.get("/api/sites/ES-OU-001/handoff", headers=ngo).status_code == 403

    gov = auth(client, email="gov@demo.eu")
    site = client.get(f"/api/situation?at={AT}", headers=gov).json()["sites"][0]
    assert site["access_routes"] is None and site["personnel_on_site"] is not None

    for h in (fire, ngo, gov):
        assert client.get(f"/api/portfolio?at={AT}", headers=h).status_code == 403
        assert client.get("/api/alerts", headers=h).status_code == 403
        assert client.get("/api/drills", headers=h).status_code == 403
        assert client.get(f"/api/sensors?at={AT}", headers=h).status_code == 200
        assert client.get(f"/api/detections?at={AT}", headers=h).status_code == 200

    admin = client.get(f"/api/situation?at={AT}", headers=auth(client)).json()
    assert admin["sites"][0]["value_eur"] is not None


class Clock:
    def __init__(self):
        self.t = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.t.strftime("%Y-%m-%dT%H:%M:%SZ")

    def add(self, s):
        self.t += timedelta(seconds=s)


def test_drill_flow_alerts_everyone_and_scores(client, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(drills, "now_iso", clock)
    admin = auth(client)
    staff = client.get("/api/staff", headers=admin).json()
    assert {u["email"] for u in staff} >= {"admin@demo.eu", "operator@demo.eu", "ana@demo.eu"}
    assert "fire@demo.eu" not in {u["email"] for u in staff}

    r = client.post("/api/drills", headers=admin,
                    json={"site_id": "ES-OU-001", "scenario": "approaching", "pace_s": 20})
    assert r.status_code == 201, r.text
    d = r.json()
    did = d["drill_id"]
    assert len(d["stages"]) == 1 and d["total_stages"] == 6 and d["level"] == "ELEVATED"
    assert len(d["notifications"]) == 2 * len(staff)
    assert d["expected_actions"]  # admin sees the answer key

    op = auth(client, email="operator@demo.eu")
    active = client.get("/api/drills/active", headers=op).json()
    assert [a["drill_id"] for a in active] == [did]
    assert active[0]["expected_actions"] is None   # hidden until they respond
    assert active[0]["responses"] == []            # cannot see colleagues

    clock.add(10)
    assert client.post(f"/api/drills/{did}/ack", headers=op).json()["my_response"]["ack_seconds"] == 10
    clock.add(55)                                  # 65 s: 4 signals revealed
    v = client.get(f"/api/drills/{did}", headers=op).json()
    assert len(v["stages"]) == 4 and v["level"] == "CRITICAL"
    assert any(n["state"] == "fire" for n in v["nodes"])
    expected = client.get(f"/api/drills/{did}", headers=admin).json()["expected_actions"]
    v = client.post(f"/api/drills/{did}/respond", headers=op,
                    json={"actions": expected, "note": "done"}).json()
    mine = v["my_response"]
    assert mine["correct"] == len(expected) and mine["wrong"] == 0 and mine["score"] == 100
    assert v["expected_actions"] == expected
    assert client.get("/api/drills/active", headers=op).json() == []
    assert client.post(f"/api/drills/{did}/respond", headers=op,
                       json={"actions": []}).status_code == 409

    ana = auth(client, email="ana@demo.eu")
    clock.add(400)
    v = client.post(f"/api/drills/{did}/respond", headers=ana, json={
        "actions": ["Send employees to fight the fire with extinguishers", expected[0]]}).json()
    assert v["my_response"]["wrong"] == 1 and v["my_response"]["score"] < 50

    board = client.post(f"/api/drills/{did}/end", headers=admin).json()
    assert board["status"] == "ended" and len(board["stages"]) == 6
    assert [r["email"] for r in board["responses"]][:2] == ["operator@demo.eu", "ana@demo.eu"]


def test_drill_rules(client):
    admin = auth(client)
    r = client.post("/api/drills", headers=admin,
                    json={"site_id": "ES-OU-002", "scenario": "sensor_first"})
    assert r.status_code == 422   # no sensor mesh on ES-OU-002
    op = auth(client, email="operator@demo.eu")
    assert client.post("/api/drills", headers=op,
                       json={"site_id": "ES-OU-001", "scenario": "approaching"}).status_code == 403
    r = client.post("/api/drills", headers=admin, json={
        "site_id": "ES-OU-005", "scenario": "false_alarm", "participants": ["ana@demo.eu"]})
    assert r.status_code == 201
    did = r.json()["drill_id"]
    assert client.get(f"/api/drills/{did}", headers=op).status_code == 404   # not invited
    assert client.post("/api/drills", headers=admin, json={
        "site_id": "ES-OU-005", "scenario": "approaching",
        "participants": ["fire@demo.eu"]}).status_code == 422
