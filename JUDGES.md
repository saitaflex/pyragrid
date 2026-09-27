# PyraGrid — for the jury

**Live:** https://rural-valley.vercel.app · sign in `admin@demo.eu` / `demo1234`

Wildfire decision support for the companies that own assets in the countryside. Not another
fire map: it turns public satellite data into *what this company should do in the next hour*.

Everything below is live and checkable. Where something is simulated or unvalidated, this
document says so in the same sentence — we would rather you find the caveat here than on stage.

---

## 60 seconds, if that is all you have

1. Open https://rural-valley.vercel.app/?at=2025-08-20T15:00:00Z — **Cork Oak Block
   Ghardimaou**, north-west Tunisia, ELEVATED, *"no fire within 25 km"*.
2. Change the clock to `2025-08-24T15:00:00Z` — same site, **HIGH 71**, fire 1.3 km south,
   wind pushing it toward the site.
3. Open the incident. The score breaks into five factors. The **spread forecast** puts the
   front **~2.5 hours** away, with all six of its assumptions one click behind the number.
4. The **AI Advisor** writes the operator's next actions, sequenced inside those 2.5 hours,
   citing only evidence we handed it, blocked from ever giving firefighting tactics, and
   needing a named human to approve each one.
5. `/history` — replayed against the real August 2025 season: **12 of 28 sites were reached by
   fire, we alerted on every one, zero missed.**

`docs/DEMO_SCRIPT.md` is the full 90-second path with deep links.

---

## Against your rubric

### Problem + user value — 20

**The user:** the operations manager of a company with rural assets — a solar farm, a cork oak
concession, a substation, a vineyard — plus the fire-service liaison they hand information to.

**The gap:** NASA FIRMS, EFFIS and OroraTech serve agencies and analysts. A site owner gets a
fire map at best. Nobody tells *them* which of their twenty sites to act on first, what their
own protocol says to do, or what the fire service needs from them.

**Honest limit:** the user is credible but **not yet validated by interviews**. We have no
letter of intent and no pilot customer. The business case is in
`docs/business-plan/PyraGrid_Business_Plan.pdf`; treat its market assumptions as assumptions.

### Functional execution — 20

Live, not a slide deck: FastAPI + Postgres on Vercel, 16 console pages, real auth, multi-tenant
isolation, role-scoped partner views, drills, handoff packs.

**Real data, not mock-ups:**

| | |
|:--|:--|
| Satellite detections | **17,937 real NASA FIRMS VIIRS** records, 8–25 Aug 2025 — 17,579 Galicia + **358 north-west Tunisia** |
| Weather | **Real observed hourly** Open-Meteo archive for all 28 sites (Ghardimaou at the demo moment: 36.3 °C, 24% RH, wind 212°) |
| Sites | 28 across two regions, placed on the actual fire clusters |
| Sensor positions | Real OpenStreetMap features — fence lines, farm buildings, forest edge |
| Live operation | `/sites/{id}/fire/live` (FIRMS **NRT**) and `/sites/{id}/weather/live` |

**What is simulated, plainly:** the ground sensor *readings* (no hardware exists — positions
are real, temperatures are derived from the same real detections), and all sites, people and
protocols, which are demo data on real geography.

### Quality of AI use — 20

Two AI components, and we are precise about which does what.

**1. The risk score is not AI.** It is a transparent weighted model — proximity, wind
alignment, weather, fuel, asset vulnerability — auditable line by line in
`backend/app/scoring.py`. We say so rather than calling it AI.

**2. The spread forecast is physics.** Rothermel (1972) with Albini (1976) dead/live weighting,
Simard (1968) fuel moisture, Alexander (1985) elliptical growth. All four fuel models reproduce
Anderson (1982)'s published rates **within 0.6%**, asserted in `backend/tests/test_spread.py` so a
coefficient edit cannot drift silently. Our first version was 3–5× too fast because it treated
live shrub fuel as bone-dry dead fuel; validating against published BEHAVE values caught it.

**3. Two LLM surfaces, both grounded the same way.**

The **AI Advisor** (on every incident) writes and prioritises the operator's next actions.
The **operations assistant** (the dock, bottom right of any page) answers whatever the operator
asks — which site is worst, how long until the front arrives, which route is exposed, why a
site scored as it did, how many people are on site.

The assistant is a chat box in the interface only. Underneath it keeps the same contract, which
is the interesting part: an open text field is normally where grounding is lost.

- It cannot browse or recall. Every answer is built from a context assembled from the live
  replay, and there is no memory beyond the turns the client sends back.
