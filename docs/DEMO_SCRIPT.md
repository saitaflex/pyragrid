# PyraGrid — 90-second demo script

One path, four screens, no detours. Everything below is real NASA FIRMS data from the
August 2025 Galicia fire season (17,579 VIIRS detections, 8–25 August 2025).

**Before you start:** log in as `admin@demo.eu` / `demo1234` and open these four tabs in
order. Every page reads the replay clock from `?at=`, so each tab opens on the right moment.

| Tab | URL |
|:--|:--|
| 1 | `/?at=2025-08-16T15:00:00Z` |
| 2 | `/incidents/ES-OU-009_20250808T1500?at=2025-08-16T15:00:00Z` |
| 3 | `/sensors?at=2025-08-16T15:00:00Z` |
| 4 | `/history` |

Generate the AI advice on tab 2 **before** you present, so the panel is already populated —
the call takes up to 15 s and you do not have 15 s to spare. Then re-generate live only if
you are comfortably ahead of time.

---

## 0:00 – 0:12 · The problem (tab 1, portfolio)

> "A company with assets in the countryside — solar farms, vineyards, warehouses — finds out
> a wildfire is coming from a phone call or the news. Public fire data exists, but nobody
> turns it into *what this company should do in the next hour*."

Point at the ranked list. Say the words **"this is real NASA satellite data from the
Galicia fires last August, not a mock-up"** — the source badge in the top bar says
*NASA FIRMS*.

## 0:12 – 0:28 · Ranking is the product (tab 1)

> "Nineteen of these twenty sites went HIGH during that season. When everything is red, an
> alert is useless. So we rank by *what it means for this company*: a critical solar farm
> with the fire heading for it outranks a shed with the wind blowing the other way."

Click **Play** for 2–3 seconds so the judge sees the levels move, then pause. Don't narrate
the slider — just let it move once.

## 0:28 – 0:48 · Why, not just what (tab 2, incident)

**Solar Larouco 03** — HIGH, score 71, *"Fire 6.1 km S, wind toward site"*.

> "Every score opens up. Proximity 26.5, wind alignment 15.3, weather 9.3, fuel 12, asset
> vulnerability 8. No black box — the operator can see the reasoning and disagree with it."

Point at the access routes, then the protocol actions below.

## 0:48 – 1:06 · Ground truth (tab 3, sensors)

> "Satellites see a 375-metre pixel every few hours. On this site, 35 solar sensors on the
> fence and the forest edge: twenty are fine, five are warm, four are in fire — and the mesh
> puts the fire inside a 700-metre circle. That is the difference between 'a fire is nearby'
> and 'it's at your south fence'."

## 1:06 – 1:22 · The AI, described honestly (back to tab 2, advisor panel)

> "The advisor writes the operator's next actions. It can only cite evidence keys we hand it —
> it cannot invent a road or a sensor. It is blocked from ever giving firefighting tactics;
> that's the fire service's job, and the panel shows how many suggestions the safety rules
> threw away. Every suggestion needs a human to approve it."

Click **Approve** on one suggestion. If the panel shows a blocked count, say the number out
loud — a guardrail that visibly fires is worth more than one you claim.

## 1:22 – 1:30 · Close on the validation number (tab 4, history)

> "Replayed against the real season: ten of our twenty sites were reached by fire. We raised
> an alert on every one of them — zero missed — with a median of four days' warning."

Stop talking. Don't offer a tour of the other twelve pages.

---

## If a judge asks

- **"Is the AI doing the detection?"** — No, and be straight about it: detection is satellite
  data plus a transparent weighted score you can audit. The model writes and prioritises the
  response, inside guardrails. If it fails, `template_engine` produces the same actions from
  the protocol rules and the badge says *Template (no AI)*.
- **"Why is everything red?"** — Because that fire season really was region-wide. It's the
  argument for ranking and explanation over alerting.
- **"Median four days of warning sounds too good."** — It is generous: in a season that
  large, sites go HIGH early and stay there, so the number measures when the region lit up as
  much as a precise prediction. High recall, weaker precision. `docs/RELIABILITY.md` says so.
- **"Do the sensors exist?"** — No hardware yet. The mesh is simulated from the same real
  detections, and that's the top of the build list. Don't claim otherwise.

## Rehearsal checklist

- [ ] Run it once with a timer. Over 90 s means cut words, not screens.
- [ ] Advisor pre-generated on tab 2.
- [ ] Zoom at 100%, browser at full screen, notifications off.
- [ ] `/api/health` green and `/system` showing Database ONLINE before you present.
- [ ] Record one clean take as a fallback in case the live app fails on the night.
