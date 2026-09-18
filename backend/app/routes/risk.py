"""routes/risk.py — portfolio, site status, timeline, detections, summary, handoff (§2.5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app import handoff as handoff_mod
from app import service, state
from app.auth import AuthUser, get_current_user
from app.db import get_db
from app.models import (
    Detection, HandoffPack, Portfolio, ReplaySummary, SiteStatus, TimelinePoint,
)
from app.providers.wildfire import FileDetectionsProvider
from app.replay import build_summary, parse, snap

router = APIRouter(tags=["risk"])


@router.get("/portfolio", response_model=Portfolio)
def portfolio(at: str | None = None, user: AuthUser = Depends(get_current_user)) -> Portfolio:
    rd = state.get_replay(user.customer_id)
    rules = get_db().list_rules(user.customer_id)
    return service.portfolio(rd, rules, snap(at))


@router.get("/sites/{site_id}/status", response_model=SiteStatus)
def site_status(site_id: str, at: str | None = None,
                user: AuthUser = Depends(get_current_user)) -> SiteStatus:
    rd = state.get_replay(user.customer_id)
    if site_id not in rd.sites:
        raise HTTPException(status_code=404, detail="site not found")
    rules = get_db().list_rules(user.customer_id)
    return service.with_sop(rd.status_at(site_id, snap(at)), rd.sites[site_id], rules)


@router.get("/sites/{site_id}/timeline", response_model=list[TimelinePoint])
def timeline(site_id: str, user: AuthUser = Depends(get_current_user)) -> list[TimelinePoint]:
    rd = state.get_replay(user.customer_id)
    if site_id not in rd.sites:
        raise HTTPException(status_code=404, detail="site not found")
    return rd.timeline(site_id)


@router.get("/detections", response_model=list[Detection])
def detections(at: str | None = None,
               window_hours: int = Query(default=12, ge=1, le=48),
               user: AuthUser = Depends(get_current_user)) -> list[Detection]:
    at = snap(at)
    from datetime import timedelta
    from app.replay import fmt
    win_start = fmt(parse(at) - timedelta(hours=window_hours))
    out = [d for d in FileDetectionsProvider().detections()
           if d.confidence in ("n", "h") and win_start < d.observed_at <= at]
    out.sort(key=lambda d: d.observed_at)
    return out


@router.get("/replay/summary", response_model=ReplaySummary)
def replay_summary(user: AuthUser = Depends(get_current_user)) -> ReplaySummary:
    return build_summary(state.get_replay(user.customer_id))


@router.get("/sites/{site_id}/handoff", response_model=HandoffPack)
def handoff(site_id: str, at: str | None = None,
            user: AuthUser = Depends(get_current_user)) -> HandoffPack:
    rd = state.get_replay(user.customer_id)
    if site_id not in rd.sites:
        raise HTTPException(status_code=404, detail="site not found")
    rules = get_db().list_rules(user.customer_id)
    at = snap(at)
    status = service.with_sop(rd.status_at(site_id, at), rd.sites[site_id], rules)
    return handoff_mod.build_pack(rd.sites[site_id], status, rd.headline_at(site_id, at), at)
