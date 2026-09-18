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
**One project (recommended):** vercel.com → Add New → Project → import this repo, leave
**Root Directory = `./`** (repo root) → Deploy. The root `vercel.json` builds the Console
(`frontend/dist`, live mode) and serves the Engine as a Python function at `/api/*`
(`api/index.py` → `backend/app`), all on one URL — no CORS or `VITE_API_BASE_URL` needed.
Then: Storage → **Neon Postgres** → connect (injects `DATABASE_URL`), add env var
`JWT_SECRET` (long random string) and optionally `GROQ_API_KEY` → Redeploy.
Check `https://<project>.vercel.app/api/health`, then log in as `admin@demo.eu` / `demo1234`.

Alternative: two projects from this repo, Engine (Root Directory = `backend`) and Console
(Root Directory = `frontend`, `VITE_API_BASE_URL=<engine url>`, `VITE_USE_MOCKS=false`).

If the Engine is unreachable, the Console falls back to built-in demo data and shows an
"Engine offline" banner.

> Fire data is NASA FIRMS VIIRS **detections** (or synthetic fallback), not fire perimeters.
> This is an MVP decision-support model, not a validated prediction model. Demo data is simulated.
