"""test_advisor.py — AI Advisor validation, template, decisions (§5.12 T1-M6)."""
import pytest

from app import advisor as A
from app.defaults import default_rules
from app.models import (
    AccessRoute, Component, Factors, FactorStatuses, Site, SiteStatus, Weather, Wind,
)
from app.providers.llm import _parse
from tests.conftest import auth


def _site():
    return Site(site_id="ES-OU-001", name="Solar Trives 01", type="solar_farm", lat=42.33,
                lon=-7.23, radius_m=600, value_eur=12400000, fuel_class="high",
                personnel_on_site=7, primary_access_bearing_deg=200, criticality=4,
                components=[Component(name="PV array", value_eur=8680000)])


def _status():
    return SiteStatus(
        site_id="ES-OU-001", name="Solar Trives 01", type="solar_farm", lat=42.33, lon=-7.23,
        radius_m=600, value_eur=12400000, personnel_on_site=7, criticality=4, score=83,
        level="CRITICAL",
        factors=Factors(proximity=30.7, wind_alignment=21.7, weather=11.0, fuel=12.0, vulnerability=8.0),
        factor_status=FactorStatuses(proximity="observed", wind_alignment="observed",
                                     weather="observed", fuel="customer_provided",
                                     vulnerability="customer_provided"),
        nearest_fire_km=3.1, fire_bearing_deg=225, fire_moving_toward_site=True,
        triggering_detection_id="d-0001", wind=Wind(speed_kmh=26, from_deg=225, to_deg=45),
        weather=Weather(temp_c=34, rh_pct=18),
        access_routes=[AccessRoute(name="Primary access", bearing_deg=200, status="potentially_exposed"),
                       AccessRoute(name="Secondary access", bearing_deg=20, status="available")],
        exposed_components=[Component(name="PV array", value_eur=8680000)], sop_actions=[])


def test_validator_drops_bad_suggestions():
    allowed = ["factor:weather"]
    raw = [
        {"title": "Confirm the plan", "detail": "Do it now", "audience": "operator",
         "priority": 1, "evidence": ["factor:weather"]},                 # good
        {"title": "Backburn the ridge", "detail": "start a firebreak", "audience": "operator",
         "priority": 1, "evidence": ["factor:weather"]},                 # tactics
        {"title": "Cite unknown", "detail": "x", "audience": "operator",
         "priority": 1, "evidence": ["rule:R-999"]},                     # unknown key
        {"title": "Wrong audience", "detail": "x", "audience": "manager",
         "priority": 1, "evidence": ["factor:weather"]},                 # bad audience
    ]
    valid, rejected = A.validate(raw, allowed)
    assert len(valid) == 1
    assert rejected == 3


def test_parse_rejects_bad_output():
    with pytest.raises(ValueError):
        _parse("{}")
    with pytest.raises(Exception):
        _parse("not json")
    assert A.validate([], ["factor:weather"]) == ([], 0)


def test_template_order():
    site, status = _site(), _status()
    rule_ids = ["R-001", "R-002", "R-004"]
    raw = A.template_engine(site, status, rule_ids)
    titles = [r["title"] for r in raw]
    assert titles[0].startswith("Confirm headcount of the 7")
    assert titles[1] == "Use Secondary access for any movement"
    assert "carrying the fire toward the site" in titles[2]
    assert titles[3] == "Send the handoff pack to the fire service liaison"
    assert titles[4].startswith("Review the protocol actions")
    # template output passes its own validator
    keys = A.evidence_keys(site, status, rule_ids)
    valid, rejected = A.validate(raw, keys)
    assert rejected == 0 and len(valid) == 5


def test_generate_without_llm_uses_template(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    resp = A.generate(_site(), _status(), "Fire 3.1 km SW, wind toward site",
                      default_rules(), "ES-OU-001_20250814T0600", "2025-08-14T15:00:00Z")
    assert resp.generated_by == "template"
    assert resp.fallback_reason == "no LLM configured"
    assert len(resp.suggestions) >= 1


def test_decisions_first_wins_and_audited(client, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    h = auth(client)
    history = client.get("/api/incidents/history", headers=h).json()
    assert history, "need an incident"
    iid = history[0]["incident_id"]
    resp = client.post(f"/api/advisor/incidents/{iid}", headers=h).json()
    assert resp["generated_by"] == "template"
    sid = resp["suggestions"][0]["suggestion_id"]
    first = client.post(f"/api/advisor/suggestions/{sid}/decision",
                        json={"decision": "approved", "note": "ok"}, headers=h).json()
    assert first["decision"] == "approved"
    second = client.post(f"/api/advisor/suggestions/{sid}/decision",
                         json={"decision": "rejected", "note": "changed"}, headers=h).json()
    assert second["decision"] == "approved"  # first wins
    latest = client.get(f"/api/advisor/incidents/{iid}/latest", headers=h).json()
    assert any(s["decision"] == "approved" for s in latest["suggestions"])
    decisions = client.get("/api/advisor/decisions", headers=h).json()
    assert any(d["suggestion_id"] == sid for d in decisions)
    assert client.post("/api/advisor/suggestions/nope/decision",
                       json={"decision": "approved", "note": ""}, headers=h).status_code == 404
