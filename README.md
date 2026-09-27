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

## Ground sensors, partner views and drills
- **Ground sensors on real places (optional per site).** Each sensor is a dot on a real
  OpenStreetMap feature within the site plus a >=1 km buffer: on the site fence, at nearby
  houses / cabins / farm buildings, and along forest, scrub, grassland and farmland edges;
  open-ground points fill the gaps (`backend/data/sensor_places.json`, refreshed with
  `python scripts/fetch_sensor_places.py`). States: OK / Warm (>=45°C) / Fire (>=65°C) /
  Offline (burned or battery) / Dropped (tilt alarm). Warm and fire sensors are combined
  (heat-weighted) into one **estimated fire position** with an uncertainty circle, which the
  AI Advisor also uses. Demo readings are simulated from the scored detections.
- **Partner views.** `fire@demo.eu`, `gov@demo.eu`, `ngo@demo.eu` see `/situation` and
  `/sensors` only, filtered by a sharing policy (fire service: personnel, access routes,
  handoff pack; government: personnel; NGO: public picture only; nobody outside the company
  sees asset values). Company endpoints return 403 to partners.
- **Drills ("white attempts").** An admin starts a case study on a real site (`/drills`):
  simulated satellite and sensor signals arrive over real time, every employee gets a
  drill alert on every page, acknowledges, picks protocol actions, and is scored on speed
  and accuracy against the site's SOP rules. Drill data never enters real alerts.
  Extra demo employees: `ana@demo.eu`, `luis@demo.eu`.

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

## Regions and data
Real NASA FIRMS VIIRS detections for both operating regions, fetched by
`backend/scripts/fetch_firms.py` from `config.REGIONS` (needs a free `FIRMS_MAP_KEY`):
**Galicia, Spain** (20 sites, 17,579 detections) and **northwest Tunisia** (8 sites, 358
detections) over 8–25 August 2025. Sites added after a database was first seeded are
backfilled idempotently on boot, so an existing deployment picks them up on redeploy.
See [`docs/RELIABILITY.md`](docs/RELIABILITY.md) for measured latencies, failure modes and
limits, and [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for the 90-second demo path.

> Fire data is NASA FIRMS VIIRS **detections** (or synthetic fallback), not fire perimeters.
> This is an MVP decision-support model, not a validated prediction model. Demo data is simulated.
