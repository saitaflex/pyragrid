"""simulate.py — AI response plan for a simulated "fire reported now" incident.

The fire spread itself is simulated in the browser (elliptical spread driven by wind, fuel,
temperature and humidity). The browser sends the conditions and the current state; this
module turns them into evidence, asks the LLM for a response plan for the company's own
operations (same guardrails as the incident advisor: evidence keys, no firefighting tactics)
and falls back to a rule-based plan.
"""
from __future__ import annotations

import json
import os

from app import config
from app.advisor import validate
from app.geo import angdiff, compass
from app.models import SimAdviceResponse, SimConditions, SimState, Site
from app.providers.llm import GroqProvider, OllamaProvider
from app.sop import match_actions

SYSTEM_PROMPT = (
    "A wildfire has just been reported near a site owned by the company you advise. This is a "
    "training simulation with the conditions and fire state given in CONTEXT.\n"
    "Rules:\n"
    "1. Give at most 6 suggestions for the company's own response: the control-room operator, "
    "the site team, or what to share with the fire service liaison.\n"
    "2. Never give firefighting tactics or tell anyone to approach the fire. Stopping the fire is "
    "the fire service's job; the company protects people and assets and gives firefighters what "
    "they need (fire position, access, hazards, water points, people on site).\n"
    "3. Use the numbers: time until the front reaches the fence (eta_min), wind, humidity, fuel, "
    "which access route is exposed, sensor readings. Put the most urgent action first.\n"
    "4. Every suggestion cites one or more evidence keys copied exactly from EVIDENCE_KEYS.\n"
    "5. Be concrete and short.\n"
    'Return only JSON: {"suggestions":[{"title": string (max 120 chars), "detail": string '
    '(max 600 chars), "audience": "operator"|"site_team"|"fire_service_liaison", "priority": '
    '1|2|3, "evidence": [string]}]}'
)
DISCLAIMER = ("SIMULATION. AI suggestions for the company's own response, grounded in the "
              "simulated conditions. Not firefighting instructions: the fire service decides how "
              "to fight the fire. A person approves every action.")


def routes(site: Site, c: SimConditions, s: SimState) -> dict[str, str]:
    """An access route is exposed when it leaves toward the fire and the fire is within 5 km."""
    primary = site.primary_access_bearing_deg
    out = {}
    for name, b in (("Primary access", primary), ("Secondary access", (primary + 180) % 360)):
        exposed = angdiff(b, c.ignition_bearing_deg) <= 60 and s.front_km <= 5
        out[name] = "potentially_exposed" if exposed else "available"
    return out


def evidence_keys(site: Site, rule_ids: list[str]) -> list[str]:
    keys = ["condition:wind", "condition:humidity", "condition:temperature", "condition:fuel",
            "sim:front_distance", "sim:eta", "sim:rate_of_spread", "sim:sensors",
            "asset:personnel_on_site", "asset:type", "route:Primary access",
            "route:Secondary access"]
    keys += [f"rule:{r}" for r in rule_ids]
    return keys


def context(site: Site, c: SimConditions, s: SimState, rts: dict, actions: list[str]) -> dict:
    return {
        "site": {"name": site.name, "type": site.type, "personnel_on_site": site.personnel_on_site,
                 "criticality": site.criticality},
        "conditions": {"wind_kmh": c.wind_kmh, "wind_from": compass(c.wind_from_deg),
                       "temp_c": c.temp_c, "rh_pct": c.rh_pct, "fuel": c.fuel},
        "fire": {"reported": f"{c.ignition_km} km {compass(c.ignition_bearing_deg)} of the site",
                 "minutes_since_report": s.minutes, "level": s.level,
                 "front_km_to_fence": s.front_km, "eta_min": s.eta_min,
                 "head_rate_of_spread_m_per_min": s.head_ros_m_min,
                 "burned_ha": s.burned_ha, "wind_toward_site": s.fire_moving_toward_site},
        "sensors": {"fire": s.sensors_fire, "warm": s.sensors_warm, "silent": s.sensors_offline},
        "access_routes": rts,
        "protocol_actions": actions,
    }


