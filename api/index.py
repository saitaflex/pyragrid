"""Vercel entrypoint for the single-project deploy (repo root).

Puts backend/ on sys.path and re-exports the FastAPI `app`; vercel.json rewrites
/api/* here, and FastAPI's routes already carry the /api prefix.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402,F401
