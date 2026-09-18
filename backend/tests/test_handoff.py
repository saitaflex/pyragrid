"""test_handoff.py — Handoff Pack (§5.12 T1-M6)."""
from app.models import HandoffPack
from tests.conftest import auth


def test_handoff_water_points_and_contact(client):
    h = auth(client)
    r = client.get("/api/sites/ES-OU-001/handoff?at=2025-08-14T15:00:00Z", headers=h)
    pack = HandoffPack.model_validate(r.json())
    a, b = pack.water_points
    assert (round(a.lat, 5), round(a.lon, 5)) == (42.33277, -7.24029)
    assert (round(b.lat, 5), round(b.lon, 5)) == (42.32723, -7.21971)
    assert pack.contact.phone == "+34 600 000 001"
    assert pack.simulated is True
    assert "fire service decides" in pack.disclaimer


def test_handoff_unknown_site_404(client):
    r = client.get("/api/sites/NOPE/handoff", headers=auth(client))
    assert r.status_code == 404
