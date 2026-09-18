"""routes/system.py — system endpoints (§2.5). T1-M1: /api/health only.

Later milestones add /api/status/sources, /api/ingestion/runs,
/api/notifications/outbox and /api/audit.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from app import config
from app.models import Health

router = APIRouter(tags=["system"])

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _data_source() -> str:
    """Read meta.json if the fetch scripts have run (§5.8); else synthetic fallback."""
    meta = _DATA_DIR / "meta.json"
    try:
        return json.loads(meta.read_text(encoding="utf-8"))["data_source"]
    except (OSError, KeyError, ValueError):
        return "synthetic_fallback"


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health(
        data_source=_data_source(),
        replay_start=config.REPLAY_START,
        replay_end=config.REPLAY_END,
    )
