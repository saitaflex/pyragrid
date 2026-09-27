# Reliability, cost and limits

Measured on 27 September 2026 against the real FIRMS dataset (17,579 VIIRS detections,
8–25 August 2025, Ourense / Galicia). Every number below was produced by a command in this
repo, not estimated. Reproduce with `scripts/eval_advisor.py` and the commands noted.

## What was measured

| Thing | Number | How |
|:--|--:|:--|
| Detections in the shipped dataset | 17,937 (17,579 Galicia + 358 Tunisia) | `data/meta.json`, source `firms_sp` |
| Detection file load, all rows parsed | 102 ms | `FileDetectionsProvider().detections()` |
| Replay compute, 28 sites × 144 steps | 3.15 s | `ReplayData("demo", sites)`, once per process |
| Cold API call (builds the replay cache) | 1,587 ms | `GET /api/portfolio` |
| Warm `GET /api/portfolio` | 5 ms | best of 3 |
| Warm `GET /api/alerts` | 10 ms | best of 3 |
| Warm `GET /api/sites/{id}/status` | 20 ms | best of 3 |
| Warm `GET /api/incidents/{id}` | 28 ms | best of 3 |
| Warm `GET /api/sites/{id}/handoff` | 23 ms | best of 3 |
| Warm `GET /api/sensors` (35-node mesh) | 59 ms | best of 3 |
| Warm `GET /api/replay/summary` | 620 ms | slowest endpoint; History page only |
| Backend tests | 50 passing | `python -m pytest --import-mode=importlib --ignore=tests/test_db_both.py` |

The replay is computed once per customer per process and cached in memory
(`app/state.py`), which is why the first request pays 1.6 s and the rest cost single-digit
milliseconds. On Vercel that cost is paid again after a cold start.

## AI Advisor: measured, not claimed

`scripts/eval_advisor.py` runs real incidents from the FIRMS replay through every configured
engine and reports grounding, guardrail hits, latency and token cost.

```
cd backend
GROQ_API_KEY=... python scripts/eval_advisor.py --cases 10 --json eval.json
```

| | template (no AI) | Groq `openai/gpt-oss-120b` |
|:--|--:|--:|
| Usable answers | 6/6 | _to fill from the run_ |
| Evidence grounding | 100% (73/73) | _to fill_ |
| Guardrail rejections | none | _to fill_ |
| Latency p50 | < 1 ms | _to fill_ |
| Cost per call | €0 | _to fill_ |

Grounding is the number that matters: it counts how many evidence keys the model cited that
were actually in the whitelist we gave it. A key it invents is a key it made up about
someone's site, and `validate()` drops the whole suggestion when that happens.

## Failure modes and what happens

| If this fails | The product does | Where |
|:--|:--|:--|
| FIRMS unreachable at data-build time | Falls back to a clearly labelled synthetic dataset; the UI shows *Synthetic demo data* instead of *NASA FIRMS* | `scripts/fetch_firms.py` |
| Groq is down, slow or rate-limited | 15 s timeout, then the next configured provider, then `template_engine` from the protocol rules; the panel shows the engine badge and the reason | `app/advisor.py:generate` |
| Groq returns invalid JSON | One automatic retry (Groq's `json_validate_failed` is intermittent), then fallback | `app/providers/llm.py` |
| The model invents evidence, wrong audience, over-length text | Suggestion dropped, count shown to the operator as *blocked by safety rules* | `app/advisor.py:validate` |
| The model gives firefighting tactics | Regex guardrail drops it before it can reach a screen | `app/advisor.py:TACTICS` |
| No LLM configured at all | Template engine; badge reads *Template (no AI)* | `app/advisor.py` |
| Engine unreachable from the browser | Console falls back to built-in demo data and shows an *Engine offline* banner | `frontend/src/api/client.ts` |
| Postgres unavailable | SQLite file database | `app/db.py` |

Cost control: `reasoning_effort=low` on the reasoning model, `max_tokens` 4000,
`temperature` 0.2, at most 6 suggestions, and advice is generated only when an operator
presses the button — never on a timer, never per detection.

## Limits — what this does not do

- **The risk score is a transparent weighted heuristic, not a trained or validated model.**
  Proximity, wind alignment, weather, fuel and asset vulnerability, hand-weighted, version
  `rules-1.0`. It has never been calibrated against ground truth.
- **The replay backtest is evidence, not validation.** Against the real August 2025 season:
  10 of 20 sites reached by fire, alerts raised on all 10, 0 missed, median lead time 111 h.
  Recall looks strong; precision is the weak side — 19 of 20 sites reached HIGH, so the score
  separates *how bad* far better than it separates *whether*. A median of 111 h partly
  measures when the region lit up, not a per-site prediction.
- **The sensor mesh is simulated.** No hardware exists. Readings are derived from the same
  real detections plus a day/night ambient model. Nothing in the demo is a physical device.
- **OSM coverage is thinner in rural Tunisia.** Four of the eight Tunisian sites returned
  no buildings or vegetation from Overpass, so their sensors fall back to an even grid
  instead of real mapped features. The two sites with meshes installed (Ghardimaou,
  Zaghouan) do sit on real OSM features.
- **Weather is not live in the demo.** The cache is empty, so scoring uses the documented
  assumed weather constants.
- **FIRMS gives detections, not fire perimeters**, at roughly 375 m resolution with hours of
  latency. The product is decision support for an asset owner, not a fire-behaviour model.
- **The tactics guardrail is a regex.** It is best-effort defence in depth behind mandatory
  human approval, not a guarantee.
- **No frontend tests.** Backend coverage is 50 tests; the console is manually tested.

## Data and privacy

- Sources cited in the UI: NASA FIRMS VIIRS (detections), Open-Meteo (weather), map data
  © OpenStreetMap contributors. Licensed brand fonts are deliberately kept out of the
  repository.
- **Sensor siting touches real dwellings.** Sensor positions are chosen from OSM features
  including houses, cabins and farm buildings near a site. That means a real deployment
  places equipment next to identifiable homes and needs landowner consent and a data
  protection assessment before a single sensor is installed. In this demo all sites, people
  and sensors are simulated.
- Partner roles see only what their sharing policy allows: the fire service gets personnel,
  access routes and the handoff pack; government gets personnel; NGOs get the public picture.
  **Asset values never leave the owning company** — company endpoints return 403 to partners.
- Every AI suggestion carries its disclaimer verbatim, names its engine and model, and
  requires a named human to approve or reject it. Decisions are written to an audit log.
- Drill data is kept separate and never enters real alerts.
