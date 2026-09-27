"""assistant.py — a grounded operations assistant the operator can ask questions.

The AI Advisor answers one question ("what should I do about this incident?") on one screen.
This answers whatever the operator actually asks, from any page: *which site is worst right
now, how long until the fire reaches Ghardimaou, which of my access routes is exposed, what
does my protocol say at CRITICAL, why did this site escalate.*

It is a chatbot only in the interface sense. Under it, the same discipline as the advisor:

- **It cannot browse or recall.** Every answer is built from a context this module assembles
  from the live replay — the portfolio, open incidents, alerts, and the selected site's status,
  spread forecast and sensor mesh. There is no retrieval over free text and no memory beyond
  the turns the client sends back.
- **It must cite.** Every answer carries evidence keys copied from a closed whitelist. A key
  it invents fails validation and the answer is replaced by the deterministic one.
- **It must refuse.** Questions the context cannot answer are refused rather than guessed at,
  and the refusal says what data would be needed.
- **The tactics guardrail applies unchanged.** It will not discuss how to fight a fire.
- **It degrades.** With no LLM configured, or on any failure, `rule_answer()` answers the
  common questions deterministically from the same context.

What this deliberately is not: a general assistant. Asked about anything outside the
operator's own data it declines, because an open-ended answer is one we cannot ground, and an
ungrounded sentence on a wildfire screen is worse than no sentence.
"""
from __future__ import annotations

import json
import os
import re

from app import config
from app.advisor import TACTICS
from app.geo import compass
from app.models import AssistantAnswer
from app.providers.llm import GroqProvider, OllamaProvider

MAX_ANSWER_CHARS = 700
MAX_HISTORY = 6          # turns the client may send back; keeps the prompt bounded
RANK = {"NORMAL": 0, "ELEVATED": 1, "HIGH": 2, "CRITICAL": 3}

SYSTEM_PROMPT = (
    "You are the operations assistant for a company that owns the sites in CONTEXT. A wildfire "
    "may threaten them. Answer the operator's question about their own sites and response.\n"
    "Rules:\n"
    "1. Answer only from CONTEXT. If CONTEXT does not contain what is needed, set refused true "
    "and say which data is missing. Never guess a number, a distance or a time.\n"
    "2. Cite one or more evidence keys, copied exactly from EVIDENCE_KEYS, for every claim you "
    "make. An answer with no citation is not acceptable unless you are refusing.\n"
    "3. Never give firefighting tactics, never suggest approaching the fire. The fire service "
    "decides all firefighting actions; the company protects people and assets and supplies "
    "information.\n"
    "4. Be direct and short: two or three sentences, plain language, no preamble. Lead with the "
    "answer, then the reason.\n"
    "5. Set urgency: 'urgent' when people or a critical asset are at risk within hours, "
    "'action' when something should be done this shift, 'info' otherwise.\n"
    "6. Anything outside this company's sites and wildfire response — general knowledge, "
    "chat, other topics — is refused with a one-line explanation.\n"
    'Return only JSON: {"answer": string (max 700 chars), "evidence": [string], '
    '"urgency": "info"|"action"|"urgent", "refused": boolean}'
)


