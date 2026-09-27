"""advisor.py — AI Advisor: context, engines, validation, template, storage (§5.10)."""
from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime, timezone

from app import config
from app.geo import compass
from app.models import AdvisorResponse, AdvisorSuggestion, Site, SiteStatus
from app.providers.llm import GroqProvider, OllamaProvider
from app.sop import match_actions

TACTICS = re.compile(
    r"back[- ]?burn|backfire|contrafuego|firebreak|fire ?line|cortafuego|extinguish|"
    r"suppress|attack the fire|water drop|drop water|approach the fire|fight the fire|tactic",
    re.IGNORECASE,
)

SYSTEM_PROMPT = (
    "You advise the operations team of a company that owns the site described in the context. "
    "A wildfire may threaten the site.\n"
    "Rules:\n"
    "1. Give at most 6 suggestions for the company's own operations: the operator in the "
    "control room, the site team, or what information to share with the fire service liaison.\n"
    "2. Never give firefighting tactics or instructions to firefighters. Never suggest "
    "approaching the fire. The fire service decides all firefighting actions; the company "
    "follows its orders.\n"
    "3. Base every suggestion only on the context. Each suggestion must cite one or more "
    "evidence keys, copied exactly from EVIDENCE_KEYS.\n"
    "4. Be concrete and short. Say nothing about how the fire will spread beyond what "
    "spread_forecast states.\n"
    "5. If spread_forecast is present, use its hours_to_arrival to set urgency and to "
    "sequence the suggestions: what must happen before the front arrives, and in what order. "
    "Quote its numbers only; never estimate a spread rate or an arrival time yourself, and "
    "never contradict arrival_confidence. It is an estimate under assumptions, so do not "
    "present it as certain.\n"
    "6. If ground_sensors is present, use it: the combined fire estimate is the most precise "
    "position the company has, heat at a building means people may be there, and silent "
    "sensors mean an area is no longer monitored.\n"
    'Return only JSON: {"suggestions":[{"title": string (max 120 chars), "detail": string '
    '(max 600 chars), "audience": "operator"|"site_team"|"fire_service_liaison", "priority": '
    '1|2|3, "evidence": [string]}]}'
)

