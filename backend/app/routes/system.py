"""routes/system.py — health, source status, ingestion runs, outbox, audit (§2.5, §5.7)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends

from app import config, state
from app.auth import AuthUser, require_admin, require_staff
from app.db import get_db
from app.models import AuditEntry, Health, IngestionRun, OutboxEmail, SourceStatus
from app.replay import build_outbox, snap

router = APIRouter(tags=["system"])

_DATA = Path(__file__).resolve().parent.parent.parent / "data"
_WEATHER = _DATA / "weather"


def _meta() -> dict:
    try:
        return json.loads((_DATA / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"data_source": "synthetic_fallback"}


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health(data_source=_meta().get("data_source", "synthetic_fallback"),
                  replay_start=config.REPLAY_START, replay_end=config.REPLAY_END)


def _weather_source(customer_id: str) -> SourceStatus:
    sites = get_db().list_assets(customer_id)
    missing = [s for s in sites if not (_WEATHER / f"{s.site_id}.json").exists()]
    assumed = os.environ.get("ASSUMED_WEATHER", "true").lower() == "true"
    if not missing:
        return SourceStatus(name="Weather", state="ONLINE", detail="Open-Meteo historical archive")
    if assumed:
        return SourceStatus(name="Weather", state="FALLBACK",
                            detail=f"Assumed weather for {len(missing)} site(s) (archive not fetched)")
    return SourceStatus(name="Weather", state="OFFLINE", detail="Weather unknown for some sites")


def _database_source() -> SourceStatus:
    db = get_db()
    if not db.healthy():
        return SourceStatus(name="Database", state="OFFLINE", detail="Database unreachable")
    if db.is_pg:
        return SourceStatus(name="Database", state="ONLINE", detail="PostgreSQL")
    if "/tmp" in getattr(db, "sqlite_path", ""):
        return SourceStatus(name="Database", state="FALLBACK",
                            detail="Temporary storage: resets when the server restarts. "
                                   "Connect Neon Postgres for the demo.")
    return SourceStatus(name="Database", state="ONLINE", detail="SQLite (local file)")


def _advisor_source() -> SourceStatus:
    if os.environ.get("GROQ_API_KEY"):
        model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        return SourceStatus(name="AI Advisor", state="ONLINE", detail=f"Groq {model}")
    if os.environ.get("OLLAMA_URL"):
        model = os.environ.get("OLLAMA_MODEL", "llama3.1")
        return SourceStatus(name="AI Advisor", state="ONLINE", detail=f"Ollama {model}")
    return SourceStatus(name="AI Advisor", state="FALLBACK",
                        detail="Template suggestions (no LLM configured)")


@router.get("/status/sources", response_model=list[SourceStatus])
def sources(user: AuthUser = Depends(require_staff)) -> list[SourceStatus]:
    ds = _meta().get("data_source", "synthetic_fallback")
    if ds.startswith("firms"):
        firms = SourceStatus(name="FIRMS", state="ONLINE", detail="NASA FIRMS VIIRS detections")
    else:
        firms = SourceStatus(name="FIRMS", state="FALLBACK",
                             detail="Synthetic demo detections (FIRMS not reachable at data build time)")
    smtp = SourceStatus(name="Notification", state="ONLINE", detail="SMTP configured") \
        if os.environ.get("SMTP_HOST") else \
        SourceStatus(name="Notification", state="FALLBACK", detail="Email outbox only (SMTP not configured)")
    return [
        firms,
        _weather_source(user.customer_id),
        SourceStatus(name="Vegetation", state="FALLBACK",
                     detail="Fuel class from customer asset data; no land-cover dataset yet"),
        smtp,
        _database_source(),
        _advisor_source(),
    ]


@router.get("/ingestion/runs", response_model=list[IngestionRun])
def ingestion_runs(user: AuthUser = Depends(require_staff)) -> list[IngestionRun]:
    try:
        raw = json.loads((_DATA / "ingestion_runs.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    runs = [IngestionRun.model_validate(r) for r in raw]
    runs.reverse()  # newest first
    return runs


@router.get("/notifications/outbox", response_model=list[OutboxEmail])
def outbox(at: str | None = None,
           user: AuthUser = Depends(require_staff)) -> list[OutboxEmail]:
    rd = state.get_replay(user.customer_id)
    rules = get_db().list_rules(user.customer_id)
    return build_outbox(rd, rules, get_db().acks_map(user.customer_id), snap(at))


@router.get("/audit", response_model=list[AuditEntry])
def audit(user: AuthUser = Depends(require_admin)) -> list[AuditEntry]:
    return [AuditEntry.model_validate(r) for r in get_db().list_audit(user.customer_id)]
