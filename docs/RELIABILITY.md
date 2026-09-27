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

| | template (no AI) | `llama3.2:1b` local, CPU | Groq `openai/gpt-oss-120b` |
|:--|--:|--:|--:|
| Usable answers | 6/6 | 1/6 | 8/8 |
| Call failures | 0 | 2 (timeout) | 0 |
| Evidence grounding | **100%** (73/73) | **72.8%** (59/81) | 100% post-validation (see note) |
| Guardrail rejections | none | 7 hallucinated evidence keys, 5 non-objects, 1 bad priority, 1 missing fields | 2 in 11 calls |
| Latency p50 / max | <1 ms | 9.87 s / 19.36 s | **1.04 s / 2.9 s** |
| Cost per call | €0 | €0 (own hardware) | fractions of a cent |

The Groq column was measured against the **live production deployment** — 11 calls to
`POST /api/advisor/incidents/TN-JN-001_20250824T0300`, the incident used in the demo script —
so it includes real network latency, not just model time. 6 suggestions per call is typical.
Because the production API only returns output that has already passed `validate()`, its 100%
grounding is true by construction rather than a measurement of the raw model: the honest
signal there is that **2 suggestions across 11 calls were rejected by the guardrails**, so even
a 120B model's raw output is not always clean. The local column below measures raw output
directly, which is why its grounding figure is the more informative one.

The template and local-model columns were measured on 6 CRITICAL incidents from the real replay. Two further local models were tried:
`qwen3.5:4b` exceeded **222 s** per call on this laptop's CPU and was abandoned, and a single
timed `llama3.2:1b` call took 22.4 s. A 3,770-character prompt with 25 evidence keys is simply
too much for a small model on a CPU.

**What this measurement actually shows.** The guardrails are load-bearing, not decorative. The
small local model invented evidence keys in **22 of 81 citations** — keys naming sensors and
access routes that do not exist on that site — and `validate()` rejected every one before it
could reach an operator's screen. It also returned 5 items that were not objects at all. The
same pipeline with the same prompt produced usable, fully grounded output from the template
engine, which is why the fallback exists.

It also shows local inference needs a GPU to be viable here: at 9.9 s median and 19.4 s worst
case, the local model misses the product's own 15 s budget, so the product would correctly
have fallen back to the template engine. Self-hosting is a real option for a customer who will
not send site data to a hosted API — on a GPU, not on a laptop.

Grounding is the number that matters: it counts how many evidence keys the model cited that
were actually in the whitelist we gave it. A key it invents is a key it made up about
someone's site, and `validate()` drops the whole suggestion when that happens.

`--timeout` raises the limit for measurement only, so a slow model gets measured instead of
only recording a timeout; the product keeps its own 15 s budget.

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
- **The replay backtest is evidence, not validation.** Against the real August 2025 season
  across both regions, on real observed weather: **12 of 28 sites reached by fire, alerts
  raised on all 12, 0 missed exposures, 7 ever CRITICAL, median lead time 109.5 h.**
  Recall looks strong; precision is the weak side — nearly every Galician site reached HIGH,
  so the score separates *how bad* far better than it separates *whether*. A median of 111 h
  partly measures when the region lit up, not a per-site prediction. The Tunisian sites are
  the better test of discrimination, since they sit quiet for days before escalating.
- **The spread forecast is physics, not a trained model.** Rothermel (1972) with published
  coefficients, calibrated to Anderson (1982) fuel-model rates and tested against them, but
  never validated against an observed perimeter. It assumes uniform slope and fuel, constant
  wind, and surface fire only — no crown fire and no spotting, which is how real fires cross
  barriers. Every response carries its own `assumptions` list. See `docs/FIRE_SPREAD.md`.
- **The sensor mesh is simulated.** No hardware exists. Readings are derived from the same
  real detections plus a day/night ambient model. Nothing in the demo is a physical device.
- **OSM coverage is thinner in rural Tunisia.** Four of the eight Tunisian sites returned
  no buildings or vegetation from Overpass, so their sensors fall back to an even grid
  instead of real mapped features. The two sites with meshes installed (Ghardimaou,
  Zaghouan) do sit on real OSM features.
- **Weather is now real observed data.** Open-Meteo's archive is committed for all 28 sites,
  hourly across the replay window, so the risk score and the spread forecast run on the
  conditions that actually occurred (36.3 °C, 24% RH, wind from 212° at Ghardimaou on
  24 August 2025 at 15:00Z). `WEATHERAPI_KEY` adds weatherapi.com current conditions for live
  operation, exposed at `GET /api/sites/{id}/weather/live`; it returns None rather than
  raising, so a weather outage cannot take the risk score down.
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
