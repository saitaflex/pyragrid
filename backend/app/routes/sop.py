"""routes/sop.py — SOP rule CRUD (§2.5). Admin for writes."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import AuthUser, get_current_user, require_admin
from app.db import get_db
from app.models import SopRule, SopRuleInput

router = APIRouter(tags=["sop"])


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("/sop/rules", response_model=list[SopRule])
def list_rules(user: AuthUser = Depends(get_current_user)) -> list[SopRule]:
    return get_db().list_rules(user.customer_id)


@router.post("/sop/rules", response_model=SopRule, status_code=201)
def create_rule(body: SopRuleInput, user: AuthUser = Depends(require_admin)) -> SopRule:
    db = get_db()
    rule = SopRule(rule_id=db.next_rule_id(user.customer_id), **body.model_dump())
    db.upsert_rule(user.customer_id, rule)
    db.add_audit(user.customer_id, _now(), user.email, "sop_rule_create", rule.rule_id)
    return rule


@router.put("/sop/rules/{rule_id}", response_model=SopRule)
def update_rule(rule_id: str, body: SopRuleInput,
                user: AuthUser = Depends(require_admin)) -> SopRule:
    db = get_db()
    if not any(r.rule_id == rule_id for r in db.list_rules(user.customer_id)):
        raise HTTPException(status_code=404, detail="rule not found")
    rule = SopRule(rule_id=rule_id, **body.model_dump())
    db.upsert_rule(user.customer_id, rule)
    db.add_audit(user.customer_id, _now(), user.email, "sop_rule_update", rule_id)
    return rule


@router.delete("/sop/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, user: AuthUser = Depends(require_admin)) -> Response:
    db = get_db()
    if not db.delete_rule(user.customer_id, rule_id):
        raise HTTPException(status_code=404, detail="rule not found")
    db.add_audit(user.customer_id, _now(), user.email, "sop_rule_delete", rule_id)
    return Response(status_code=204)