- It must cite evidence keys from a closed whitelist. **Live testing caught the model citing
  JSON paths (`selected_site.personnel_on_site`) instead of whitelist keys — validation
  rejected those answers and the deterministic engine answered instead.** The prompt was then
  fixed; the guardrail had already done its job.
- It refuses what it cannot ground, including general knowledge, and says why.
- The tactics guardrail applies unchanged: ask it how to put the fire out and it declines.
- With no model configured, or on any rejection or rate-limit, `rule_answer()` answers the
  common questions deterministically from the same context. You can see this happen: hammer it
  and Groq returns 429, and the answers keep coming from the rules.

Try it: *"How do I put the fire out?"* → declines. *"What is the capital of France?"* →
declines. *"How long until the fire reaches this site?"* → 2.5 hours, citing
`forecast:time_to_arrival`.

**3b. The advisor in detail.** Its job is language and judgement, not
detection. What makes it trustworthy:

- **Closed-whitelist grounding.** It may cite only evidence keys we hand it. A key it invents
  fails validation and the whole suggestion is dropped.
- **A hard safety rule.** It is blocked from firefighting tactics — that is the fire service's
  decision, and the operator's screen shows how many suggestions the rules threw away.
- **Human approval on every suggestion**, recorded with a name in an audit log.
- **Provider-agnostic with a real fallback**: Groq, any local Ollama model, or a deterministic
  template engine that needs no model at all.

**Measured, not claimed** (`backend/scripts/eval_advisor.py`, full table in `docs/RELIABILITY.md`):

| | template (no AI) | `llama3.2:1b` local CPU | Groq `gpt-oss-120b` |
|:--|--:|--:|--:|
| Usable answers | 6/6 | 1/6 | 8/8 |
| **Evidence grounding** | 100% (73/73) | **72.8%** (59/81) | validated output only |
| Guardrails caught | none | **22 invented evidence keys**, 5 non-objects | 2 in 11 calls |
| Latency p50 / worst | <1 ms | 9.87 s / 19.36 s | **1.04 s / 2.9 s** |

The middle column is the one we would point at: a small local model invented evidence — sensors
and access routes that do not exist on that site — in **22 of 81 citations**, and validation
rejected every one. Even the 120B had 2 suggestions blocked across 11 calls. **The guardrail is
load-bearing, not decoration.**

**Not built, and not implied:** no trained or fine-tuned model, no PINN, no learned spread
correction. `docs/FIRE_SPREAD.md` sets out the staged path and the datasets it needs.

### Testing + reliability — 15

**72 tests passing.** `cd backend && python -m pytest --import-mode=importlib`

Measured, on the live deployment (`docs/RELIABILITY.md`):

| | |
|:--|:--|
| Cold API call (builds the replay cache) | 1,587 ms |
| Warm portfolio / incident / alerts | 4 / 7 / 13 ms |
| Sensors (49-node mesh) | 15 ms |
| Spread forecast | 79 ms |
| Advisor end-to-end via Groq | 1.04 s p50, 2.9 s worst |

**Failure modes, each with a fallback:** FIRMS unreachable → labelled synthetic dataset;
Groq down or slow → 15 s timeout, then any other provider, then the template engine, with the
reason shown on screen; invalid JSON → one retry; model invents evidence → suggestion dropped
and counted; engine unreachable from the browser → console falls back to demo data with an
offline banner; Postgres down → SQLite; weather or live-fire API down → reports unavailable
rather than raising, so it cannot take the risk score with it.

**Cost control:** `reasoning_effort=low`, 4,000 max tokens, at most 6 suggestions, and advice is
generated only when an operator presses the button — never on a timer, never per detection.

**The backtest.** Against the real August 2025 season on real weather: 12 of 28 sites reached by
fire, alerted on all 12, **0 missed**, median lead time 109.5 h. Recall looks strong; **precision
is the weak side** — nearly every Galician site reached HIGH, because that season really was
region-wide. The score separates *how bad* far better than *whether*. The 109.5 h median partly
measures when the region lit up, not a per-site prediction. This is evidence, not validation:
nothing has been checked against an observed fire perimeter.

**No frontend tests.** Backend coverage is 72 tests; the console is manually tested.

### Experience + demo — 15

One rehearsed 90-second path, five deep links, in `docs/DEMO_SCRIPT.md` — including the four
questions a sharp judge asks and our answers. Every page takes the replay clock from `?at=`, so
any moment in the season is a shareable URL.