_AUDIENCES = {"operator", "site_team", "fire_service_liaison"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def matched_rule_ids(status: SiteStatus, site: Site, rules) -> list[str]:
    _, rule_ids = match_actions(rules, status.level, site.type, status.criticality,
                                status.fire_moving_toward_site)
    return rule_ids


def _hot(ground) -> list:
    return [n for n in ground[1] if n.state in ("warm", "fire")] if ground else []


def _dead(ground) -> list:
    return [n for n in ground[1] if n.state == "offline"] if ground else []


def evidence_keys(site: Site, status: SiteStatus, rule_ids: list[str],
                  ground=None, forecast=None) -> list[str]:
    keys = [f"factor:{n}" for n in
            ("proximity", "wind_alignment", "weather", "fuel", "vulnerability")]
    keys += [f"route:{r.name}" for r in status.access_routes]
    keys += [f"rule:{rid}" for rid in rule_ids]
    keys += ["asset:personnel_on_site", "asset:type", "asset:criticality", "asset:value_eur"]
    keys += [f"component:{c.name}" for c in status.exposed_components]
    if status.wind is not None:
        keys.append("weather:wind")
    if status.triggering_detection_id:
        keys.append(f"detection:{status.triggering_detection_id}")
    if ground:
        mesh = ground[0]
        keys.append("sensors:mesh")
        if mesh.fire_estimate:
            keys.append("sensors:fire_estimate")
        keys += [f"sensor:{n.label}" for n in _hot(ground) + _dead(ground)]
    if forecast is not None:
        keys += ["forecast:spread_rate", "forecast:direction"]
        if forecast.hours_to_arrival is not None:
            keys.append("forecast:time_to_arrival")
    return sorted(set(keys))


def build_context(site: Site, status: SiteStatus, headline: str, rules, ground=None,
                  forecast=None) -> dict:
    actions, rule_ids = match_actions(rules, status.level, site.type, status.criticality,
                                      status.fire_moving_toward_site)
    sensors = None
    if ground:
        mesh = ground[0]
        est = mesh.fire_estimate
        sensors = {
            "counts": mesh.counts,
            "fire_estimate": None if not est else {
                "distance_m": est.distance_m, "compass": compass(est.bearing_deg),
                "uncertainty_m": est.radius_m, "sensors": est.sensors,
                "confidence": est.confidence},
            "hot_sensors": [{"sensor": n.label, "place": n.place, "state": n.state,
                             "temp_c": n.temp_c, "distance_m": n.dist_m,
                             "compass": compass(n.bearing_deg)} for n in _hot(ground)],
            "offline_sensors": [{"sensor": n.label, "place": n.place,
                                 "compass": compass(n.bearing_deg)} for n in _dead(ground)],
        }
    spread_forecast = None
    if forecast is not None:
        spread_forecast = {
            "hours_to_arrival": forecast.hours_to_arrival,
            "arrival_confidence": forecast.arrival_confidence,
            "spread_rate_toward_site_m_per_hour": forecast.ros_toward_site_m_h,
            "heading_spread_rate_m_per_hour": forecast.ros_head_m_h,
            "fire_distance_km": forecast.distance_km,
            "approach_compass": compass(forecast.bearing_from_fire),
            "fuel_model": forecast.fuel_model,
            "front_positions": [p.model_dump() if hasattr(p, "model_dump") else p
                                for p in forecast.front_positions],
            "assumptions": forecast.assumptions,
        }
    return {
        "spread_forecast": spread_forecast,
        "ground_sensors": sensors,
        "site_name": site.name, "type": site.type, "criticality": site.criticality,
        "personnel_on_site": site.personnel_on_site, "level": status.level,
        "score": status.score,
        "factors": status.factors.model_dump(),
        "factor_status": status.factor_status.model_dump(),
        "wind": status.wind.model_dump() if status.wind else None,
        "weather": status.weather.model_dump() if status.weather else None,
        "nearest_fire_km": status.nearest_fire_km,
        "fire_compass": compass(status.fire_bearing_deg) if status.fire_bearing_deg is not None else None,
        "fire_moving_toward_site": status.fire_moving_toward_site,
        "headline": headline,
        "access_routes": [r.model_dump() for r in status.access_routes],
        "exposed_components": [c.model_dump() for c in status.exposed_components],
        "matching_rules": [{"rule_id": rid} for rid in rule_ids], "actions": actions,
    }


def validate(raw: list[dict], allowed_keys: list[str]) -> tuple[list[AdvisorSuggestion], int]:
    """Return (valid suggestions sorted by priority, count rejected by guardrails)."""
    allowed = set(allowed_keys)
    valid: list[AdvisorSuggestion] = []
    rejected = 0
    for item in raw[:10]:
        try:
            title = str(item["title"]).strip()
            detail = str(item["detail"]).strip()
            audience = item["audience"]
            priority = item["priority"]
            evidence = item["evidence"]
        except (KeyError, TypeError):
            rejected += 1
            continue
        ok = (
            0 < len(title) <= 120
            and 0 < len(detail) <= 600
            and audience in _AUDIENCES
            and priority in (1, 2, 3)
            and isinstance(evidence, list) and evidence
            and all(k in allowed for k in evidence)
            and not TACTICS.search(f"{title} {detail}")
        )
        if not ok:
            rejected += 1
            continue
        valid.append(AdvisorSuggestion(
            suggestion_id="sug_" + secrets.token_hex(4), title=title, detail=detail,
            audience=audience, priority=priority, evidence=list(evidence),
            decision=None, decided_by=None, decided_at=None))
    valid.sort(key=lambda s: s.priority)
    return valid[:config.MAX_SUGGESTIONS], rejected


def template_engine(site: Site, status: SiteStatus, rule_ids: list[str],
                    ground=None, forecast=None) -> list[dict]:
    routes = {r.name: r.status for r in status.access_routes}
    exposed = [n for n, st in routes.items() if st == "potentially_exposed"]
    available = [n for n, st in routes.items() if st == "available"]
    is_high = status.level in ("HIGH", "CRITICAL")
    rule_keys = [f"rule:{rid}" for rid in rule_ids]
    out: list[dict] = []

    if site.personnel_on_site > 0 and is_high:  # T1
        out.append({"title": f"Confirm headcount of the {site.personnel_on_site} people on site",
                    "detail": f"{site.personnel_on_site} people are recorded on site at level "
                              f"{status.level}. Confirm every person's location with the site manager.",
                    "audience": "site_team", "priority": 1,
                    "evidence": ["asset:personnel_on_site"]})
    if exposed and available:  # T2
        out.append({"title": f"Use {available[0]} for any movement",
                    "detail": f"{exposed[0]} is potentially exposed; {available[0]} is available.",
                    "audience": "site_team", "priority": 1,
                    "evidence": [f"route:{exposed[0]}", f"route:{available[0]}"]})
    elif len(exposed) == 2:  # T3
        out.append({"title": "Both access routes may be exposed: keep people away from the "
                             "perimeter and ask the fire service liaison for guidance",
                    "detail": "Both Primary and Secondary access are potentially exposed.",
                    "audience": "site_team", "priority": 1,
                    "evidence": [f"route:{n}" for n in routes]})
    if status.fire_moving_toward_site is True and rule_keys:  # T4
        out.append({"title": "Wind is carrying the fire toward the site: prepare the protocol "
                             "actions now",
                    "detail": "The wind is carrying the fire toward the site. Prepare the "
                              "protocol actions from the matching rules.",
                    "audience": "operator", "priority": 1,
                    "evidence": ["weather:wind"] + rule_keys})
    if status.level == "CRITICAL" and site.type in (
            "solar_farm", "substation", "wind_farm", "telecom_tower"):  # T5
        out.append({"title": "Send the handoff pack to the fire service liaison",
                    "detail": f"This {site.type} is at CRITICAL. Share the handoff pack "
                              "(hazards, water points, access) with the fire service liaison.",
                    "audience": "fire_service_liaison", "priority": 2,
                    "evidence": ["asset:type"]})
    est = ground[0].fire_estimate if ground else None
    if est:  # T8: combined sensor position is the most precise location the company has
        out.append({"title": f"Ground sensors place the fire {est.distance_m} m "
                             f"{compass(est.bearing_deg)} of the site: share it with the fire "
                             "service liaison",
                    "detail": f"{est.sensors} sensor(s) combined, {est.confidence} confidence, "
                              f"± {est.radius_m} m. Hottest: {est.hottest}. Share this position "
                              "with the fire service liaison.",
                    "audience": "fire_service_liaison", "priority": 1,
                    "evidence": ["sensors:fire_estimate"]})
    homes = [n for n in _hot(ground) if n.kind == "structure"]
    if homes:  # T9
        n = homes[0]
        out.append({"title": f"Heat at a {n.place.lower()} near the site ({n.label}): check "
                             "whether anyone is there",
                    "detail": f"Sensor {n.label} at a {n.place.lower()} {n.dist_m} m "
                              f"{compass(n.bearing_deg)} reads {n.temp_c}°C. Ask the site "
                              "manager whether employees or contractors are at that building "
                              "and pass the location to the fire service liaison.",
                    "audience": "operator", "priority": 1,
                    "evidence": [f"sensor:{n.label}"]})
    dead = _dead(ground)
    if dead:  # T10
        out.append({"title": f"{len(dead)} sensor(s) stopped reporting: treat those areas as "
                             "unmonitored",
                    "detail": "Silent sensors: " + ", ".join(
                        f"{n.label} ({n.place}, {compass(n.bearing_deg)})" for n in dead[:6])
                              + ". Do not assume those areas are safe.",
                    "audience": "operator", "priority": 2,
                    "evidence": [f"sensor:{n.label}" for n in dead[:6]]})
    if status.factor_status.weather in ("assumed", "unknown"):  # T6
        out.append({"title": f"Weather for this site is {status.factor_status.weather}: verify "
                             "local wind before acting",
                    "detail": f"Weather status is {status.factor_status.weather}. Verify local "
                              "wind conditions before acting on wind-based factors.",
                    "audience": "operator", "priority": 2, "evidence": ["factor:weather"]})
    if is_high and rule_keys:  # T7
        out.append({"title": "Review the protocol actions and record which were taken",
                    "detail": "Review the matching protocol actions and record which were taken.",
                    "audience": "operator", "priority": 3, "evidence": rule_keys})
    if forecast is not None and forecast.hours_to_arrival is not None:  # T8
        h = forecast.hours_to_arrival
        out.append({"title": f"Work to an estimated {h:.1f} h before the front reaches the site",
                    "detail": f"At the estimated spread rate of "
                              f"{forecast.ros_toward_site_m_h} m/h toward the site, the front "
                              f"is about {h:.1f} h away ({forecast.arrival_confidence}). "
                              "Sequence protocol actions to finish inside that window and "
                              "re-check after the next satellite pass; this is an estimate "
                              "under stated assumptions, not a certainty.",
                    "audience": "operator", "priority": 1,
                    "evidence": ["forecast:time_to_arrival", "forecast:spread_rate"]})
    return out


def generate(site: Site, status: SiteStatus, headline: str, rules, incident_id: str,
             at: str, ground=None, forecast=None) -> AdvisorResponse:
    """`ground` = (SensorMesh, [SensorNode]) when the site has sensors installed.
    `forecast` = SpreadForecast when a fire is in range, so the advice can be sequenced
    against the time the front is estimated to arrive."""
    rule_ids = matched_rule_ids(status, site, rules)
    keys = evidence_keys(site, status, rule_ids, ground, forecast)
    context = build_context(site, status, headline, rules, ground, forecast)
    user_message = f"EVIDENCE_KEYS: {json.dumps(keys)}\nCONTEXT: {json.dumps(context)}"

    attempts = []
    if os.environ.get("GROQ_API_KEY"):
        attempts.append(("groq", GroqProvider()))
    if os.environ.get("OLLAMA_URL"):
        attempts.append(("ollama", OllamaProvider()))

    generated_by = None
    model = None
    suggestions: list[AdvisorSuggestion] = []
    rejected = 0
    fallback_reason = None if attempts else "no LLM configured"

    for name, provider in attempts:
        try:
            raw = provider.suggest(SYSTEM_PROMPT, user_message)
        except Exception as e:  # noqa: BLE001
            fallback_reason = f"LLM error: {str(e)[:80]}"
            continue
        valid, rej = validate(raw, keys)
        if valid:
            generated_by, model, suggestions, rejected = name, provider.model, valid, rej
            fallback_reason = None
            break
        fallback_reason = "LLM output failed validation"

    if not suggestions:
        generated_by, model = "template", None
        suggestions, rejected = validate(
            template_engine(site, status, rule_ids, ground, forecast), keys)

    return AdvisorResponse(
        incident_id=incident_id, at=at, generated_by=generated_by, model=model,
        created_at=_now(), evidence_keys=keys, suggestions=suggestions,
        rejected_by_guardrails=rejected, fallback_reason=fallback_reason,
        disclaimer=config.DISCLAIMER_ADVISOR,
    )