def build_context(rd, rules, at: str, site_id: str | None, alerts, incidents) -> tuple[dict, list[str]]:
    """The operator's situation, and the keys the model may cite. Kept compact: the portfolio
    is summarised to one line per site, and only the selected site is expanded."""
    from app import service

    keys: list[str] = ["portfolio:levels", "portfolio:worst_site"]
    sites = []
    for sid, statuses in rd.statuses.items():
        i = rd.steps.index(at)
        st = statuses[i]
        sites.append({"site_id": sid, "name": rd.sites[sid].name, "level": st.level,
                      "score": st.score, "nearest_fire_km": st.nearest_fire_km,
                      "type": rd.sites[sid].type,
                      "personnel_on_site": rd.sites[sid].personnel_on_site})
        keys.append(f"site:{sid}")
    sites.sort(key=lambda s: (-RANK[s["level"]], -s["score"]))

    ctx: dict = {
        "now": at,
        "site_count": len(sites),
        "levels": {lv: sum(1 for s in sites if s["level"] == lv)
                   for lv in ("CRITICAL", "HIGH", "ELEVATED", "NORMAL")},
        "sites_worst_first": sites[:12],
        "open_incidents": [{"incident_id": i.incident_id, "site_id": i.site_id,
                            "level": i.level, "score": i.score} for i in incidents[:8]],
        "unacknowledged_alerts": sum(1 for a in alerts if not a.acknowledged),
    }
    for i in incidents[:8]:
        keys.append(f"incident:{i.incident_id}")
    if alerts:
        keys.append("alerts:unacknowledged")

    # the selected site, in full: this is what most questions are actually about
    if site_id and site_id in rd.sites:
        site = rd.sites[site_id]
        st = service.with_sop(rd.status_at(site_id, at), site, rules)
        ctx["selected_site"] = {
            "site_id": site_id, "name": site.name, "type": site.type,
            "criticality": site.criticality, "personnel_on_site": site.personnel_on_site,
            "level": st.level, "score": st.score,
            "factors": st.factors.model_dump(),
            "nearest_fire_km": st.nearest_fire_km,
            "fire_compass": compass(st.fire_bearing_deg) if st.fire_bearing_deg is not None else None,
            "fire_moving_toward_site": st.fire_moving_toward_site,
            "weather": st.weather.model_dump() if st.weather else None,
            "access_routes": [r.model_dump() for r in st.access_routes],
            "protocol_actions": st.sop_actions,
            "headline": rd.headline_at(site_id, at),
        }
        keys += [f"factor:{n}" for n in
                 ("proximity", "wind_alignment", "weather", "fuel", "vulnerability")]
        keys += [f"route:{r.name}" for r in st.access_routes]
        keys += ["asset:personnel_on_site", "asset:type", "asset:criticality"]
        if st.weather is not None:
            keys.append("weather:observed")

        forecast = service.forecast_for(rd, site, at)
        if forecast is not None:
            ctx["selected_site"]["spread_forecast"] = {
                "hours_to_arrival": forecast.hours_to_arrival,
                "arrival_confidence": forecast.arrival_confidence,
                "spread_rate_toward_site_m_per_hour": forecast.ros_toward_site_m_h,
                "fire_distance_km": forecast.distance_km,
                "fuel_model": forecast.fuel_model,
                "assumptions": forecast.assumptions,
            }
            keys += ["forecast:time_to_arrival", "forecast:spread_rate"]
        ctx["selected_site"]["matching_rules"] = [{"rule_id": r} for r in
                                                  _rule_ids(st, site, rules)]
        keys += [f"rule:{r}" for r in _rule_ids(st, site, rules)]
    return ctx, sorted(set(keys))


def _rule_ids(status, site, rules) -> list[str]:
    from app.advisor import matched_rule_ids
    return matched_rule_ids(status, site, rules)


def rule_answer(question: str, ctx: dict) -> tuple[str, list[str], str]:
    """Deterministic answers to the questions operators actually ask, used when no model is
    configured and whenever the model's answer fails validation. Intentionally narrow: it
    answers what it can recognise and otherwise says so."""
    q = question.lower()
    sites = ctx.get("sites_worst_first") or []
    sel = ctx.get("selected_site")

    if sel and re.search(r"how long|when will|arrive|reach|eta|time", q):
        f = sel.get("spread_forecast")
        if f and f.get("hours_to_arrival") is not None:
            return (f"About {f['hours_to_arrival']:.1f} hours at the estimated spread rate of "
                    f"{f['spread_rate_toward_site_m_per_hour']} m/h toward {sel['name']} "
                    f"({f['arrival_confidence']}). This is a physics estimate under stated "
                    f"assumptions, not a certainty.",
                    ["forecast:time_to_arrival", "forecast:spread_rate"], "urgent"
                    if f["hours_to_arrival"] <= 6 else "action")
        return ("No fire is currently within range of this site, so there is no arrival "
                "estimate.", ["portfolio:levels"], "info")

    if re.search(r"worst|most at risk|priority|first|which site", q) and sites:
        w = sites[0]
        return (f"{w['name']} ({w['site_id']}) is the highest priority: {w['level']} at score "
                f"{w['score']}"
                + (f", nearest fire {w['nearest_fire_km']} km." if w['nearest_fire_km'] is not None
                   else ".")
                + f" {ctx['levels']['CRITICAL']} sites are CRITICAL and "
                  f"{ctx['levels']['HIGH']} are HIGH right now.",
                ["portfolio:worst_site", f"site:{w['site_id']}"],
                "urgent" if w["level"] == "CRITICAL" else "action")

    if sel and re.search(r"people|personnel|staff|headcount|who", q):
        return (f"{sel['personnel_on_site']} people are recorded on site at {sel['name']}, "
                f"currently {sel['level']}. Confirm each person's location with the site "
                f"manager.", ["asset:personnel_on_site"],
                "urgent" if sel["level"] in ("HIGH", "CRITICAL") else "info")

    if re.search(r"how many|count|summary|overview|status|situation", q):
        lv = ctx["levels"]
        return (f"{ctx['site_count']} sites: {lv['CRITICAL']} CRITICAL, {lv['HIGH']} HIGH, "
                f"{lv['ELEVATED']} ELEVATED, {lv['NORMAL']} NORMAL. "
                f"{ctx['unacknowledged_alerts']} alerts are unacknowledged.",
                ["portfolio:levels"], "action" if lv["CRITICAL"] else "info")

    if sel and re.search(r"route|access|road|evacuat", q):
        exposed = [r["name"] for r in sel["access_routes"]
                   if r["status"] == "potentially_exposed"]
        clear = [r["name"] for r in sel["access_routes"] if r["status"] == "available"]
        if exposed:
            return (f"{', '.join(exposed)} is potentially exposed at {sel['name']}. "
                    + (f"Use {clear[0]} instead." if clear
                       else "No route is currently marked available."),
                    [f"route:{n}" for n in exposed + clear], "urgent")
        return (f"All access routes at {sel['name']} are currently available.",
                [f"route:{r['name']}" for r in sel["access_routes"]], "info")

    if sel and re.search(r"why|explain|reason|factor|score", q):
        f = sel["factors"]
        top = sorted(f.items(), key=lambda kv: -kv[1])[:3]
        return (f"{sel['name']} is {sel['level']} at {sel['score']}. The largest contributors "
                f"are " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in top)
                + f". Headline: {sel['headline']}",
                [f"factor:{k}" for k, _ in top], "info")

    return ("", [], "info")


