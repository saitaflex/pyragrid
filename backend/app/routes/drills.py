"""routes/drills.py — training drills: admin starts, every participant is alerted and scored."""
from __future__ import annotations

import json
import secrets

from fastapi import APIRouter, Depends, HTTPException

from app import drills, state
from app.auth import STAFF_ROLES, AuthUser, require_admin, require_staff
from app.db import get_db
from app.models import DrillCreate, DrillRespondRequest, DrillView, StaffUser

router = APIRouter(tags=["drills"])


def _load(user: AuthUser, drill_id: str) -> dict:
    raw = get_db().get_drill(user.customer_id, drill_id)
    if not raw:
        raise HTTPException(status_code=404, detail="drill not found")
    d = json.loads(raw)
    if user.role != "admin" and user.email not in d["participants"]:
        raise HTTPException(status_code=404, detail="drill not found")
    return d


def _view(user: AuthUser, d: dict) -> DrillView:
    resp = {e: json.loads(r) for e, r in
            get_db().list_responses(user.customer_id, d["drill_id"]).items()}
    return drills.view(d, resp, user.email, user.role == "admin", drills.now_iso())


def _my_response(user: AuthUser, drill_id: str) -> dict:
    raw = get_db().list_responses(user.customer_id, drill_id).get(user.email)
    return json.loads(raw) if raw else {"email": user.email, "name": user.name,
                                        "acked_at": None, "responded_at": None,
                                        "actions": [], "note": ""}


@router.get("/staff", response_model=list[StaffUser])
def staff(user: AuthUser = Depends(require_admin)) -> list[StaffUser]:
    return [StaffUser(**u) for u in get_db().list_users(user.customer_id)
            if u["role"] in STAFF_ROLES]


@router.post("/drills", response_model=DrillView, status_code=201)
def create(body: DrillCreate, user: AuthUser = Depends(require_admin)) -> DrillView:
    db = get_db()
    site = state.get_replay(user.customer_id).sites.get(body.site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="site not found")
    if not 5 <= body.pace_s <= 600:
        raise HTTPException(status_code=422, detail="pace_s must be 5..600")
    has_mesh = body.site_id in db.list_installs(user.customer_id)
    if body.scenario in ("sensor_first", "false_alarm") and not has_mesh:
        raise HTTPException(status_code=422,
                            detail="this scenario needs a sensor mesh on the site")
    names = {u["email"]: u["name"] for u in db.list_users(user.customer_id)
             if u["role"] in STAFF_ROLES}
    staff_emails = list(names)
    participants = body.participants or staff_emails
    unknown = [p for p in participants if p not in staff_emails]
    if unknown:
        raise HTTPException(status_code=422, detail=f"not an employee: {', '.join(unknown)}")
    drill_id = f"DR-{secrets.token_hex(3).upper()}"
    d = drills.new_drill(drill_id, site, body.scenario, body.pace_s, has_mesh, participants,
                         names, db.list_rules(user.customer_id), user.email)
    db.save_drill(user.customer_id, drill_id, json.dumps(d), d["created_at"])
    db.add_audit(user.customer_id, d["created_at"], user.email, "drill_start",
                 f"{drill_id} {body.scenario} {body.site_id} ({len(participants)} notified)")
    return _view(user, d)


@router.get("/drills", response_model=list[DrillView])
def list_drills(user: AuthUser = Depends(require_staff)) -> list[DrillView]:
    out = []
    for raw in get_db().list_drills(user.customer_id):
        d = json.loads(raw)
        if user.role == "admin" or user.email in d["participants"]:
            out.append(_view(user, d))
    return out


@router.get("/drills/active", response_model=list[DrillView])
def active(user: AuthUser = Depends(require_staff)) -> list[DrillView]:
    """Running drills this user still has to respond to (drives the alert banner)."""
    out = []
    for raw in get_db().list_drills(user.customer_id, limit=10):
        d = json.loads(raw)
        if user.email not in d["participants"]:
            continue
        v = _view(user, d)
        if v.status == "running" and not (v.my_response and v.my_response.responded_at):
            out.append(v)
    return out


@router.get("/drills/{drill_id}", response_model=DrillView)
def get(drill_id: str, user: AuthUser = Depends(require_staff)) -> DrillView:
    return _view(user, _load(user, drill_id))


@router.post("/drills/{drill_id}/ack", response_model=DrillView)
def ack(drill_id: str, user: AuthUser = Depends(require_staff)) -> DrillView:
    d = _load(user, drill_id)
    if user.email not in d["participants"]:
        raise HTTPException(status_code=403, detail="not a participant")
    r = _my_response(user, drill_id)
    if not r["acked_at"]:
        r["acked_at"] = drills.now_iso()
        get_db().save_response(user.customer_id, drill_id, user.email, json.dumps(r))
        get_db().add_audit(user.customer_id, r["acked_at"], user.email, "drill_ack", drill_id)
    return _view(user, d)


@router.post("/drills/{drill_id}/respond", response_model=DrillView)
def respond(drill_id: str, body: DrillRespondRequest,
            user: AuthUser = Depends(require_staff)) -> DrillView:
    d = _load(user, drill_id)
    if user.email not in d["participants"]:
        raise HTTPException(status_code=403, detail="not a participant")
    if _view(user, d).status == "ended":
        raise HTTPException(status_code=409, detail="drill has ended")
    r = _my_response(user, drill_id)
    if r["responded_at"]:
        raise HTTPException(status_code=409, detail="already responded")
    bad = [a for a in body.actions if a not in d["options"]]
    if bad:
        raise HTTPException(status_code=422, detail="unknown action")
    now = drills.now_iso()
    r.update(acked_at=r["acked_at"] or now, responded_at=now, actions=body.actions,
             note=body.note[:500])
    get_db().save_response(user.customer_id, drill_id, user.email, json.dumps(r))
    get_db().add_audit(user.customer_id, now, user.email, "drill_respond", drill_id)
    return _view(user, d)


@router.post("/drills/{drill_id}/end", response_model=DrillView)
def end(drill_id: str, user: AuthUser = Depends(require_admin)) -> DrillView:
    d = _load(user, drill_id)
    if not d.get("ended_at"):
        d["ended_at"] = drills.now_iso()
        get_db().save_drill(user.customer_id, drill_id, json.dumps(d), d["created_at"])
        get_db().add_audit(user.customer_id, d["ended_at"], user.email, "drill_end", drill_id)
    return _view(user, d)
