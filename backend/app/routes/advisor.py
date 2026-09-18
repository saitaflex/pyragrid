"""routes/advisor.py — AI Advisor endpoints (§2.5, §5.10)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app import advisor as advisor_mod
from app import service, state
from app.auth import AuthUser, require_admin, require_staff
from app.db import get_db
from app.models import (
    AdvisorResponse, AdvisorSuggestion, DecisionRecord, DecisionRequest,
)
from app.replay import incident_by_id, snap

router = APIRouter(tags=["advisor"])


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _store(customer_id: str, resp: AdvisorResponse) -> None:
    db = get_db()
    for s in resp.suggestions:
        data = {"suggestion": s.model_dump(), "generated_by": resp.generated_by,
                "model": resp.model, "at": resp.at, "created_at": resp.created_at,
                "evidence_keys": resp.evidence_keys,
                "rejected_by_guardrails": resp.rejected_by_guardrails,
                "fallback_reason": resp.fallback_reason, "incident_id": resp.incident_id,
                "title": s.title}
        db.save_suggestion(customer_id, s.suggestion_id, resp.incident_id,
                           json.dumps(data), resp.created_at)


def _fill_decision(customer_id: str, s: AdvisorSuggestion) -> AdvisorSuggestion:
    d = get_db().get_decision(customer_id, s.suggestion_id)
    if not d:
        return s
    return s.model_copy(update={"decision": d["decision"], "decided_by": d["decided_by"],
                                "decided_at": d["decided_at"]})


def _latest(customer_id: str, incident_id: str) -> AdvisorResponse | None:
    rows = get_db().suggestions_for_incident(customer_id, incident_id)
    if not rows:
        return None
    parsed = [json.loads(r["data"]) for r in rows]
    newest = max(p["created_at"] for p in parsed)
    group = [p for p in parsed if p["created_at"] == newest]
    meta = group[0]
    suggestions = [_fill_decision(customer_id, AdvisorSuggestion.model_validate(p["suggestion"]))
                   for p in group]
    suggestions.sort(key=lambda s: s.priority)
    return AdvisorResponse(
        incident_id=incident_id, at=meta["at"], generated_by=meta["generated_by"],
        model=meta["model"], created_at=meta["created_at"],
        evidence_keys=meta["evidence_keys"], suggestions=suggestions,
        rejected_by_guardrails=meta["rejected_by_guardrails"],
        fallback_reason=meta["fallback_reason"], disclaimer=advisor_mod.config.DISCLAIMER_ADVISOR,
    )


@router.post("/advisor/incidents/{incident_id}", response_model=AdvisorResponse)
def generate(incident_id: str, at: str | None = None,
             user: AuthUser = Depends(require_staff)) -> AdvisorResponse:
    rd = state.get_replay(user.customer_id)
    rules = get_db().list_rules(user.customer_id)
    at = snap(at)
    inc = incident_by_id(rd, rules, incident_id, at)
    if inc is None:
        raise HTTPException(status_code=404, detail="incident not found")
    site = rd.sites[inc.site_id]
    status = service.with_sop(rd.status_at(inc.site_id, at), site, rules)
    headline = rd.headline_at(inc.site_id, at)
    resp = advisor_mod.generate(site, status, headline, rules, incident_id, at)
    _store(user.customer_id, resp)
    get_db().add_audit(user.customer_id, _now(), user.email, "advisor_generate", incident_id)
    return resp


@router.get("/advisor/incidents/{incident_id}/latest", response_model=AdvisorResponse)
def latest(incident_id: str, user: AuthUser = Depends(require_staff)) -> AdvisorResponse:
    resp = _latest(user.customer_id, incident_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="no advice yet")
    return resp


@router.post("/advisor/suggestions/{suggestion_id}/decision", response_model=DecisionRecord)
def decide(suggestion_id: str, body: DecisionRequest,
           user: AuthUser = Depends(require_staff)) -> DecisionRecord:
    db = get_db()
    row = db.get_suggestion(user.customer_id, suggestion_id)
    if not row:
        raise HTTPException(status_code=404, detail="suggestion not found")
    now = _now()
    db.add_decision(user.customer_id, suggestion_id, body.decision, body.note, user.email, now)
    stored = db.get_decision(user.customer_id, suggestion_id)  # first decision wins
    db.add_audit(user.customer_id, now, user.email, "advisor_decision", suggestion_id)
    meta = json.loads(row["data"])
    return DecisionRecord(
        suggestion_id=suggestion_id, incident_id=row["incident_id"], title=meta["title"],
        decision=stored["decision"], note=stored["note"], decided_by=stored["decided_by"],
        decided_at=stored["decided_at"], generated_by=meta["generated_by"])


@router.get("/advisor/decisions", response_model=list[DecisionRecord])
def decisions(user: AuthUser = Depends(require_admin)) -> list[DecisionRecord]:
    db = get_db()
    out = []
    for d in db.list_decisions(user.customer_id):
        row = db.get_suggestion(user.customer_id, d["suggestion_id"])
        if not row:
            continue
        meta = json.loads(row["data"])
        out.append(DecisionRecord(
            suggestion_id=d["suggestion_id"], incident_id=row["incident_id"],
            title=meta["title"], decision=d["decision"], note=d["note"],
            decided_by=d["decided_by"], decided_at=d["decided_at"],
            generated_by=meta["generated_by"]))
    return out
