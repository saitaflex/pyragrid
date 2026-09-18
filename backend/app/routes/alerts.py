"""routes/alerts.py — alerts, acknowledge, incidents (§2.5)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app import state
from app.auth import AuthUser, get_current_user
from app.db import get_db
from app.models import AckResponse, Alert, Incident
from app.replay import (
    build_alerts, incident_by_id, incidents_history, incidents_open_at, snap,
)

router = APIRouter(tags=["alerts"])


def _alerts(user: AuthUser) -> list[Alert]:
    rd = state.get_replay(user.customer_id)
    rules = get_db().list_rules(user.customer_id)
    return build_alerts(rd, rules, get_db().acks_map(user.customer_id))


@router.get("/alerts", response_model=list[Alert])
def list_alerts(at: str | None = None, status: str = Query(default="all"),
                user: AuthUser = Depends(get_current_user)) -> list[Alert]:
    at = snap(at)
    out = [a for a in _alerts(user) if a.at <= at]
    if status == "unacknowledged":
        out = [a for a in out if not a.acknowledged]
    out.sort(key=lambda a: a.at, reverse=True)
    return out


@router.post("/alerts/{alert_id}/acknowledge", response_model=AckResponse)
def acknowledge(alert_id: str, user: AuthUser = Depends(get_current_user)) -> AckResponse:
    if not any(a.alert_id == alert_id for a in _alerts(user)):
        raise HTTPException(status_code=404, detail="alert not found")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    db = get_db()
    db.add_ack(user.customer_id, alert_id, user.email, now)  # first ack wins
    ack = db.get_ack(user.customer_id, alert_id)
    db.add_audit(user.customer_id, now, user.email, "alert_acknowledge", alert_id)
    return AckResponse(alert_id=alert_id, acknowledged_by=ack["acked_by"],
                       acknowledged_at=ack["acked_at"])


@router.get("/incidents", response_model=list[Incident])
def incidents(at: str | None = None,
              user: AuthUser = Depends(get_current_user)) -> list[Incident]:
    rd = state.get_replay(user.customer_id)
    return incidents_open_at(rd, get_db().list_rules(user.customer_id), snap(at))


@router.get("/incidents/history", response_model=list[Incident])
def incidents_history_route(user: AuthUser = Depends(get_current_user)) -> list[Incident]:
    rd = state.get_replay(user.customer_id)
    return incidents_history(rd, get_db().list_rules(user.customer_id))


@router.get("/incidents/{incident_id}", response_model=Incident)
def incident(incident_id: str, at: str | None = None,
             user: AuthUser = Depends(get_current_user)) -> Incident:
    rd = state.get_replay(user.customer_id)
    inc = incident_by_id(rd, get_db().list_rules(user.customer_id), incident_id, snap(at))
    if inc is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return inc
