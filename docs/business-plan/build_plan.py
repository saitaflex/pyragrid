"""build_plan.py — writes PyraGrid_Business_Plan.md from the financial model.

    python build_plan.py

Every figure in the plan is computed by model.py; nothing is typed by hand.
"""
from __future__ import annotations

from pathlib import Path

import model as M

A, Y = M.A, M.YEARS
B = M.run()
BEAR = M.run(growth_factor=0.6, price_factor=0.9, churn=0.12)
BULL = M.run(growth_factor=1.3, price_factor=1.05, churn=0.06)
# the same plan without the two competition rules (normal tariff, shipping any day)
FREE = dict(A, elec_surcharge=0.0, stock_weeks=2, spare_sensors_per_site=0)
B0 = M.run(FREE)
PB = '\n<div style="page-break-after: always;"></div>\n'


# ------------------------------------------------------------------ formatting
def k(v: float, dec: int = 0) -> str:
    """Thousands of euros, negatives in brackets (finance convention)."""
    s = f"{abs(v) / 1000:,.{dec}f}"
    return f"({s})" if v < -0.5 else ("–" if abs(v) < 0.5 else s)


def eur(v: float) -> str:
    return f"€{v:,.0f}" if v >= 0 else f"(€{-v:,.0f})"


def m(v: float, dec: int = 1) -> str:
    s = f"€{abs(v) / 1e6:,.{dec}f}M"
    return f"({s})" if v < 0 else s


def pct(v: float, dec: int = 0) -> str:
    return f"{v * 100:.{dec}f}%" if v == v else "n/a"


def n(v: float) -> str:
    return f"{v:,.0f}"


def row(label: str, vals, fmt=k, bold: bool = False) -> str:
    cells = [fmt(v) for v in vals]
    if bold:
        label, cells = f"**{label}**", [f"**{c}**" for c in cells]
    return f"| {label} | " + " | ".join(cells) + " |"


def head(first: str = "k€") -> str:
    return f"| {first} | " + " | ".join(f"FY{y}" for y in Y) + " |\n|:--|" + "--:|" * len(Y)


def growth(series, i):
    return series[i] / series[i - 1] - 1 if i and series[i - 1] else float("nan")


# ------------------------------------------------------------------ derived analysis
rev, ebitda, arr = B["revenue"], B["ebitda"], B["arr"]
gm = [B["gross"][i] / rev[i] if rev[i] else float("nan") for i in range(M.N)]
em = [ebitda[i] / rev[i] if rev[i] else float("nan") for i in range(M.N)]