Interface notes: controls behave like equipment rather than marketing — they firm up on hover
and depress when pressed, nothing floats in a dense table. Keyboard focus is visible on every
control, `prefers-reduced-motion` is respected (a CRITICAL indicator stays solid instead of
blinking), and data provenance is carried on a chip's left edge so *observed* versus *assumed*
survives a colour-blind viewer.

### Responsible AI + data — 10

- **Human oversight is structural.** Every AI suggestion needs a named human to approve or
  reject it, recorded in an audit log. Nothing acts autonomously.
- **A safety boundary in code, not just a prompt.** The advisor cannot emit firefighting
  tactics; the guardrail is a regex behind mandatory human approval, and we call it best-effort
  rather than a guarantee.
- **Data minimisation by role.** The fire service sees personnel, access routes and the handoff
  pack; government sees personnel; NGOs see the public picture. **Asset values never leave the
  owning company** — company endpoints return 403 to partners.
- **A privacy question we raise ourselves:** sensor positions are chosen from OSM features
  including houses and farm buildings, so a real deployment puts equipment beside identifiable
  homes and needs landowner consent and a data protection assessment before a single install.
- **Attribution and licensing:** NASA FIRMS, Open-Meteo, weatherapi.com, map data ©
  OpenStreetMap contributors, all credited in the interface. Licensed brand fonts are
  deliberately excluded from this repository so nobody redistributes a font without a licence.
- **Stated limits, everywhere.** Disclaimers are returned by the API verbatim and rendered
  verbatim; the spread forecast ships its own six assumptions and the UI shows them.

---

## Security

Because this repository is being handed over: `docs/SECURITY.md` has the threat model, the test
covering each control, and the gaps unsoftened.

Rate limiting by route class (10/min login per IP **and** per account, 15/min on the paid
advisor route), constant-time login so response timing cannot enumerate accounts, HS256 pinned
with required claims, a **fatal** error if `JWT_SECRET` is missing in production, security
headers and `Cache-Control: no-store` on every response, a 1 MiB body cap, and one error
handler that logs the detail and returns only a request id. All parameterised SQL.

**Stated limits:** the rate limiter is in-process, so on Vercel the effective limit scales with
instance count — a real speed bump against one attacker, **not** a distributed rate limit. No
token revocation, no MFA or lockout, no pen test, dependencies unpinned.

One thing that looks like a hole and is not: `/api/detections` is readable by partner roles.
Those are public NASA FIRMS rows with no site, asset or personnel fields, and partners exist to
see the fire. Every endpoint that joins a detection to a site requires staff.

---

## Running it yourself

```bash
# Engine
cd backend && pip install -r requirements-dev.txt
python -m pytest --import-mode=importlib        # 72 tests
uvicorn app.main:app --port 8000

# Console
cd frontend && npm install && npm run dev

# Reproduce the data (a free FIRMS key; weather needs none)
FIRMS_MAP_KEY=... python scripts/fetch_firms.py    # both regions
python scripts/fetch_weather.py                    # real observed hourly weather

# Measure the AI yourself
GROQ_API_KEY=... python scripts/eval_advisor.py --cases 10
OLLAMA_URL=http://localhost:11434 OLLAMA_MODEL=qwen2.5:14b python scripts/eval_advisor.py
```

## Where to look

| | |
|:--|:--|
| `docs/DEMO_SCRIPT.md` | The 90-second path, with the hard questions answered |
| `docs/RELIABILITY.md` | Measured latencies, the AI evaluation, failure modes, limits |
| `docs/FIRE_SPREAD.md` | The spread model, its calibration, and the path to a trained one |
| `docs/SECURITY.md` | Threat model, controls, tests, and gaps |
| `backend/app/scoring.py` | The risk model — no black box |
| `backend/app/spread.py` | Rothermel, with every coefficient sourced |
| `backend/app/advisor.py` | Grounding, guardrails, validation, fallback |
| `backend/scripts/eval_advisor.py` | Reproduce our AI numbers |

## What we would do next

1. Validate the spread model against EFFIS perimeters for Galicia and Tunisia — the first real
   error distribution, and no GPU needed.
2. Add a 30 m DEM. Slope enters Rothermel squared, so the uniform-slope assumption is our
   largest error term today.
3. Put one physical sensor on one real fence. Everything about the mesh is honest except that
   it does not exist yet.
4. Find one pilot site owner. The product logic is ahead of the customer evidence, and we know
   which of those is harder.

*Built by two people. Fire data © NASA FIRMS; weather from Open-Meteo and weatherapi.com; map
data © OpenStreetMap contributors. The risk score supports decisions and is not a validated
prediction model. The fire service decides all firefighting actions.*
