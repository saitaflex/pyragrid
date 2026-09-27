"""routes/assistant.py — the grounded operations assistant.

One POST, because a question is not a resource. Staff only: the context it builds contains
asset criticality and personnel counts, which never go to partner roles.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import assistant as assistant_mod
from app import state
from app.auth import AuthUser, require_staff
from app.db import get_db
from app.models import AssistantAnswer
from app.replay import build_alerts, incidents_open_at, snap

router = APIRouter(tags=["assistant"])


class Turn(BaseModel):
    role: str
    text: str = Field(max_length=1000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    site_id: str | None = None
    at: str | None = None
    history: list[Turn] = Field(default_factory=list, max_length=12)


@router.post("/assistant/ask", response_model=AssistantAnswer)
def ask(body: AskRequest, user: AuthUser = Depends(require_staff)) -> AssistantAnswer:
    rd = state.get_replay(user.customer_id)
    rules = get_db().list_rules(user.customer_id)
    at = snap(body.at)
    if body.site_id and body.site_id not in rd.sites:
        raise HTTPException(status_code=404, detail="site not found")

    acks = get_db().acks_map(user.customer_id)
    alerts = build_alerts(rd, rules, acks)
    alerts = [a for a in alerts if a.at <= at]
    incidents = incidents_open_at(rd, rules, at)

    ctx, keys = assistant_mod.build_context(rd, rules, at, body.site_id, alerts, incidents)
    answer = assistant_mod.ask(body.question, ctx, keys,
                               [t.model_dump() for t in body.history])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    get_db().add_audit(user.customer_id, now, user.email, "assistant_ask",
                       body.question[:120])
    return answer
