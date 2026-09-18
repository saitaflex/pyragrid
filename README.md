# Rural Valley — Wildfire Asset Intelligence

Source-agnostic geospatial decision-support platform for wildfire asset risk.
Built by two people in one repo (Rural Valley hackathon).

- **Full spec:** [`docs/TEAM_PLAN.md`](docs/TEAM_PLAN.md) — read Section 0 first.
- **Track 1 — Engine (`backend/`):** Oussama (@saitaflex). Python 3.12, FastAPI. Build Section 5.
- **Track 2 — Console (`frontend/`):** @callmegema. Node 22, Vite + React + TS. Build Section 6.
- **Contract:** Section 2 is shared and must match on both sides, byte for byte.

## Folder ownership (Section 3, absolute)
- Track 1 writes only `backend/`, root `README.md`, root `.gitignore`, `docs/`.
- Track 2 writes only `frontend/`.
- Branches: `t1/<topic>` and `t2/<topic>` → PR into `main`. Commits start with `[T1]` or `[T2]`.

## Run locally
```bash
# Engine
cd backend && pip install -r requirements-dev.txt && uvicorn app.main:app --port 8000
# Console (separate terminal, after it exists)
cd frontend && npm install && npm run dev
```

## Deploy (Vercel — Section 7)
Two projects from **this one repo**: Engine (Root Directory = `backend`) and Console (Root Directory = `frontend`).

> Fire data is NASA FIRMS VIIRS **detections** (or synthetic fallback), not fire perimeters.
> This is an MVP decision-support model, not a validated prediction model. Demo data is simulated.
