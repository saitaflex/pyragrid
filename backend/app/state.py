"""state.py — per-customer replay cache (§5.9). Computed lazily, invalidated on import."""
from __future__ import annotations

from app.db import get_db
from app.replay import ReplayData

_cache: dict[str, ReplayData] = {}


def get_replay(customer_id: str) -> ReplayData:
    if customer_id not in _cache:
        sites = get_db().list_assets(customer_id)
        _cache[customer_id] = ReplayData(customer_id, sites)
    return _cache[customer_id]


def invalidate(customer_id: str) -> None:
    _cache.pop(customer_id, None)


def clear() -> None:
    _cache.clear()
