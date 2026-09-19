# Wildfire Asset Intelligence — Engine (backend)

FastAPI backend for the Rural Valley hackathon project. Source-agnostic wildfire
asset-risk engine: ingests detections, enriches them, scores exposure transparently
(`rules-1.0`), and produces a prioritized action list, alerts, an AI Advisor and a
firefighter handoff pack. Contract version **2.1.0** (see `../docs/TEAM_PLAN.md` §2).

## Run locally
```bash
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --port 8000
curl localhost:8000/api/health          # {"status":"ok","contract_version":"2.1.0",...}
pytest                                    # 40 tests
```
First start seeds the demo data into SQLite (`data/app.db` locally). To rebuild the
detection dataset: `python scripts/generate_synthetic_detections.py` (offline), or
`python scripts/fetch_firms.py` + `python scripts/fetch_weather.py` with real API keys.

## Demo accounts (seeded on first start)
| Email | Password | Customer | Role |
|---|---|---|---|
| admin@demo.eu | demo1234 | demo | admin |
| operator@demo.eu | demo1234 | demo | operator |
| other@othercorp.eu | demo1234 | othercorp | admin |

`operator` reads its own customer's data and acknowledges alerts. `admin` also imports
assets, edits SOP rules and reads the audit log. `othercorp` (one asset) proves tenant isolation.

## Environment variables
| Var | Purpose | Default |
|---|---|---|
| `JWT_SECRET` | JWT signing secret (set a long random string) | `dev-only-change-me` (warns) |
| `DATABASE_URL` | Postgres (Neon) connection; unset → SQLite | unset |
| `ASSUMED_WEATHER` | Use assumed weather when no archive file | `true` |
| `GROQ_API_KEY` | Enables the Groq LLM advisor | unset → template engine |
| `GROQ_MODEL` | Groq model id | `openai/gpt-oss-120b` |
| `OLLAMA_URL` / `OLLAMA_MODEL` | Local-dev LLM advisor | unset / `llama3.1` |
| `FIRMS_MAP_KEY` | NASA FIRMS key for `fetch_firms.py` | unset → synthetic |

Secrets are never committed (`.env` is gitignored; see `.env.example`).

## Deploy to Vercel (§7)
1. Import this repo → **Root Directory = `backend`** → FastAPI is detected from
   `app/main.py` exposing `app`. Python 3.12 (`.python-version`).
2. Storage → **Neon Postgres** (free) → connect; `DATABASE_URL` is injected.
3. Env vars: `JWT_SECRET`, `GROQ_API_KEY`, `GROQ_MODEL`, `ASSUMED_WEATHER=true`. Redeploy.
4. Verify `/api/health` returns contract `2.1.0` and `/api/status/sources` shows Database ONLINE.

`vercel.json` sets `maxDuration=60` and excludes `tests/` and `scripts/` from the bundle.
The function filesystem is read-only except `/tmp`; without Postgres, SQLite falls back to
`/tmp/wai.db` (flagged FALLBACK — acknowledgements reset on restart).

## Honesty & safety (visible in the product)
- Fire data is **NASA FIRMS VIIRS detections** (or a clearly-labelled synthetic fallback),
  not fire perimeters. Cite NASA FIRMS. Weather from the **Open-Meteo** historical archive.
- Every factor carries a status: `observed`, `customer_provided`, `assumed` or `unknown`;
  missing data is never invented. Never "real-time" — "near-real-time".
- The score is an **MVP decision-support model, not a validated prediction model**. No accuracy
  percentage is claimed — only measured backtest numbers.
- The **AI Advisor** advises the *company's* own operations only, never firefighting tactics.
  Every suggestion cites its evidence, is labelled by engine (`groq`/`ollama`/`template`), and
  a human approves or rejects it. The Handoff Pack informs the fire service; the fire service
  decides all firefighting actions. Sites, values, personnel and SOPs are simulated.
