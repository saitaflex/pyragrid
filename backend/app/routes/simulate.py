"""routes/simulate.py — AI response plan and logging for the "fire reported now" simulator."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app import simulate, state
from app.auth import AuthUser, require_staff
from app.db import get_db
from app.drills import now_iso
from app.models import SimAdviceRequest, SimAdviceResponse, SimCompleteRequest

router = APIRouter(tags=["simulate"])


@router.post("/simulate/advice", response_model=SimAdviceResponse)
def advice(body: SimAdviceRequest, user: AuthUser = Depends(require_staff)) -> SimAdviceResponse:
    site = state.get_replay(user.customer_id).sites.get(body.site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="site not found")
    resp = simulate.advise(site, body.conditions, body.state, get_db().list_rules(user.customer_id))
    get_db().add_audit(user.customer_id, now_iso(), user.email, "simulation_advice",
                       f"{body.site_id} {body.state.level} {resp.generated_by}")
    return resp


@router.post("/simulate/complete", status_code=201)
def complete(body: SimCompleteRequest, user: AuthUser = Depends(require_staff)) -> dict:
    if body.site_id not in state.get_replay(user.customer_id).sites:
        raise HTTPException(status_code=404, detail="site not found")
    get_db().add_audit(user.customer_id, now_iso(), user.email, "simulation_response",
                       f"{body.site_id}: {len(body.actions_done)}/{body.actions_total} actions "
                       f"in {body.duration_s}s. {body.summary[:300]}")
    return {"logged": True}