def validate_answer(raw: dict, allowed: list[str]) -> tuple[AssistantAnswer | None, str | None]:
    """Same contract as the advisor: cite from the whitelist, no tactics, bounded length."""
    if not isinstance(raw, dict):
        return None, "not an object"
    answer = str(raw.get("answer", "")).strip()
    refused = bool(raw.get("refused", False))
    urgency = raw.get("urgency", "info")
    evidence = raw.get("evidence", [])
    if not answer or len(answer) > MAX_ANSWER_CHARS:
        return None, "answer missing or too long"
    if urgency not in ("info", "action", "urgent"):
        return None, "bad urgency"
    if not isinstance(evidence, list):
        return None, "evidence not a list"
    if TACTICS.search(answer):
        return None, "firefighting tactics"
    unknown = [k for k in evidence if k not in set(allowed)]
    if unknown:
        return None, f"cited evidence we never supplied: {unknown[:3]}"
    if not refused and not evidence:
        return None, "no evidence cited"
    return AssistantAnswer(
        answer=answer, evidence=list(evidence), urgency=urgency, refused=refused,
        generated_by="", model=None, fallback_reason=None,
        disclaimer=config.DISCLAIMER_ASSISTANT), None


def ask(question: str, ctx: dict, keys: list[str],
        history: list[dict] | None = None) -> AssistantAnswer:
    """Answer one question. Never raises: a failure becomes the deterministic answer."""
    question = (question or "").strip()[:500]
    turns = (history or [])[-MAX_HISTORY:]
    convo = "\n".join(f"{t.get('role')}: {str(t.get('text'))[:300]}" for t in turns
                      if t.get("role") in ("operator", "assistant"))
    user = (f"EVIDENCE_KEYS: {json.dumps(keys)}\nCONTEXT: {json.dumps(ctx)}\n"
            + (f"EARLIER TURNS:\n{convo}\n" if convo else "")
            + f"QUESTION: {question}")

    attempts = []
    if os.environ.get("GROQ_API_KEY"):
        attempts.append(("groq", GroqProvider()))
    if os.environ.get("OLLAMA_URL"):
        attempts.append(("ollama", OllamaProvider()))

    fallback_reason = None if attempts else "no LLM configured"
    for name, provider in attempts:
        try:
            raw = provider.suggest_one(SYSTEM_PROMPT, user)
        except Exception as e:  # noqa: BLE001
            fallback_reason = f"LLM error: {str(e)[:80]}"
            continue
        ans, why = validate_answer(raw, keys)
        if ans is not None:
            ans.generated_by = name
            ans.model = provider.model
            return ans
        fallback_reason = f"answer rejected: {why}"

    text, ev, urgency = rule_answer(question, ctx)
    if not text:
        return AssistantAnswer(
            answer="I can only answer from this company's own site data - levels, factors, "
                   "access routes, protocol actions, sensors and the spread forecast. Ask me "
                   "about one of those, or open a site and ask again.",
            evidence=[], urgency="info", refused=True, generated_by="rules", model=None,
            fallback_reason=fallback_reason, disclaimer=config.DISCLAIMER_ASSISTANT)
    return AssistantAnswer(answer=text, evidence=ev, urgency=urgency, refused=False,
                           generated_by="rules", model=None, fallback_reason=fallback_reason,
                           disclaimer=config.DISCLAIMER_ASSISTANT)