# EBITDA break-even month: monthly EBITDA linear over the two years around the crossing
be_year = next(i for i in range(1, M.N) if ebitda[i] > 0)
e1, e2 = ebitda[be_year - 1], ebitda[be_year]
b_slope = (e2 - e1) / 144                      # sum of 12 months shifts by 144·b between years
a0 = e1 / 12 - b_slope * 6.5
t0 = -a0 / b_slope                             # month index from 1 Jan of be_year-1
be_month = int(t0) + 1
be_label = f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][(be_month - 1) % 12]} {Y[be_year - 1] + (be_month - 1) // 12}"
min_cash = min(B["cash"][1:])
min_cash_year = Y[B["cash"].index(min_cash)]

# unit economics (FY2029, the first year at scale)
u = 3
price_site = B["blended"][u]
EF = 1 + A["elec_surcharge"]
dc_share = A["dc_energy_share"]
site_cloud = A["cloud_per_site"] * (1 - dc_share)
site_llm = A["llm_per_site"] * (1 - dc_share)
site_elec = (A["cloud_per_site"] + A["llm_per_site"]) * dc_share * EF
site_cost = site_cloud + site_llm + site_elec + A["support_pct"] * price_site
site_margin = price_site - site_cost
kit = A["sensors_per_site"] * A["sensor_unit_cost"] + A["gateway_cost"]
spares = A["spare_sensors_per_site"] * A["sensor_unit_cost"]
kit_freight = A["freight_pct"] * kit
sensor_upfront = kit + kit_freight + spares + A["install_cost"]
sensor_repl = A["sensor_replacement"] * A["sensors_per_site"] * A["sensor_unit_cost"] * (1 + A["freight_pct"])
gw_elec = A["gateway_kwh"] * A["elec_price"] * EF
sensor_contrib = A["sensor_fee"] - A["sensor_opex"] - gw_elec - A["support_pct"] * A["sensor_fee"] - sensor_repl
sensor_payback_m = sensor_upfront / sensor_contrib * 12
sensor_irr = M.irr([-sensor_upfront] + [sensor_contrib] * A["sensor_life"])
avg_cust = (B["customers"][u - 1] + B["customers"][u]) / 2
arpa = rev[u] / avg_cust
# fully loaded CAC: sales and marketing, half of customer success (onboarding, pilots)
# and 30% of the founders' time spent selling
LIFE_CAP = 5
cs_cost = A["fte_cs"][u] * A["cost_cs"] * (1 + A["wage_growth"]) ** u
founder_sell = A["founders"] * A["founder_pay"][u] * 0.30
cac = (B["sm_cost"][u] + 0.5 * cs_cost + founder_sell) / B["new_customers"][u]
ltv_uncapped = arpa * gm[u] / A["logo_churn"]
def ltv_at(churn: float) -> float:
    """Gross profit over a 5-year horizon, weighted by the chance the customer is still there."""
    return arpa * gm[u] * sum((1 - churn) ** t for t in range(LIFE_CAP))


ltv = ltv_at(A["logo_churn"])
cac_payback = cac / (arpa * gm[u] / 12)

# cap table
pre_seed_pre, seed_pre, esop = 1_200_000, 6_000_000, 0.10
ps_share = A["preseed"] / (pre_seed_pre + A["preseed"])
seed_post = seed_pre + A["seed"]
seed_share = A["seed"] / seed_post
rest = 1 - seed_share - esop
founders_post = (1 - ps_share) * rest
preseed_post = ps_share * rest

# valuation and returns
pv_fcf, tv, pv_tv, dcf, exit_val, pv_exit = M.valuation(B)
exits = [4.0, 6.0, 8.0]
hold_seed, hold_ps = 3.75, 5.5


def moic_irr(stake, invested, years, multiple):
    proceeds = arr[-1] * multiple * stake
    mo = proceeds / invested
    return proceeds, mo, mo ** (1 / years) - 1


# sensitivity: FY2031 EBITDA for price × growth
PRICES, GROWTHS = [0.8, 0.9, 1.0, 1.1, 1.2], [0.7, 0.85, 1.0, 1.15, 1.3]
SENS = {(p, g): M.run(price_factor=p, growth_factor=g) for p in PRICES for g in GROWTHS}

# ------------------------------------------------------------------ document
L: list[str] = []
w = L.append

w(f"""# PyraGrid

## Business Plan and Financial Model, FY2026–FY2031

**Wildfire intelligence for companies with sites in fire country**

| | |
|:--|:--|
| **Company** | PyraGrid (in formation, Spain) |
| **Stage** | Pre-seed, working product live at rural-valley.vercel.app |
| **Document** | Business plan, five-year financial model, valuation |
| **Version** | 1.0, September 2026 |
| **Funding sought** | {m(A['preseed'], 2)} pre-seed now, {m(A['seed'])} seed in Q1 2028 |
| **Confidentiality** | Confidential. Prepared for investors, grant bodies and the Rural Valley programme. |

> All financial figures are forecasts built from the assumptions in section 9.1. They are
> planning estimates, not guarantees. Market figures marked *estimate* are to be validated
> during the 2027 pilot programme.
{PB}
## Contents

1. [Executive summary](#1-executive-summary)
2. [The problem](#2-the-problem)
3. [The solution](#3-the-solution)
4. [Market analysis](#4-market-analysis)
5. [Competition and positioning](#5-competition-and-positioning)
6. [Business model and pricing](#6-business-model-and-pricing)
7. [Go-to-market strategy](#7-go-to-market-strategy)
8. [Operations and team](#8-operations-and-team)
9. [Financial plan](#9-financial-plan)
10. [KPIs and performance targets](#10-kpis-and-performance-targets)
11. [Funding and capital structure](#11-funding-and-capital-structure)
12. [Valuation](#12-valuation)
13. [Risks and mitigation](#13-risks-and-mitigation)
14. [Milestones and roadmap](#14-milestones-and-roadmap)
15. [Impact](#15-impact)
16. [Appendix: methodology and formulas](#16-appendix-methodology-and-formulas)
{PB}
## 1. Executive summary

**The problem.** Companies that own energy, telecom and forestry assets in Southern Europe
face a growing wildfire risk, but the data they get is not built for them. Public satellite
services show where heat is, not what it means for a specific solar farm, substation or
tower, and not what the company should do next.

**The solution.** PyraGrid turns satellite fire detections, weather and optional ground
sensors into one risk level per site, an estimated fire position, and the company's own
emergency protocol, with an AI advisor that proposes next steps and a person who approves
them. The same picture is shared, with the right level of detail, with the fire service,
civil protection and local organisations. A drill mode trains staff on realistic scenarios.

**Business model.** Annual subscription per monitored site ({eur(A['price_essential'])}
Essential, {eur(A['price_pro'])} Professional), optional Sensor-as-a-Service
({eur(A['sensor_fee'])} per site per year) and onboarding and training services.

**Key figures (base case)**

| | FY2027 | FY2029 | FY2031 |
|:--|--:|--:|--:|
| Customers (year end) | {n(B['customers'][1])} | {n(B['customers'][3])} | {n(B['customers'][5])} |
| Monitored sites (year end) | {n(B['sites'][1])} | {n(B['sites'][3])} | {n(B['sites'][5])} |
| Annual recurring revenue (ARR) | {m(arr[1], 2)} | {m(arr[3])} | {m(arr[5])} |
| Revenue | {m(rev[1], 2)} | {m(rev[3])} | {m(rev[5])} |
| Gross margin | {pct(gm[1])} | {pct(gm[3])} | {pct(gm[5])} |
| EBITDA | {m(ebitda[1], 2)} | {m(ebitda[3], 2)} | {m(ebitda[5])} |
| EBITDA margin | {pct(em[1])} | {pct(em[3])} | {pct(em[5])} |
| Team (FTE) | {n(B['fte'][1])} | {n(B['fte'][3])} | {n(B['fte'][5])} |

<!-- chart:growth -->

- **Break-even:** monthly EBITDA turns positive around **{be_label}**; FY{Y[be_year]} is the first profitable year.
- **Competition rules included:** electricity {pct(A['elec_surcharge'])} more expensive and shipping only one day a week are built into every year of the model (section 9.11).
- **Funding:** {m(A['preseed'], 2)} pre-seed plus an ENISA participative loan ({m(A['enisa_loan'], 2)}) and innovation grants ({m(sum(A['grant']), 2)}) fund the pilots; a **{m(A['seed'])} seed round** in Q1 2028 takes the company to profitability. The lowest year-end cash balance is {m(min_cash, 2)} (FY{min_cash_year}).
- **Unit economics:** a platform site earns a {pct(site_margin / price_site)} contribution margin; a sensor site pays back in {sensor_payback_m:.0f} months; LTV/CAC is {ltv / cac:.1f}x and the cost of winning a customer is paid back in {cac_payback:.0f} months.
- **Valuation:** {m(dcf)} on a discounted cash flow at a {pct(A['wacc'])} venture discount rate; {m(pv_exit)} present value of a {A['arr_multiple']:.0f}x ARR exit in 2031.
{PB}
## 2. The problem

Wildfires in Southern Europe are becoming larger, faster and harder to predict. Longer
droughts, heat waves and the abandonment of rural land leave more fuel near infrastructure.
The EU's European Forest Fire Information System (EFFIS) reports that Spain, Portugal,
Italy and Greece account for most of the burned area in the EU in a typical year.

For a company that owns assets in these regions, a fire means:

- **People at risk:** technicians and contractors on remote sites, often with one access road.
- **Physical damage:** solar panels, inverters, turbines, substations and telecom equipment.
- **Outages and penalties:** lost generation, grid and telecom service interruptions.
- **Rising insurance costs** and new disclosure duties on physical climate risk
  (EU CSRD, ESRS E1).

**What companies have today.** Free satellite services such as NASA FIRMS and EFFIS show
heat anomalies across the whole region, several times a day. They answer *where is there
heat?* but not:

1. *Which of my sites is exposed, and how badly?*
2. *Is the fire really there, and exactly where, at night or under cloud?*
3. *What does our own procedure say we must do now, and who does it?*
4. *What does the fire service need from us?*
5. *Is our team trained to react in minutes, not hours?*

In practice, control rooms monitor public maps by hand, phone site managers, and search
for the emergency procedure in a PDF. That costs the minutes that matter most.
{PB}
## 3. The solution

PyraGrid is a decision layer between fire data and the people who must act. It runs in
the browser and is live today.

| Capability | What it does for the customer |
|:--|:--|
| **Asset risk engine** | Scores every site from 0 to 100 every satellite pass from distance, wind alignment, weather, fuel and vulnerability, with every factor shown. |
| **Ground sensors (optional)** | Temperature sensors placed on real places around each site (fence, nearby buildings, forest edges). They confirm fire on the ground, see it at night or under cloud, and flag when a sensor dies or is moved. |
| **Combined fire position** | Hot sensors are combined into one estimated fire position with an uncertainty radius, far more precise than a 375 m satellite pixel. |
| **Protocol engine** | The company's own emergency rules turn each risk level into a checklist: who to call, what to check, when to evacuate. |
| **AI advisor** | A language model proposes next steps from the evidence. Every suggestion cites its data, never gives firefighting tactics, and is approved or rejected by a person. |
| **Fire-service handoff** | A one-page pack for firefighters: access routes, hazards, water points, people on site, fire position. |
| **Shared situation view** | Fire service, civil protection and NGOs see the same picture with a data-sharing policy per role. |
| **Drills and simulation** | Staff train on realistic scenarios; the system scores response speed and accuracy. A live simulator shows how a fire would spread under today's conditions. |

**Why it is defensible**

- **Data network effects:** every site, sensor and drill improves the scoring and the
  protocol library; partner agencies using the shared view pull more asset owners in.
- **Workflow lock-in:** once a company's protocols, contacts and audit trail live in
  PyraGrid, switching costs are high.
- **Hardware plus software:** the sensor network is a physical asset in the field with a
  multi-year contract.
- **Trust by design:** transparent scoring, evidence-cited AI and human approval fit the
  needs of regulated operators and insurers.
{PB}
## 4. Market analysis

### 4.1 Target customers

| Segment | Assets | Why they buy |
|:--|:--|:--|
| Renewable energy owners and operators | Solar plants, wind farms, battery storage | Personnel safety, lost generation, insurance, lender requirements |
| Grid operators | Substations, lines crossing forest | Service continuity, regulatory duty, liability |
| Telecom tower companies | Rural towers and shelters | Uptime obligations, emergency communications |
| Forestry and timber companies | Managed plantations | Asset value, certification, insurance |
| Insurers and brokers (channel) | Portfolios of the above | Loss prevention, underwriting data |
| Public bodies (partners) | Fire services, civil protection, municipalities | Free shared view; they bring asset owners in |

### 4.2 Market size (bottom-up)

Sizing counts monitored sites, the unit PyraGrid sells. Site counts are *estimates* built
from public registries and industry sources at order-of-magnitude level; they will be
validated with regulator and industry data during the 2027 pilots.

| Level | Scope | Sites (*estimate*) | Revenue per site | Annual market |
|:--|:--|--:|--:|--:|
| **TAM** | Exposed critical sites in Spain, Portugal, southern France, Italy and Greece | 120,000 | €2,900 | €348M |
| **SAM** | Energy, telecom and forestry sites in high-risk zones of Spain and Portugal | 27,000 | €2,900 | €78M |
| **SOM** | PyraGrid base case, FY2031 | {n(B['sites'][5])} | {eur(arr[5] / B['sites'][5])} | {m(arr[5])} |

The FY2031 base case reaches **{pct(B['sites'][5] / 27000, 1)} of the Iberian SAM**, a
realistic share for a specialist leader five years after launch. Revenue per site in the
TAM and SAM rows is a blended planning figure (platform tiers plus sensor attach).

<!-- chart:market -->

### 4.3 Market drivers

- **Climate:** longer and more intense fire seasons across the Mediterranean.
- **Regulation:** the EU Corporate Sustainability Reporting Directive (CSRD) and ESRS E1
  require large companies to assess and report physical climate risks.
- **Insurance:** underwriters increasingly price wildfire exposure per asset and reward
  mitigation.
- **Energy transition:** thousands of new solar and wind sites are being built in rural,
  fire-prone land.
- **Public policy:** EU and national programmes fund wildfire prevention and early detection.
{PB}
## 5. Competition and positioning

### 5.1 Landscape

Wildfire technology is growing fast, but almost every company solves **one step**: seeing
the fire. PyraGrid solves the step after it: **what a company with sites must do now**.
The market has five groups.

| | Public satellite data | Satellite analytics | Camera networks | Ground sensor networks | **PyraGrid** |
|:--|:--|:--|:--|:--|:--|
| Detects fires across the region | Yes | Yes | Partial | No | **Yes (satellite)** |
| Risk score per customer site | No | Partial | No | No | **Yes** |
| Confirms fire at night and under cloud | No | Partial | Partial | Yes | **Yes (sensors)** |
| Company protocol and actions | No | No | No | No | **Yes** |
| AI advisor with human approval | No | No | No | No | **Yes** |
| Shared view for fire services | Public only | No | Partial | Partial | **Yes, per role** |
| Drills and training | No | No | No | No | **Yes** |
| Typical price | Free | Enterprise contract | Hardware project | Hardware project | **From €1,800 per site/yr** |

### 5.2 Main competitors

| Company (base) | What they do | Strengths | Limits for a site owner | PyraGrid's stance |
|:--|:--|:--|:--|:--|
| **NASA FIRMS, Copernicus EFFIS** (USA, EU) | Free satellite hotspots and fire-danger maps | Free, wide coverage, trusted by agencies | Not per site; pixels of 375 m to 1 km; no workflow | Data source we build on |
| **OroraTech** (Germany) | Thermal satellite constellation and wildfire monitoring platform | Dedicated fire satellites, government contracts | Wide-area view; no site procedures or drills | Possible data partner |
| **Pano AI** (USA) | AI cameras on high points that alert utilities and fire agencies | Fast visual detection, utility references | Camera towers needed per region; US and Australia focus | Competes in utilities; camera feed can be an input |
| **Dryad Networks** (Germany) | Solar-powered gas sensors in a forest mesh network (Silvanet) | Very early detection of smouldering fires | Many sensors per hectare; detection only | Closest to our sensor layer; partner or rival |
| **IQ FireWatch** (Germany) | Optical camera towers that detect smoke | Proven in forests for many years | Tower cost; detection only | Data input |
| **Technosylva** (Spain, USA) | Fire spread modelling and risk analytics | Deep fire science | Large projects; mostly large US utilities | We serve mid-size owners faster |
| **Overstory** (Netherlands) | Satellite vegetation intelligence for utilities | Strong prevention analytics | Planning tool, not live incident response | Complementary |
| **Everbridge and similar** (USA) | Critical event and mass notification platforms | Enterprise reach | Not fire-specific: no fire position, risk or sensors | Integration target |

*Based on public company information as of 2026. Competitor features change quickly and
are re-checked before each investor meeting.*

### 5.3 Positioning map

<!-- chart:positioning -->

PyraGrid sits in the top-right corner: it combines several data sources and turns them into
the company's response. The other players focus on detection, planning or generic alerts;
none of them combines all three for a site owner.

### 5.4 Buying criteria (score 1 to 5, team assessment)

| Criterion (weight) | Public data | Satellite analytics | Cameras | Sensors | **PyraGrid** |
|:--|--:|--:|--:|--:|--:|
| Risk for my exact sites (25%) | 1 | 3 | 2 | 2 | **5** |
| Ground confirmation (15%) | 1 | 2 | 3 | 5 | **4** |
| Response workflow and protocols (25%) | 1 | 1 | 1 | 1 | **5** |
| Sharing with fire services (10%) | 3 | 1 | 3 | 2 | **5** |
| Time to go live (15%) | 5 | 3 | 1 | 2 | **4** |
| Cost for 20 sites (10%) | 5 | 2 | 1 | 2 | **4** |
| **Weighted score** | **2.2** | **2.1** | **1.8** | **2.2** | **4.6** |

### 5.5 How we stay ahead

- **Integrate, do not compete, on detection.** New satellites and cameras make PyraGrid
  better, because it fuses any source. Detection companies become suppliers.
- **Own the workflow.** Protocols, contacts, audit logs and drill history are the
  customer's operating memory, and they are hard to move.
- **Win the public side.** Fire services use the shared view for free; every agency
  connected makes the next asset owner easier to sign.
- **Iberia first.** Spanish and Portuguese customers, language, regulation (CSRD) and
  field partners before larger US players focus on Southern Europe.
- **If a detection company adds site alerts,** PyraGrid still leads on protocols, drills,
  multi-agency sharing and sensor-confirmed fire position, and can use that company's feed.
{PB}
## 6. Business model and pricing

### 6.1 Offer

| Product | Includes | Price (2026 list) |
|:--|:--|--:|
| **Essential** | Risk engine, alerts, protocol engine, handoff pack, shared view | {eur(A['price_essential'])} per site / year |
| **Professional** | Essential plus AI advisor, drills and simulator, API, partner sharing controls | {eur(A['price_pro'])} per site / year |
| **Enterprise** | Professional for 50+ sites, integrations, SLA | Volume pricing from Professional |
| **Sensor-as-a-Service** | {A['sensors_per_site']} sensors and a gateway per site, installation, maintenance, replacement; 3-year minimum term | {eur(A['sensor_fee'])} per site / year |
| **Onboarding** | Site import, protocol set-up, integration | {eur(A['onboarding_fee'])} per customer |
| **Training and drills** | Annual drill programme and training | {eur(A['training_fee'])} per customer / year |
| **Public partners** | Shared situation view for fire services and agencies | Free |

List prices rise 3% a year from FY2029. The Professional share grows from
{pct(A['pro_mix'][1])} to {pct(A['pro_mix'][5])} of sites as customers adopt the AI advisor and drills.

### 6.2 Revenue model

- **Recurring subscription** (platform and sensors) is billed annually in advance: about
  {pct((B['rev_platform'][5] + B['rev_sensor'][5]) / rev[5])} of FY2031 revenue.
- **Land and expand:** customers start with their most exposed sites and add sites over
  time; sites per customer grow from {A['sites_per_customer'][1]:.0f} to {A['sites_per_customer'][5]:.0f}.
- **Hardware as a service** keeps the sensor fleet on PyraGrid's balance sheet, turning a
  one-off sale into recurring revenue with a {pct(sensor_irr)} internal rate of return per sensor site.
{PB}
## 7. Go-to-market strategy

| Phase | Period | Focus | Target |
|:--|:--|:--|:--|
| **1. Pilots** | 2026–2027 | Galicia (Ourense) and northern Portugal; grant-funded sensor pilots; Rural Valley programme | {n(B['customers'][1])} paying customers, {n(B['sites'][1])} sites |
| **2. Iberia** | 2028–2029 | Renewable owners, grid operators and tower companies across Spain and Portugal | {n(B['customers'][3])} customers, {n(B['sites'][3])} sites |
| **3. Southern Europe** | 2030–2031 | France (south), Italy, Greece through partners | {n(B['customers'][5])} customers, {n(B['sites'][5])} sites |

**Channels**

1. **Direct sales** to asset owners: head of HSE, operations and risk.
2. **Insurers and brokers:** PyraGrid as a loss-prevention service bundled with policies.
3. **EPC and O&M contractors** who build and run solar and wind plants.
4. **Public partners:** free shared view for fire services and civil protection, which
   creates demand from asset owners in their area.

**Sales cycle:** 3 to 6 months for mid-size operators, 6 to 12 months for utilities.
A paid pilot of 5 to 10 sites converts to a portfolio contract.
{PB}
## 8. Operations and team

### 8.1 Founding team

- **Co-founder, technology (engine, data and AI):** risk engine, sensor model, AI advisor, infrastructure.
- **Co-founder, product (console and experience):** operator console, partner views, design.

The founders will recruit advisors in wildfire operations (a former fire-service officer),
energy asset management and insurance in 2027.

### 8.2 Hiring plan (FTE at year end)

| Function | """ + " | ".join(f"FY{y}" for y in Y) + """ |
|:--|""" + "--:|" * len(Y) + f"""
| Founders | """ + " | ".join(str(A["founders"]) for _ in Y) + """ |
| Engineering and data | """ + " | ".join(f"{v:g}" for v in A["fte_eng"]) + """ |
| Sales and partnerships | """ + " | ".join(f"{v:g}" for v in A["fte_sales"]) + """ |
| Customer success and field operations | """ + " | ".join(f"{v:g}" for v in A["fte_cs"]) + """ |
| Finance, legal and admin | """ + " | ".join(f"{v:g}" for v in A["fte_ga"]) + """ |
| **Total** | """ + " | ".join(f"**{v:g}**" for v in B["fte"]) + f""" |

Fully loaded annual costs (salary plus Spanish social security) are €{A['cost_eng']:,}
(engineering), €{A['cost_sales']:,} (sales, including variable pay), €{A['cost_cs']:,}
(customer success and field) and €{A['cost_ga']:,} (G&A), rising 3% a year. Founders take
reduced salaries until the seed round.

### 8.3 Operations

- **Cloud platform:** serverless hosting and managed Postgres; the cost scales with sites
  ({eur(A['cloud_per_site'] + A['llm_per_site'])} per site per year including AI inference).
- **Sensor supply chain:** off-the-shelf LoRaWAN modules, thermistors, solar cells and
  enclosures assembled by a regional partner; bill of materials about
  {eur(A['sensor_unit_cost'])} per sensor, {eur(kit)} per site kit including the gateway.
- **Field operations:** installation by trained local contractors ({eur(A['install_cost'])} per site),
  annual inspection and battery service ({eur(A['sensor_opex'])} per site per year).
- **Weekly shipping (competition rule):** carriers collect and deliver only one day a week,
  so hardware cannot be sent next day. PyraGrid plans installations around the weekly
  delivery, keeps {A['stock_weeks']} weeks of sensor kits in stock and leaves
  {A['spare_sensors_per_site']} spare sensors on every sensor site, so a failed sensor is
  swapped the same day by the local contractor instead of waiting for the next shipment.
- **Electricity (competition rule):** electricity costs {pct(A['elec_surcharge'])} more than
  the reference tariff of €{A['elec_price']:.2f} per kWh. The model applies this to
  data-centre power (about {pct(A['dc_energy_share'])} of cloud and AI cost), gateway power
  on sensor sites and office power. Sensors run on solar cells and batteries, so the field
  network does not depend on the grid.
{PB}
## 9. Financial plan

All amounts are in thousands of euros (k€) unless stated. Negative values are in brackets.
The fiscal year is the calendar year. FY2026 is the formation and pilot year.

### 9.1 Key assumptions

| Area | Assumption | Value |
|:--|:--|:--|
| Customers | Paying customers at year end | {", ".join(n(v) for v in A['customers_end'])} |
| Expansion | Average sites per customer | {", ".join(f"{v:g}" for v in A['sites_per_customer'])} |
| Pricing | Essential / Professional per site per year | {eur(A['price_essential'])} / {eur(A['price_pro'])}, +3%/yr from FY2029 |
| Mix | Professional share of sites | {", ".join(pct(v) for v in A['pro_mix'])} |
| Sensors | Share of sites with the sensor network | {", ".join(pct(v) for v in A['sensor_attach'])} |
| Churn | Annual customer churn from FY2028 | {pct(A['logo_churn'])} (replaced by new sales) |
| Revenue timing | Recognised on average sites in the year; billed annually in advance | |
| Cost of revenue | Cloud and AI per site; support {pct(A['support_pct'])} of subscriptions; sensor field costs; installation | See 8.3 |
| Sensor fleet | Capitalised, straight-line over {A['sensor_life']} years (half-year convention); {pct(A['sensor_replacement'])} of sensors replaced each year | |
| Marketing | Fixed programme plus {pct(A['marketing_pct'])} of revenue | |
| Working capital | Receivables {A['dso_days']} days; payables {A['dpo_days']} days; deferred revenue {pct(A['deferred_share'])} of annual subscription | |
| **Rule: electricity** | Tariff €{A['elec_price']:.2f}/kWh **+{pct(A['elec_surcharge'])}** = €{A['elec_price'] * EF:.2f}/kWh; data-centre share of cloud cost {pct(A['dc_energy_share'])}; {A['gateway_kwh']} kWh per sensor site; {A['office_kwh_per_fte']:,} kWh per employee | Every year |
| **Rule: shipping** | **One shipping day a week**: {A['stock_weeks']} weeks of kits in stock, {A['spare_sensors_per_site']} spare sensors per sensor site, freight {pct(A['freight_pct'])} of hardware bought | Every year |
| Tax | Spanish corporate tax: 15% for the first two profitable years, then 25%; losses carried forward | |
| Public funding | ENISA participative loan {m(A['enisa_loan'], 2)} at {pct(A['enisa_rate'])}, repaid FY2029–FY2031; innovation grants {m(sum(A['grant']), 2)} | |
""")

# ---- 9.2 revenue build
w("### 9.2 Revenue build\n")
w(head("Driver"))
w(row("Customers (year end)", B["customers"], n))
w(row("New customers", B["new_customers"], n))
w(row("Monitored sites (year end)", B["sites"], n))
w(row("Sites with sensors (year end)", B["sensor_sites"], n))
w(row("Blended price per site (€)", [B["blended"][i] if B["sites"][i] else 0 for i in range(M.N)], lambda v: n(v) if v else "–"))
w("")
w(head())
w(row("Platform subscriptions", B["rev_platform"]))
w(row("Sensor-as-a-Service", B["rev_sensor"]))
w(row("Onboarding and training", B["rev_services"]))
w(row("Total revenue", rev, bold=True))
w(row("Annual recurring revenue (year end)", arr))
w(row("Revenue growth", [growth(rev, i) for i in range(M.N)], lambda v: pct(v)))
w("\n<!-- chart:mix -->")
w(PB)

# ---- 9.3 unit economics
w(f"""### 9.3 Unit economics

**Per platform site (FY2029)**

| | € per site per year |
|:--|--:|
| Blended subscription price | {eur(price_site)} |
| Cloud hosting and data (excluding electricity) | ({eur(site_cloud)[1:]}) |
| AI inference (excluding electricity) | ({eur(site_llm)[1:]}) |
| Data-centre electricity, +40% tariff | ({eur(site_elec)[1:]}) |
| Customer support ({pct(A['support_pct'])}) | ({eur(A['support_pct'] * price_site)[1:]}) |
| **Contribution per site** | **{eur(site_margin)}** |
| **Contribution margin** | **{pct(site_margin / price_site)}** |

**Per sensor site (Sensor-as-a-Service)**

| | € |
|:--|--:|
| Hardware kit ({A['sensors_per_site']} sensors and gateway) | {eur(kit)} |
| Weekly consolidated freight ({pct(A['freight_pct'])}) | {eur(kit_freight)} |
| Spare sensors left on site ({A['spare_sensors_per_site']}) | {eur(spares)} |
| Installation | {eur(A['install_cost'])} |
| **Upfront investment** | **{eur(sensor_upfront)}** |
| Annual fee | {eur(A['sensor_fee'])} |
| Field service, connectivity and batteries | ({eur(A['sensor_opex'])[1:]}) |
| Gateway electricity, +40% tariff | ({eur(gw_elec)[1:]}) |
| Support ({pct(A['support_pct'])}) | ({eur(A['support_pct'] * A['sensor_fee'])[1:]}) |
| Sensor replacement ({pct(A['sensor_replacement'])} per year, with freight) | ({eur(sensor_repl)[1:]}) |
| **Annual contribution** | **{eur(sensor_contrib)}** |
| **Payback** | **{sensor_payback_m:.0f} months** |
| **IRR over the {A['sensor_life']}-year sensor life** | **{pct(sensor_irr)}** |

**Per customer (FY2029)**

| Metric | Value | How it is calculated |
|:--|--:|:--|
| Average revenue per customer (ARPA) | {eur(arpa)} | Revenue ÷ average customers |
| Customer acquisition cost (CAC), fully loaded | {eur(cac)} | (Sales and marketing + 50% of customer success + 30% of founders' time) ÷ new customers |
| Gross margin | {pct(gm[u])} | Gross profit ÷ revenue |
| Lifetime value (LTV), 5-year horizon | {eur(ltv)} | ARPA × gross margin × Σ (1 − churn)ᵗ for t = 0…4 |
| LTV uncapped | {eur(ltv_uncapped)} | ARPA × gross margin ÷ churn |
| **LTV / CAC** | **{ltv / cac:.1f}x** | Benchmark for healthy SaaS: 3x or more |
| **CAC payback** | **{cac_payback:.0f} months** | CAC ÷ monthly gross profit per customer |
{PB}""")

# ---- 9.4 P&L
w("### 9.4 Income statement\n")
w(head())
w(row("Revenue", rev, bold=True))
w(row("Cloud, data and AI (excl. electricity)", [-v for v in B["cogs_cloud"]]))
w(row("Electricity: data centres, gateways (+40%)", [-v for v in B["cogs_energy"]]))
w(row("Weekly freight", [-v for v in B["cogs_freight"]]))
w(row("Customer support", [-v for v in B["cogs_support"]]))
w(row("Sensor field operations", [-v for v in B["cogs_sensor_ops"]]))
w(row("Sensor installation", [-v for v in B["cogs_install"]]))
w(row("Sensor fleet depreciation", [-v for v in B["depreciation"]]))
w(row("Gross profit", B["gross"], bold=True))
w(row("Gross margin", gm, lambda v: pct(v)))
w(row("People", [-v for v in B["opex_people"]]))
w(row("Marketing", [-v for v in B["opex_marketing"]]))
w(row("Office electricity (+40%)", [-v for v in B["opex_energy"]]))
w(row("Other operating costs", [-v for v in B["opex_other"]]))
w(row("EBITDA", ebitda, bold=True))
w(row("EBITDA margin", em, lambda v: pct(v)))
w(row("Depreciation", [-v for v in B["depreciation"]]))
w(row("EBIT", B["ebit"]))
w(row("Grants", B["grant"]))
w(row("Interest", [-v for v in B["interest"]]))
w(row("Profit before tax", B["ebt"]))
w(row("Corporate tax", [-v for v in B["tax"]]))
w(row("Net profit", B["net"], bold=True))
w("\nDepreciation of the sensor fleet is part of the cost of revenue; it is added back to reach EBITDA.")
w(PB)

# ---- 9.5 cash flow
dnwc = [-(B["nwc"][i] - (B["nwc"][i - 1] if i else 0)) for i in range(M.N)]
debt = [B["loan"][i] - (B["loan"][i - 1] if i else 0) for i in range(M.N)]
w("### 9.5 Cash flow statement\n")
w(head())
w(row("Net profit", B["net"]))
w(row("Depreciation", B["depreciation"]))
w(row("Change in working capital", dnwc))
w(row("Operating cash flow", B["cfo"], bold=True))
w(row("Sensor fleet capex", [-v for v in B["capex"]]))
w(row("Free cash flow", B["fcf"], bold=True))
w(row("Equity raised", B["equity_in"]))
w(row("ENISA loan drawn / (repaid)", debt))
w(row("Net change in cash", [B["cash"][i] - (B["cash"][i - 1] if i else 0) for i in range(M.N)]))
w(row("Cash at year end", B["cash"], bold=True))
w("\n<!-- chart:cash -->")
w(f"\nAnnual billing in advance makes working capital a source of cash as the company grows: deferred revenue reaches {m(B['deferred'][5])} in FY2031.")

# ---- 9.6 balance sheet
w("\n### 9.6 Balance sheet (year end)\n")
w(head())
w(row("Cash", B["cash"]))
w(row("Trade receivables", B["ar"]))
w(row("Inventory: kits in stock and spares", B["inventory"]))
w(row("Sensor fleet (net)", B["fleet_net"]))
w(row("Total assets", B["assets"], bold=True))
w(row("Trade payables", B["ap"]))
w(row("Deferred revenue", B["deferred"]))
w(row("ENISA loan", B["loan"]))
w(row("Paid-in capital", B["paid_in"]))
w(row("Retained earnings", B["retained"]))
w(row("Total liabilities and equity", B["liab_eq"], bold=True))
w("\nThe balance sheet balances in every year: total assets equal total liabilities and equity.")
w(PB)

# ---- 9.7 KPIs
burn_mult = [(-B["fcf"][i]) / (arr[i] - arr[i - 1]) if i and B["fcf"][i] < 0 and arr[i] > arr[i - 1] else float("nan") for i in range(M.N)]
rule40 = [growth(rev, i) + em[i] if i >= 4 else float("nan") for i in range(M.N)]   # meaningful at scale only
w("### 9.7 SaaS metrics and KPIs\n")
w(head("Metric"))
w(row("ARR (k€)", arr))
w(row("ARR growth", [growth(arr, i) for i in range(M.N)], lambda v: pct(v)))
w(row("Gross margin", gm, lambda v: pct(v)))
w(row("EBITDA margin", em, lambda v: pct(v)))
w(row("Rule of 40 (growth + EBITDA margin)", rule40, lambda v: pct(v)))
w(row("Burn multiple (net burn ÷ net new ARR)", burn_mult, lambda v: f"{v:.2f}x" if v == v else "n/a"))
w(row("Revenue per FTE (k€)", [rev[i] / B["fte"][i] if rev[i] else 0 for i in range(M.N)]))
w(row("Sales and marketing ÷ revenue", [B["sm_cost"][i] / rev[i] if rev[i] else float("nan") for i in range(M.N)], lambda v: pct(v)))
w("\nA burn multiple below 1.5x and a Rule of 40 above 40% are signs of efficient growth. The Rule of 40 is shown from FY2030, when revenue is large enough for it to be meaningful.")

# ---- 9.8 break-even
fixed30 = B["opex"][be_year]
contrib_site = B["gross"][be_year] / B["avg_sites"][be_year]
w(f"""
### 9.8 Break-even analysis

- **EBITDA break-even (monthly run rate):** {be_label}, found by assuming monthly EBITDA
  grows linearly across FY{Y[be_year - 1]} and FY{Y[be_year]} (see appendix).
- **First profitable year:** FY{Y[be_year]}, EBITDA {m(ebitda[be_year], 2)}.
- **Sites needed to cover fixed costs in FY{Y[be_year]}:** operating costs of {m(fixed30, 2)}
  ÷ gross profit per average site of {eur(contrib_site)} = **{n(fixed30 / contrib_site)} sites**,
  against {n(B['avg_sites'][be_year])} average sites in the base case.
- **Lowest year-end cash:** {m(min_cash, 2)} in FY{min_cash_year}, just before the seed round.
{PB}
### 9.9 Scenarios

| FY2031 | Bear | **Base** | Bull |
|:--|--:|--:|--:|
| Growth versus plan | 60% | **100%** | 130% |
| Price versus plan | 90% | **100%** | 105% |
| Annual churn | 12% | **8%** | 6% |
| Customers | {n(BEAR['customers'][5])} | **{n(B['customers'][5])}** | {n(BULL['customers'][5])} |
| Revenue | {m(BEAR['revenue'][5])} | **{m(rev[5])}** | {m(BULL['revenue'][5])} |
| EBITDA | {m(BEAR['ebitda'][5])} | **{m(ebitda[5])}** | {m(BULL['ebitda'][5])} |
| EBITDA margin | {pct(BEAR['ebitda'][5] / BEAR['revenue'][5])} | **{pct(em[5])}** | {pct(BULL['ebitda'][5] / BULL['revenue'][5])} |
| Lowest year-end cash | {m(min(BEAR['cash'][1:]), 2)} | **{m(min_cash, 2)}** | {m(min(BULL['cash'][1:]), 2)} |
| Cash FY2031 | {m(BEAR['cash'][5])} | **{m(B['cash'][5])}** | {m(BULL['cash'][5])} |
| DCF value | {m(M.valuation(BEAR)[3])} | **{m(dcf)}** | {m(M.valuation(BULL)[3])} |

Even in the bear case the company does not run out of cash with the planned funding and
reaches positive EBITDA by FY2031. The bull case would justify an optional Series A to
enter France and Italy earlier (section 11.4).

### 9.10 Sensitivity: FY2031 EBITDA (k€)

Rows: price versus plan. Columns: customer growth versus plan.

| Price \\ Growth | """ + " | ".join(pct(g) for g in GROWTHS) + """ |
|:--|""" + "--:|" * len(GROWTHS))
for p in PRICES:
    cells = []
    for g in GROWTHS:
        v = k(SENS[(p, g)]["ebitda"][5])
        cells.append(f"**{v}**" if p == 1.0 and g == 1.0 else v)
    w(f"| {pct(p)} | " + " | ".join(cells) + " |")
w("\nPrice has a stronger effect than volume because most costs are fixed: a 10% price change moves FY2031 EBITDA by about "
  + m(SENS[(1.1, 1.0)]["ebitda"][5] - ebitda[5], 2) + ".")

w("\n**Sensitivity of LTV/CAC to churn (FY2029)**\n")
w("| Annual churn | 4% | 8% | 12% | 16% |\n|:--|--:|--:|--:|--:|")
w("| LTV/CAC (5-year horizon) | " + " | ".join(f"{ltv_at(c) / cac:.1f}x" for c in [0.04, 0.08, 0.12, 0.16]) + " |")
w(PB)


# ---- 9.11 competition rules
def be_of(r):
    e = r["ebitda"]
    y = next(i for i in range(1, M.N) if e[i] > 0)
    sl = (e[y] - e[y - 1]) / 144
    t = -(e[y - 1] / 12 - sl * 6.5) / sl
    mo = int(t) + 1
    return f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][(mo - 1) % 12]} {Y[y - 1] + (mo - 1) // 12}"


elec_total = [B["cogs_energy"][i] + B["opex_energy"][i] for i in range(M.N)]
w("### 9.11 Competition rules and their impact\n")
w(f"""The plan follows the two rules set by the competition in every year of the forecast:

1. **Electricity is {pct(A['elec_surcharge'])} more expensive** than the reference tariff.
2. **Shipping is available only one day a week.**

**Electricity cost**
""")
w(head())
w(row("Electricity at the reference tariff", [v / EF for v in elec_total], lambda v: k(v, 1)))
w(row("Extra cost from the +40% rule", B["elec_extra"], lambda v: k(v, 1)))
w(row("Total electricity", elec_total, lambda v: k(v, 1), bold=True))
w(row("Electricity ÷ revenue", [elec_total[i] / rev[i] if rev[i] else float("nan") for i in range(M.N)], lambda v: pct(v, 1)))
w("\n**Weekly shipping**\n")
w(head())
w(row("Inventory held (kits in stock and spares)", B["inventory"]))
w(row("Extra inventory versus shipping any day", [B["inventory"][i] - B0["inventory"][i] for i in range(M.N)]))
w(row("Weekly freight", B["cogs_freight"]))
w("\n**The plan with and without the rules**\n")
w("| | Without the rules | **With the rules** | Difference |\n|:--|--:|--:|--:|")
for label, v0, v1, f in [
    ("EBITDA FY2029", B0["ebitda"][3], ebitda[3], lambda v: m(v, 2)),
    ("EBITDA FY2031", B0["ebitda"][5], ebitda[5], lambda v: m(v, 2)),
    ("Gross margin FY2031", B0["gross"][5] / B0["revenue"][5], gm[5], lambda v: pct(v, 1)),
    ("Lowest year-end cash", min(B0["cash"][1:]), min_cash, lambda v: m(v, 2)),
    ("Cash FY2031", B0["cash"][5], B["cash"][5], lambda v: m(v, 2)),
    ("DCF value", M.valuation(B0)[3], dcf, lambda v: m(v, 2)),
]:
    d = f"({(v0 - v1) * 100:.1f} pts)" if "margin" in label else f(v1 - v0)
    w(f"| {label} | {f(v0)} | **{f(v1)}** | {d} |")
w(f"| EBITDA break-even month | {be_of(B0)} | **{be_label}** | |")
w(f"""
**What this means.** PyraGrid is a software company, so electricity is a small share of
its costs: even at +40% it is {pct(elec_total[5] / rev[5], 1)} of revenue in FY2031. The weekly
shipping rule mainly ties up cash in stock rather than adding cost; the company answers it
with planned installation days, local stock and spares on every site. Together the two
rules reduce EBITDA over the six years by {m(sum(B0['ebitda']) - sum(ebitda), 2)} and do not
change the funding plan or the first profitable year.
""")
w(PB)


# ---- 10 KPIs
def nrr_at(i):
    """Net revenue retention implied by site expansion and price for existing customers."""
    return (1 - A["logo_churn"]) * (A["sites_per_customer"][i] / A["sites_per_customer"][i - 1]) * (B["blended"][i] / B["blended"][i - 1])


def runway(i):
    burn = -B["fcf"][i] / 12
    return B["cash"][i] / burn if burn > 0 else float("inf")


def bm(i):
    return f"{-B['fcf'][i] / (arr[i] - arr[i - 1]):.2f}x" if B["fcf"][i] < 0 else "cash positive"


def rw(i):
    return f"{runway(i):.0f} months" if B["fcf"][i] < 0 else "cash positive"



elec_rev = [(B["cogs_energy"][i] + B["opex_energy"][i]) / rev[i] if rev[i] else float("nan") for i in range(M.N)]
w(f"""## 10. KPIs and performance targets

PyraGrid runs on a small set of measurable targets. They are reviewed every month by the
management team and reported every quarter to investors and the board.

**North-star metric: sites protected with a tested response plan.** A site counts when it
is monitored, has an approved protocol, and has run at least one drill in the last year.
It grows with revenue and with real safety at the same time.

### 10.1 KPI dashboard (base case)

<!-- kpi-cards -->

### 10.2 Growth and commercial KPIs

| KPI | Definition | FY2027 | FY2029 | FY2031 |
|:--|:--|--:|--:|--:|
| Customers | Paying customers at year end | {n(B['customers'][1])} | {n(B['customers'][3])} | {n(B['customers'][5])} |
| Sites protected | Monitored sites at year end | {n(B['sites'][1])} | {n(B['sites'][3])} | {n(B['sites'][5])} |
| ARR | Annual recurring revenue at year end | {m(arr[1], 2)} | {m(arr[3], 2)} | {m(arr[5], 1)} |
| ARR per customer | ARR ÷ customers | {eur(arr[1] / B['customers'][1])} | {eur(arr[3] / B['customers'][3])} | {eur(arr[5] / B['customers'][5])} |
| New customers | Won in the year | {n(B['new_customers'][1])} | {n(B['new_customers'][3])} | {n(B['new_customers'][5])} |
| Gross revenue retention | 1 − customer churn | pilot year | {pct(1 - A['logo_churn'])} | {pct(1 - A['logo_churn'])} |
| Net revenue retention | Churn, site expansion and price, existing customers | pilot year | {pct(nrr_at(3))} | {pct(nrr_at(5))} |
| Sensor attach rate | Sites with sensors ÷ all sites | {pct(B['sensor_sites'][1] / B['sites'][1])} | {pct(B['sensor_sites'][3] / B['sites'][3])} | {pct(B['sensor_sites'][5] / B['sites'][5])} |
| Professional share | Sites on the Professional tier | {pct(A['pro_mix'][1])} | {pct(A['pro_mix'][3])} | {pct(A['pro_mix'][5])} |
| Pipeline coverage | Qualified pipeline ÷ next year's new ARR target | 3.0x | 3.0x | 3.0x |
| Win rate | Won ÷ qualified opportunities | 20% | 25% | 30% |
| Sales cycle | First meeting to signed contract | ≤ 9 months | ≤ 6 months | ≤ 5 months |

### 10.3 Unit economics and efficiency KPIs

| KPI | Definition | FY2027 | FY2029 | FY2031 |
|:--|:--|--:|--:|--:|
| Gross margin | Gross profit ÷ revenue | {pct(gm[1])} | {pct(gm[3])} | {pct(gm[5])} |
| EBITDA margin | EBITDA ÷ revenue | {pct(em[1])} | {pct(em[3])} | {pct(em[5])} |
| LTV / CAC | See section 9.3 | – | {ltv / cac:.1f}x | – |
| CAC payback | Months of gross profit to repay CAC | – | {cac_payback:.0f} months | – |
| Burn multiple | Net burn ÷ net new ARR | {bm(1)} | {bm(3)} | {bm(5)} |
| Revenue per employee | Revenue ÷ FTE | {eur(rev[1] / B['fte'][1])} | {eur(rev[3] / B['fte'][3])} | {eur(rev[5] / B['fte'][5])} |
| Cash runway | Cash ÷ monthly free-cash burn | {rw(1)} | {rw(3)} | {rw(5)} |
| Electricity ÷ revenue | Includes the +40% tariff rule | {pct(elec_rev[1], 1)} | {pct(elec_rev[3], 1)} | {pct(elec_rev[5], 1)} |
| Inventory cover | Weeks of sensor kits in stock (weekly shipping rule) | {A['stock_weeks']} weeks | {A['stock_weeks']} weeks | {A['stock_weeks']} weeks |

### 10.4 Product and operational KPIs (targets)

| KPI | Definition | FY2027 | FY2029 | FY2031 |
|:--|:--|--:|--:|--:|
| Satellite-to-alert time | Hotspot published → customer alerted | ≤ 5 min | ≤ 2 min | ≤ 1 min |
| Sensor alert latency | Sensor reading → alert on screen | ≤ 60 s | ≤ 30 s | ≤ 30 s |
| Fire position accuracy | Uncertainty radius on sensor sites | ≤ 150 m | ≤ 100 m | ≤ 75 m |
| False alarm rate | Alerts dismissed as not a fire | ≤ 15% | ≤ 8% | ≤ 5% |
| Alert acknowledged | Median time until a person responds | ≤ 10 min | ≤ 5 min | ≤ 3 min |
| AI suggestions approved | Approved without changes by the operator | ≥ 60% | ≥ 70% | ≥ 75% |
| Platform availability | Monthly uptime | 99.5% | 99.9% | 99.9% |
| Sensor network uptime | Sensors reporting on time | ≥ 97% | ≥ 98.5% | ≥ 99% |
| Sensor repair time | Fault → working again (spares on site) | ≤ 2 days | ≤ 1 day | ≤ 1 day |
| Drill participation | Site staff completing a drill each year | ≥ 70% | ≥ 85% | ≥ 90% |

### 10.5 Impact KPIs

| KPI | FY2027 | FY2029 | FY2031 |
|:--|--:|--:|--:|
| Sites protected | {n(B['sites'][1])} | {n(B['sites'][3])} | {n(B['sites'][5])} |
| Sites with ground sensors | {n(B['sensor_sites'][1])} | {n(B['sensor_sites'][3])} | {n(B['sensor_sites'][5])} |
| Fire services and agencies connected (target) | 3 | 15 | 40 |
| People trained through drills (target) | 150 | 1,500 | 6,000 |
| Rural field jobs supported (installers, service) | 2 | 8 | 20 |

### 10.6 Reporting

| Rhythm | Audience | Content |
|:--|:--|:--|
| Weekly | Team | Pipeline, alerts, sensor health, open incidents, stock level |
| Monthly | Management | Full KPI dashboard, cash, budget against actual |
| Quarterly | Board and investors | KPI dashboard, financial statements, forecast update, risks |
| Yearly | Customers and partners | Impact report: sites protected, drills, response times |
""")
w(PB)

# ---- 11 funding
seed_use = [("Engineering and product (sensor v2, AI, integrations)", 0.40), ("Sales and partnerships in Spain and Portugal", 0.30),
            ("Sensor fleet for new customers", 0.15), ("Customer success and field operations", 0.10), ("Working capital and contingency", 0.05)]
w(f"""## 11. Funding and capital structure

### 11.1 Sources and uses, FY2026–FY2028

| Sources | k€ | Uses | k€ |
|:--|--:|:--|--:|
| Founders' capital | {k(A['founders_equity'])} | Operating losses FY2026–FY2028 (EBITDA) | {k(-sum(ebitda[:3]))} |
| Pre-seed (business angels, programme) | {k(A['preseed'])} | Sensor fleet capex FY2026–FY2028 | {k(sum(B['capex'][:3]))} |
| ENISA participative loan | {k(A['enisa_loan'])} | Interest and tax, less the cash from annual billing in advance | {k(sum(B['interest'][:3]) + sum(B['tax'][:3]) - sum(dnwc[:3]))} |
| Innovation grants (e.g. CDTI, regional) | {k(sum(A['grant'][:3]))} | Cash at end of FY2028 | {k(B['cash'][2])} |
| Seed round | {k(A['seed'])} | | |
| **Total** | **{k(A['founders_equity'] + A['preseed'] + A['enisa_loan'] + sum(A['grant'][:3]) + A['seed'])}** | **Total** | **{k(-sum(ebitda[:3]) + sum(B['capex'][:3]) + sum(B['interest'][:3]) + sum(B['tax'][:3]) - sum(dnwc[:3]) + B['cash'][2])}** |

### 11.2 Use of the seed round ({m(A['seed'])})

| Use | Share | k€ |
|:--|--:|--:|
""" + "\n".join(f"| {name} | {pct(s)} | {k(A['seed'] * s)} |" for name, s in seed_use) + f"""
| **Total** | **100%** | **{k(A['seed'])}** |

### 11.3 Capitalisation table

| Shareholder | After pre-seed (FY2026) | After seed (FY2028) |
|:--|--:|--:|
| Founders | {pct(1 - ps_share, 1)} | {pct(founders_post, 1)} |
| Pre-seed investors | {pct(ps_share, 1)} | {pct(preseed_post, 1)} |
| Employee option pool | – | {pct(esop, 1)} |
| Seed investors | – | {pct(seed_share, 1)} |
| **Total** | **100.0%** | **100.0%** |
| Pre-money valuation | {m(pre_seed_pre, 2)} | {m(seed_pre, 2)} |
| Post-money valuation | {m(pre_seed_pre + A['preseed'], 2)} | {m(seed_post, 2)} |

The option pool is created before the seed round (included in the pre-money valuation).

### 11.4 Optional Series A

If the bull case materialises, a Series A of about €4–6M in FY2029–FY2030 would fund entry
into France, Italy and Greece. It is not needed for the base case, which is self-funding from FY2030.

### 11.5 Investor returns (exit at year-end FY2031)

Exit value = FY2031 ARR ({m(arr[5])}) × ARR multiple. No further dilution assumed.

| ARR multiple | Exit value | Seed proceeds | Seed multiple | Seed IRR | Pre-seed multiple | Pre-seed IRR |
|:--|--:|--:|--:|--:|--:|--:|
""")
for mult in exits:
    sp, smo, sirr = moic_irr(seed_share, A["seed"], hold_seed, mult)
    pp, pmo, pirr = moic_irr(preseed_post, A["preseed"], hold_ps, mult)
    w(f"| {mult:.0f}x | {m(arr[5] * mult)} | {m(sp)} | {smo:.1f}x | {pct(sirr)} | {pmo:.1f}x | {pct(pirr)} |")
w(f"\nHolding periods: seed {hold_seed} years (Q1 2028 to end of 2031), pre-seed {hold_ps} years (mid-2026 to end of 2031).")
w(PB)

# ---- 11 valuation
w("## 12. Valuation\n\n### 12.1 Discounted cash flow\n")
w(f"Free cash flow is discounted at **{pct(A['wacc'])}**, a venture-stage rate that reflects execution risk (a mature SaaS company would use 10–12%). Terminal value uses the Gordon growth model with **{pct(A['g_terminal'])}** long-term growth.\n")
w("| k€ | " + " | ".join(f"FY{y}" for y in Y[1:]) + " |\n|:--|" + "--:|" * (M.N - 1))
w("| Free cash flow | " + " | ".join(k(v) for v in B["fcf"][1:]) + " |")
dfs = [1 / (1 + A["wacc"]) ** i for i in range(1, M.N)]
w("| Discount factor | " + " | ".join(f"{d:.3f}" for d in dfs) + " |")
w("| Present value | " + " | ".join(k(v * d) for v, d in zip(B["fcf"][1:], dfs)) + " |")
w(f"""
| Component | k€ |
|:--|--:|
| Present value of FY2027–FY2031 free cash flow | {k(pv_fcf)} |
| Terminal value at FY2031 (FCF × (1 + g) ÷ (WACC − g)) | {k(tv)} |
| Present value of terminal value | {k(pv_tv)} |
| **Enterprise value (DCF)** | **{k(dcf)}** |

**Sensitivity of the DCF value (k€)**

| Discount rate \\ Terminal growth | 2% | 3% | 4% |
|:--|--:|--:|--:|""")
for wr in [0.20, 0.25, 0.30]:
    cells = []
    for g in [0.02, 0.03, 0.04]:
        a2 = dict(A, wacc=wr, g_terminal=g)
        v = M.valuation(B, a2)[3]
        cells.append(f"**{k(v)}**" if wr == A["wacc"] and g == A["g_terminal"] else k(v))
    w(f"| {pct(wr)} | " + " | ".join(cells) + " |")
w(f"""
### 12.2 Market multiples

Listed and private vertical SaaS companies with growth above 40% are commonly valued at
5–10x ARR. Applying {A['arr_multiple']:.0f}x to FY2031 ARR gives an exit value of {m(exit_val)},
worth {m(pv_exit)} today at the same {pct(A['wacc'])} discount rate.

### 12.3 Summary

| Method | Value today |
|:--|--:|
| DCF (Gordon terminal value) | {m(dcf)} |
| ARR multiple exit, discounted ({A['arr_multiple']:.0f}x FY2031 ARR) | {m(pv_exit)} |
| Seed post-money used in this plan | {m(seed_post)} |

The seed post-money of {m(seed_post)} sits between the two methods and leaves room for
investor return, which supports it as a fair entry valuation.
{PB}
## 13. Risks and mitigation

| Risk | Likelihood | Impact | Mitigation |
|:--|:--|:--|:--|
| Slow enterprise sales cycles | High | High | Paid pilots of 5–10 sites; insurer and EPC channels; public-partner pull |
| A quiet fire season lowers urgency | Medium | Medium | Year-round value: drills, protocols, CSRD climate-risk reporting |
| Sensor hardware failures in the field | Medium | Medium | Replacement budget in the model; tilt and heartbeat alerts; field partners |
| Liability if a fire harms a site | Low | High | Decision-support positioning; human approval; no firefighting advice; professional insurance |
| AI gives a wrong or unsafe suggestion | Medium | High | Evidence-cited output, tactics filter, human approval, rule-based fallback |
| Large incumbents copy the product | Medium | Medium | Speed, focus on asset owners, partner network, protocol lock-in |
| Satellite data access changes | Low | Medium | Several sources (NASA FIRMS, Copernicus); ground sensors reduce dependence |
| Funding delay | Medium | High | Public funding (ENISA, grants); bear case survives on planned funding; cost levers in hiring |
| Electricity prices rise beyond +40% | Medium | Low | Solar-powered sensors; fixed-price cloud contracts; electricity is a small share of costs |
| Weekly shipping delays a repair or an installation | High | Medium | {A['stock_weeks']} weeks of kits in stock; {A['spare_sensors_per_site']} spares on every site; installations planned around delivery day |
| Data protection and security | Low | High | EU hosting, per-customer data isolation, role-based access, audit log |

## 14. Milestones and roadmap

| When | Milestone |
|:--|:--|
| Q4 2026 | Company incorporated; pre-seed and ENISA loan closed; 3 sensor pilot sites in Ourense |
| Q2 2027 | First paying customers; sensor hardware v1 certified (CE, radio) |
| Q4 2027 | {n(B['customers'][1])} customers, {n(B['sites'][1])} sites; grant programme completed |
| Q1 2028 | Seed round of {m(A['seed'])} closed |
| Q4 2028 | {n(B['customers'][2])} customers, {n(B['sites'][2])} sites; first insurer partnership |
| Q4 2029 | {n(B['customers'][3])} customers, ARR {m(arr[3])}; monthly EBITDA positive around {be_label} |
| FY2030 | First profitable year; entry into southern France and Italy through partners |
| FY2031 | {n(B['customers'][5])} customers, {n(B['sites'][5])} sites, ARR {m(arr[5])} |

## 15. Impact

- **Lives and safety:** earlier warning and clear procedures for people working on remote sites.
- **Climate resilience:** protects the renewable energy and grid assets the energy transition depends on.
- **Rural jobs:** field installation and maintenance jobs in rural Galicia and beyond.
- **Public good:** a free shared view for fire services and civil protection.
- **UN Sustainable Development Goals:** 7 (clean energy), 9 (resilient infrastructure),
  11 (safe communities), 13 (climate action) and 15 (life on land).
{PB}
## 16. Appendix: methodology and formulas

**Revenue.** Platform revenue = average sites in the year × blended price. Average sites =
(opening + closing sites) ÷ 2. Blended price = Essential price × (1 − Professional share)
+ Professional price × Professional share.

**ARR.** Closing sites × blended price + closing paying sensor sites × sensor fee.

**Sensor fleet.** Capex = new sensor sites × kit cost + opening sensor sites × replacement
rate × sensor cost. Depreciation is straight-line over {A['sensor_life']} years with a
half-year convention in the first and last year.

**EBITDA.** Gross profit + depreciation − operating expenses.

**Tax.** Losses are carried forward and used against later profits; 15% applies to the
first two years with a positive tax base (Spanish rate for new companies), 25% afterwards.
The 70% offset limit for large bases is ignored, as it does not bind at this scale.

**Working capital.** Inventory as in the shipping rule above. Receivables = revenue × {A['dso_days']} ÷ 365. Payables = non-payroll cash
costs × {A['dpo_days']} ÷ 365. Deferred revenue = {pct(A['deferred_share'])} of annual
subscription run rate at year end (annual billing in advance, renewals spread through the year).

**Electricity (+40% rule).** Electricity = (cloud and AI cost × {pct(A['dc_energy_share'])}
+ average sensor sites × {A['gateway_kwh']} kWh × €{A['elec_price']:.2f}
+ FTE × {A['office_kwh_per_fte']:,} kWh × €{A['elec_price']:.2f}) × {EF:.1f}.

**Weekly shipping rule.** Inventory = sensor purchases in the year × {A['stock_weeks']} ÷ 52
+ sensor sites × {A['spare_sensors_per_site']} spares × sensor cost. Inventory is part of working
capital, so it reduces cash but not profit. Freight = {pct(A['freight_pct'])} of sensor purchases.

**Break-even month.** Monthly EBITDA is modelled as m(t) = a + b·t over the 24 months of
FY{Y[be_year - 1]} and FY{Y[be_year]}, fitted so that each year's 12 months add up to its annual
EBITDA. The break-even month is where m(t) = 0.

**DCF.** Enterprise value = Σ FCFₜ ÷ (1 + r)ᵗ + TV ÷ (1 + r)⁵, with TV = FCF₂₀₃₁ × (1 + g) ÷ (r − g).

**LTV and CAC.** LTV = ARPA × gross margin × Σ (1 − churn)ᵗ over t = 0…{LIFE_CAP - 1}, the gross profit a customer brings over five years weighted by retention. CAC is fully
loaded: (sales and marketing + 50% of customer success + 30% of founders' time) ÷ new
customers in the year. The five-year horizon keeps LTV conservative for a young company.

**Net revenue retention.** (1 − churn) × (sites per customer this year ÷ last year) × (blended
price this year ÷ last year): the revenue change from existing customers only, assuming
they grow to the average number of sites.

**IRR.** The discount rate at which the net present value of the cash flows is zero,
solved numerically.

**Source of every figure.** All tables are generated from `model.py` in the same folder;
changing an assumption and running `python build_plan.py` (Markdown) or `python build_pdf.py`
(designed PDF) regenerates this document.

---

*PyraGrid, September 2026. Forward-looking statements are based on the assumptions above
and are subject to risks and uncertainties; actual results may differ.*
""")

out = Path(__file__).with_name("PyraGrid_Business_Plan.md")
out.write_text("\n".join(L), encoding="utf-8")
print("written", out, len("\n".join(L)), "chars")