def template(site: Site, c: SimConditions, s: SimState, rts: dict, rule_ids: list[str]) -> list[dict]:
    exposed = [n for n, v in rts.items() if v == "potentially_exposed"]
    free = [n for n, v in rts.items() if v == "available"]
    eta = s.eta_min
    out: list[dict] = []
    if site.personnel_on_site and (eta is not None and eta <= 180 or s.level == "CRITICAL"):
        route = free[0] if free else None
        out.append({
            "title": f"Move the {site.personnel_on_site} people on site out now"
                     + (f" by the {route.lower()}" if route else ""),
            "detail": (f"At the current spread the front reaches the fence in about {eta} min. "
                       if eta is not None else "") +
                      (f"The {exposed[0].lower()} faces the fire. " if exposed else "") +
                      "Confirm every person's location before they leave.",
            "audience": "site_team", "priority": 1,
            "evidence": ["sim:eta", "asset:personnel_on_site"] + [f"route:{n}" for n in rts]})
    out.append({
        "title": "Give the fire service the reported position, the wind and the site layout",
        "detail": f"Fire reported {c.ignition_km} km {compass(c.ignition_bearing_deg)}, spreading "
                  f"about {round(s.head_ros_m_min)} m/min with the wind from "
                  f"{compass(c.wind_from_deg)}. Send the handoff pack: access, hazards, water points.",
        "audience": "fire_service_liaison", "priority": 1,
        "evidence": ["sim:front_distance", "sim:rate_of_spread", "condition:wind"]})
    if s.level in ("HIGH", "CRITICAL") and site.type in ("solar_farm", "substation", "wind_farm"):
        out.append({"title": "Prepare a controlled shutdown so the site is safe for firefighters",
                    "detail": "Energised equipment is a hazard for crews. Prepare the shutdown and "
                              "tell the fire service liaison when it is done.",
                    "audience": "operator", "priority": 2, "evidence": ["asset:type"] + [f"rule:{r}" for r in rule_ids][:2]})
    if c.rh_pct < 25 or c.wind_kmh >= 30:
        out.append({"title": "Expect fast spread: re-check the arrival time every 10 minutes",
                    "detail": f"{c.rh_pct} % humidity and {c.wind_kmh} km/h wind make the spread "
                              "fast and harder to predict. Keep the fire service informed of changes.",
                    "audience": "operator", "priority": 2, "evidence": ["condition:humidity", "condition:wind"]})
    if s.sensors_fire or s.sensors_offline:
        out.append({"title": "Pass the ground-sensor readings to the fire service liaison",
                    "detail": f"{s.sensors_fire} sensor(s) report fire and {s.sensors_offline} went "
                              "silent. They show where the front actually is.",
                    "audience": "fire_service_liaison", "priority": 2, "evidence": ["sim:sensors"]})
    if rule_ids:
        out.append({"title": "Run the protocol actions for this level and record each one",
                    "detail": "Tick each action as it is done so the response is logged.",
                    "audience": "operator", "priority": 3, "evidence": [f"rule:{r}" for r in rule_ids]})
    return out


def advise(site: Site, c: SimConditions, s: SimState, rules) -> SimAdviceResponse:
    actions, rule_ids = match_actions(rules, s.level, site.type, site.criticality,
                                      s.fire_moving_toward_site)
    rts = routes(site, c, s)
    keys = evidence_keys(site, rule_ids)
    ctx = context(site, c, s, rts, actions)
    msg = f"EVIDENCE_KEYS: {json.dumps(keys)}\nCONTEXT: {json.dumps(ctx)}"

    attempts = []
    if os.environ.get("GROQ_API_KEY"):
        attempts.append(("groq", GroqProvider()))
    if os.environ.get("OLLAMA_URL"):
        attempts.append(("ollama", OllamaProvider()))
    reason = None if attempts else "no LLM configured"
    for name, provider in attempts:
        try:
            raw = provider.suggest(SYSTEM_PROMPT, msg)
        except Exception as e:  # noqa: BLE001
            reason = f"LLM error: {str(e)[:80]}"
            continue
        valid, rejected = validate(raw, keys)
        if valid:
            return SimAdviceResponse(generated_by=name, model=provider.model, suggestions=valid,
                                     evidence_keys=keys, rejected_by_guardrails=rejected,
                                     fallback_reason=None, protocol_actions=actions,
                                     access_routes=rts, disclaimer=DISCLAIMER)
        reason = "LLM output failed validation"
    valid, rejected = validate(template(site, c, s, rts, rule_ids), keys)
    return SimAdviceResponse(generated_by="template", model=None, suggestions=valid[:config.MAX_SUGGESTIONS],
                             evidence_keys=keys, rejected_by_guardrails=rejected,
                             fallback_reason=reason, protocol_actions=actions, access_routes=rts,
                             disclaimer=DISCLAIMER)
