# PyraGrid — 90-second demo script

One path, four screens, no detours. Every number is real NASA FIRMS data: 17,937 VIIRS
detections, 8–25 August 2025, across both operating regions — **northwest Tunisia** (358
detections: Ghardimaou, Béja, Zaghouan, Bou Arada) and **Galicia, Spain** (17,579, the
August 2025 fire season).

Open in Tunisia, because the escalation there is clean and the room is Tunisian. Close on
Galicia, because that is where the scale and the validation numbers are.

**Before you start:** log in as `admin@demo.eu` / `demo1234` and open these tabs in order.
Every page reads the replay clock from `?at=`, so each tab opens on the right moment.

| Tab | URL | Shows |
|:--|:--|:--|
| 1 | `/?at=2025-08-20T15:00:00Z` | Portfolio, Tunisia quiet |
| 2 | `/?at=2025-08-24T15:00:00Z` | Same portfolio, Tunisia critical |
| 3 | `/incidents/TN-JN-001_20250824T0300?at=2025-08-24T15:00:00Z` | The incident and the advisor |
| 4 | `/sensors?at=2025-08-24T15:00:00Z` | The mesh localising the fire |
| 5 | `/history` | The Galicia validation numbers |

Generate the AI advice on tab 3 **before** you present — the call takes up to 15 s and you do
not have 15 s to spare. Re-generate live only if you are comfortably ahead.

---

## 0:00 – 0:12 · The problem (tab 1)

> "A company with assets in the countryside — a cork oak concession in Ghardimaou, a solar
> farm at Zaghouan, a substation at Djebibina — finds out a wildfire is coming from a phone
> call or from the news. Public satellite fire data exists. Nobody turns it into *what this
> company should do in the next hour*."

Point at **Cork Oak Block Ghardimaou**: ELEVATED, *"No fire within 25 km"*. Say the words
**"this is real NASA satellite data from last August, not a mock-up"** — the top bar source
badge reads *NASA FIRMS*.

## 0:12 – 0:26 · Four days later (tab 2)

Same site, four days on: **CRITICAL, score 79, "Fire 1.3 km S, wind toward site."**

> "Nothing about the site changed. The fire moved, the wind turned, and the ranking moved it
> to the top on its own."

Then, in one sentence, the honest scale note:

> "Our Spanish sites are almost all red in this period — that season really was region-wide.
> When everything is red, an alert is useless, and ranking is the product."

## 0:26 – 0:46 · Why, not just what (tab 3)

> "Every score opens up: proximity, wind alignment, weather, fuel, and how vulnerable this
> particular asset is. No black box — the operator sees the reasoning and can disagree with
> it."

Point at the access routes, then the protocol actions underneath.

## 0:46 – 1:04 · Ground truth (tab 4)

> "Satellites see a 375-metre pixel every few hours. On this site there are 49 solar sensors,
> placed on real OpenStreetMap features — the fence line, farm buildings, the forest edge.
> Forty-three are fine, one is warm, one is in fire, three have gone silent. The mesh puts
> the fire inside a 323-metre circle. That is the difference between 'a fire is nearby' and
> 'it is at your southern boundary'."

## 1:04 – 1:20 · The AI, described honestly (back to tab 3)

> "The advisor writes the operator's next actions. It can only cite evidence we hand it — it
> cannot invent a road or a sensor. It is blocked from ever giving firefighting tactics; that
> is the fire service's job. The panel shows how many suggestions the safety rules threw
> away, and every suggestion needs a named human to approve it."

Click **Approve** on one suggestion. If a blocked count is showing, say the number out loud —
a guardrail that visibly fires beats one you merely claim.

## 1:20 – 1:30 · Close on the validation (tab 5)

> "Replayed against the real season across both regions: eleven of the twenty-eight sites
> were reached by fire. We raised an alert on every one — zero missed — with a median of four
> days' warning."

Stop talking. Do not offer a tour of the other twelve pages.

---

## If a judge asks

- **"Is the AI doing the detection?"** — No, and say so plainly: detection is satellite data
  plus a transparent weighted score you can audit line by line. The model writes and
  prioritises the *response*, inside guardrails. If it fails, the template engine produces
  the same actions from the protocol rules and the badge reads *Template (no AI)*.
- **"Why are the Spanish sites all red?"** — Because that fire season was region-wide. It is
  the argument for ranking and explanation over alerting.
- **"Median four days of warning sounds too good."** — It is generous. In a season that
  large, sites go HIGH early and stay there, so the figure measures when the region lit up as
  much as a per-site prediction. High recall, weaker precision. `docs/RELIABILITY.md` says
  exactly that.
- **"Do the sensors exist?"** — No hardware yet. The mesh is simulated from the same real
  detections; the *positions* are real OSM features. It is the top of the build list. Don't
  claim otherwise.
- **"Why Tunisia and Spain?"** — Galicia is the pilot region in the business plan; Tunisia is
  the second operating region. Both carry real FIRMS data in the demo, fetched by
  `scripts/fetch_firms.py` from `config.REGIONS`.

## Rehearsal checklist

- [ ] Run it once with a timer. Over 90 s means cut words, not screens.
- [ ] Advisor pre-generated on tab 3.
- [ ] Zoom at 100%, browser full screen, notifications off.
- [ ] `/api/health` green and `/system` showing Database ONLINE before you present.
- [ ] Record one clean take as a fallback in case the live app fails on the night.
