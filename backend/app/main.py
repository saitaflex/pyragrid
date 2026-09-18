"""main.py — FastAPI app named `app` (Vercel entrypoint). TEAM_PLAN.md §5.9.

No startup work: every route calls ensure_ready() first (idempotent, guarded by a
lock, runs once per server instance).
"""
from __future__ import annotations

import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import system

app = FastAPI(title="Wildfire Asset Intelligence — Engine", version="2.1.0")

# CORS: allow all origins, methods and headers (bearer tokens, no cookies). §2.1
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

_ready_lock = threading.Lock()
_ready = False


def ensure_ready() -> None:
    """Create schema, seed and load data once per instance (§5.9). No-op for now."""
    global _ready
    if _ready:
        return
    with _ready_lock:
        if _ready:
            return
        # T1-M4+ will create the schema, seed users/sites/rules, and load replay data here.
        _ready = True


app.include_router(system.router, prefix="/api")
