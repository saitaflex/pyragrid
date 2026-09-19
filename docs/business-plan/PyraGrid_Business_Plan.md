# PyraGrid

## Business Plan and Financial Model, FY2026–FY2031

**Wildfire intelligence for companies with sites in fire country**

| | |
|:--|:--|
| **Company** | PyraGrid (in formation, Spain) |
| **Stage** | Pre-seed, working product live at rural-valley.vercel.app |
| **Document** | Business plan, five-year financial model, valuation |
| **Version** | 1.0, September 2026 |
| **Funding sought** | €0.30M pre-seed now, €1.5M seed in Q1 2028 |
| **Confidentiality** | Confidential. Prepared for investors, grant bodies and the Rural Valley programme. |

> All financial figures are forecasts built from the assumptions in section 9.1. They are
> planning estimates, not guarantees. Market figures marked *estimate* are to be validated
> during the 2027 pilot programme.

<div style="page-break-after: always;"></div>

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
10. [Funding and capital structure](#10-funding-and-capital-structure)
11. [Valuation](#11-valuation)
12. [Risks and mitigation](#12-risks-and-mitigation)
13. [Milestones and roadmap](#13-milestones-and-roadmap)
14. [Impact](#14-impact)
15. [Appendix: methodology and formulas](#15-appendix-methodology-and-formulas)

<div style="page-break-after: always;"></div>

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

**Business model.** Annual subscription per monitored site (€1,800
Essential, €3,600 Professional), optional Sensor-as-a-Service
(€2,400 per site per year) and onboarding and training services.

**Key figures (base case)**

| | FY2027 | FY2029 | FY2031 |
|:--|--:|--:|--:|
| Customers (year end) | 6 | 40 | 110 |
| Monitored sites (year end) | 60 | 760 | 2,860 |
| Annual recurring revenue (ARR) | €0.17M | €2.6M | €11.5M |
| Revenue | €0.09M | €1.8M | €9.2M |
| Gross margin | 75% | 73% | 74% |
| EBITDA | (€0.34M) | (€0.15M) | €3.6M |
| EBITDA margin | -360% | -8% | 40% |
| Team (FTE) | 6 | 18 | 34 |

- **Break-even:** monthly EBITDA turns positive around **Aug 2029**; FY2030 is the first profitable year.
- **Competition rules included:** electricity 40% more expensive and shipping only one day a week are built into every year of the model (section 9.11).
- **Funding:** €0.30M pre-seed plus an ENISA participative loan (€0.15M) and innovation grants (€0.25M) fund the pilots; a **€1.5M seed round** in Q1 2028 takes the company to profitability. The lowest year-end cash balance is €0.22M (FY2027).
- **Unit economics:** a platform site earns a 89% contribution margin; a sensor site pays back in 33 months; LTV/CAC is 6.3x and the cost of winning a customer is paid back in 8 months.
- **Valuation:** €6.5M on a discounted cash flow at a 25% venture discount rate; €22.6M present value of a 6x ARR exit in 2031.

<div style="page-break-after: always;"></div>

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

<div style="page-break-after: always;"></div>

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

<div style="page-break-after: always;"></div>

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
| **SOM** | PyraGrid base case, FY2031 | 2,860 | €4,026 | €11.5M |

The FY2031 base case reaches **10.6% of the Iberian SAM**, a
realistic share for a specialist leader five years after launch. Revenue per site in the
TAM and SAM rows is a blended planning figure (platform tiers plus sensor attach).

### 4.3 Market drivers

- **Climate:** longer and more intense fire seasons across the Mediterranean.
- **Regulation:** the EU Corporate Sustainability Reporting Directive (CSRD) and ESRS E1
  require large companies to assess and report physical climate risks.
- **Insurance:** underwriters increasingly price wildfire exposure per asset and reward
  mitigation.
- **Energy transition:** thousands of new solar and wind sites are being built in rural,
  fire-prone land.
- **Public policy:** EU and national programmes fund wildfire prevention and early detection.

<div style="page-break-after: always;"></div>

## 5. Competition and positioning

| | Public satellite services (FIRMS, EFFIS) | Satellite analytics start-ups | Ground sensor networks | Camera detection networks | **PyraGrid** |
|:--|:--|:--|:--|:--|:--|
| Detects fires across the region | Yes | Yes | No | Partial | **Yes (satellite)** |
| Risk score per customer site | No | Partial | No | No | **Yes** |
| Confirms fire on the ground, night and cloud | No | No | Yes | Partial | **Yes (optional sensors)** |
| Company protocol and actions | No | No | No | No | **Yes** |
| AI advisor with human approval | No | No | No | No | **Yes** |
| Shared view for fire service and agencies | Public only | No | Partial | Partial | **Yes, per-role policy** |
| Drills and training | No | No | No | No | **Yes** |
| Price | Free | High, enterprise | Hardware-led | Hardware-led | **Per site, from €1,800/yr** |

**Positioning:** PyraGrid does not compete with public satellite data; it uses it. It sits
one level up, as the operational layer an asset owner needs to act, and it integrates
detection sources rather than betting on one. Sensor and camera providers are potential
data partners.

<div style="page-break-after: always;"></div>

## 6. Business model and pricing

### 6.1 Offer

| Product | Includes | Price (2026 list) |
|:--|:--|--:|
| **Essential** | Risk engine, alerts, protocol engine, handoff pack, shared view | €1,800 per site / year |
| **Professional** | Essential plus AI advisor, drills and simulator, API, partner sharing controls | €3,600 per site / year |
| **Enterprise** | Professional for 50+ sites, integrations, SLA | Volume pricing from Professional |
| **Sensor-as-a-Service** | 30 sensors and a gateway per site, installation, maintenance, replacement; 3-year minimum term | €2,400 per site / year |
| **Onboarding** | Site import, protocol set-up, integration | €2,000 per customer |
| **Training and drills** | Annual drill programme and training | €1,000 per customer / year |
| **Public partners** | Shared situation view for fire services and agencies | Free |

List prices rise 3% a year from FY2029. The Professional share grows from
40% to 62% of sites as customers adopt the AI advisor and drills.

### 6.2 Revenue model

- **Recurring subscription** (platform and sensors) is billed annually in advance: about
  98% of FY2031 revenue.
- **Land and expand:** customers start with their most exposed sites and add sites over
  time; sites per customer grow from 10 to 26.
- **Hardware as a service** keeps the sensor fleet on PyraGrid's balance sheet, turning a
  one-off sale into recurring revenue with a 17% internal rate of return per sensor site.

<div style="page-break-after: always;"></div>

## 7. Go-to-market strategy

| Phase | Period | Focus | Target |
|:--|:--|:--|:--|
| **1. Pilots** | 2026–2027 | Galicia (Ourense) and northern Portugal; grant-funded sensor pilots; Rural Valley programme | 6 paying customers, 60 sites |
| **2. Iberia** | 2028–2029 | Renewable owners, grid operators and tower companies across Spain and Portugal | 40 customers, 760 sites |
| **3. Southern Europe** | 2030–2031 | France (south), Italy, Greece through partners | 110 customers, 2,860 sites |

**Channels**

1. **Direct sales** to asset owners: head of HSE, operations and risk.
2. **Insurers and brokers:** PyraGrid as a loss-prevention service bundled with policies.
3. **EPC and O&M contractors** who build and run solar and wind plants.
4. **Public partners:** free shared view for fire services and civil protection, which
   creates demand from asset owners in their area.

**Sales cycle:** 3 to 6 months for mid-size operators, 6 to 12 months for utilities.
A paid pilot of 5 to 10 sites converts to a portfolio contract.

<div style="page-break-after: always;"></div>

## 8. Operations and team

### 8.1 Founding team

- **Co-founder, technology (engine, data and AI):** risk engine, sensor model, AI advisor, infrastructure.
- **Co-founder, product (console and experience):** operator console, partner views, design.

The founders will recruit advisors in wildfire operations (a former fire-service officer),
energy asset management and insurance in 2027.

### 8.2 Hiring plan (FTE at year end)

| Function | FY2026 | FY2027 | FY2028 | FY2029 | FY2030 | FY2031 |
|:--|--:|--:|--:|--:|--:|--:|
| Founders | 2 | 2 | 2 | 2 | 2 | 2 |
| Engineering and data | 0 | 2 | 4 | 6 | 9 | 12 |
| Sales and partnerships | 0 | 1 | 2 | 4 | 6 | 8 |
| Customer success and field operations | 0 | 1 | 2 | 4 | 6 | 8 |
| Finance, legal and admin | 0 | 0.5 | 1 | 2 | 3 | 4 |
| **Total** | **2** | **6.5** | **11** | **18** | **26** | **34** |

Fully loaded annual costs (salary plus Spanish social security) are €58,000
(engineering), €62,000 (sales, including variable pay), €45,000
(customer success and field) and €50,000 (G&A), rising 3% a year. Founders take
reduced salaries until the seed round.

### 8.3 Operations

- **Cloud platform:** serverless hosting and managed Postgres; the cost scales with sites
  (€85 per site per year including AI inference).
- **Sensor supply chain:** off-the-shelf LoRaWAN modules, thermistors, solar cells and
  enclosures assembled by a regional partner; bill of materials about
  €85 per sensor, €3,000 per site kit including the gateway.
- **Field operations:** installation by trained local contractors (€1,200 per site),
  annual inspection and battery service (€250 per site per year).
- **Weekly shipping (competition rule):** carriers collect and deliver only one day a week,
  so hardware cannot be sent next day. PyraGrid plans installations around the weekly
  delivery, keeps 6 weeks of sensor kits in stock and leaves
  2 spare sensors on every sensor site, so a failed sensor is
  swapped the same day by the local contractor instead of waiting for the next shipment.
- **Electricity (competition rule):** electricity costs 40% more than
  the reference tariff of €0.20 per kWh. The model applies this to
  data-centre power (about 30% of cloud and AI cost), gateway power
  on sensor sites and office power. Sensors run on solar cells and batteries, so the field
  network does not depend on the grid.

<div style="page-break-after: always;"></div>

## 9. Financial plan

All amounts are in thousands of euros (k€) unless stated. Negative values are in brackets.
The fiscal year is the calendar year. FY2026 is the formation and pilot year.

### 9.1 Key assumptions

| Area | Assumption | Value |
|:--|:--|:--|
| Customers | Paying customers at year end | 0, 6, 18, 40, 70, 110 |
| Expansion | Average sites per customer | 0, 10, 14, 19, 23.5, 26 |
| Pricing | Essential / Professional per site per year | €1,800 / €3,600, +3%/yr from FY2029 |
| Mix | Professional share of sites | 0%, 40%, 50%, 55%, 60%, 62% |
| Sensors | Share of sites with the sensor network | 0%, 15%, 20%, 25%, 30%, 35% |
| Churn | Annual customer churn from FY2028 | 8% (replaced by new sales) |
| Revenue timing | Recognised on average sites in the year; billed annually in advance | |
| Cost of revenue | Cloud and AI per site; support 8% of subscriptions; sensor field costs; installation | See 8.3 |
| Sensor fleet | Capitalised, straight-line over 4 years (half-year convention); 10% of sensors replaced each year | |
| Marketing | Fixed programme plus 10% of revenue | |
| Working capital | Receivables 45 days; payables 30 days; deferred revenue 45% of annual subscription | |
| **Rule: electricity** | Tariff €0.20/kWh **+40%** = €0.28/kWh; data-centre share of cloud cost 30%; 150 kWh per sensor site; 2,500 kWh per employee | Every year |
| **Rule: shipping** | **One shipping day a week**: 6 weeks of kits in stock, 2 spare sensors per sensor site, freight 4% of hardware bought | Every year |
| Tax | Spanish corporate tax: 15% for the first two profitable years, then 25%; losses carried forward | |
| Public funding | ENISA participative loan €0.15M at 4%, repaid FY2029–FY2031; innovation grants €0.25M | |

### 9.2 Revenue build

| Driver | FY2026 | FY2027 | FY2028 | FY2029 | FY2030 | FY2031 |
|:--|--:|--:|--:|--:|--:|--:|
| Customers (year end) | 0 | 6 | 18 | 40 | 70 | 110 |
| New customers | 0 | 6 | 12 | 23 | 33 | 46 |
| Monitored sites (year end) | 0 | 60 | 252 | 760 | 1,645 | 2,860 |
| Sites with sensors (year end) | 3 | 9 | 50 | 190 | 494 | 1,001 |
| Blended price per site (€) | – | 2,520 | 2,700 | 2,874 | 3,055 | 3,186 |

| k€ | FY2026 | FY2027 | FY2028 | FY2029 | FY2030 | FY2031 |
|:--|--:|--:|--:|--:|--:|--:|
| Platform subscriptions | – | 76 | 421 | 1,454 | 3,674 | 7,177 |
| Sensor-as-a-Service | – | 7 | 71 | 288 | 820 | 1,793 |
| Onboarding and training | – | 12 | 42 | 86 | 136 | 202 |
| **Total revenue** | **–** | **95** | **534** | **1,829** | **4,630** | **9,173** |
| Annual recurring revenue (year end) | – | 166 | 801 | 2,640 | 6,211 | 11,515 |
| Revenue growth | n/a | n/a | 464% | 242% | 153% | 98% |

<div style="page-break-after: always;"></div>

### 9.3 Unit economics

**Per platform site (FY2029)**

| | € per site per year |
|:--|--:|
| Blended subscription price | €2,874 |
| Cloud hosting and data (excluding electricity) | (49) |
| AI inference (excluding electricity) | (10) |
| Data-centre electricity, +40% tariff | (36) |
| Customer support (8%) | (230) |
| **Contribution per site** | **€2,549** |
| **Contribution margin** | **89%** |

**Per sensor site (Sensor-as-a-Service)**

| | € |
|:--|--:|
| Hardware kit (30 sensors and gateway) | €3,000 |
| Weekly consolidated freight (4%) | €120 |
| Spare sensors left on site (2) | €170 |
| Installation | €1,200 |
| **Upfront investment** | **€4,490** |
| Annual fee | €2,400 |
| Field service, connectivity and batteries | (250) |
| Gateway electricity, +40% tariff | (42) |
| Support (8%) | (192) |
| Sensor replacement (10% per year, with freight) | (265) |
| **Annual contribution** | **€1,651** |
| **Payback** | **33 months** |
| **IRR over the 4-year sensor life** | **17%** |

**Per customer (FY2029)**

| Metric | Value | How it is calculated |
|:--|--:|:--|
| Average revenue per customer (ARPA) | €63,054 | Revenue ÷ average customers |
| Customer acquisition cost (CAC), fully loaded | €31,052 | (Sales and marketing + 50% of customer success + 30% of founders' time) ÷ new customers |
| Gross margin | 73% | Gross profit ÷ revenue |
| Lifetime value (LTV), 5-year horizon | €195,233 | ARPA × gross margin × Σ (1 − churn)ᵗ for t = 0…4 |
| LTV uncapped | €572,668 | ARPA × gross margin ÷ churn |
| **LTV / CAC** | **6.3x** | Benchmark for healthy SaaS: 3x or more |
| **CAC payback** | **8 months** | CAC ÷ monthly gross profit per customer |

<div style="page-break-after: always;"></div>

### 9.4 Income statement

| k€ | FY2026 | FY2027 | FY2028 | FY2029 | FY2030 | FY2031 |
|:--|--:|--:|--:|--:|--:|--:|
| **Revenue** | **–** | **95** | **534** | **1,829** | **4,630** | **9,173** |
| Cloud, data and AI (excl. electricity) | (1) | (2) | (9) | (30) | (72) | (134) |
| Electricity: data centres, gateways (+40%) | (1) | (1) | (7) | (23) | (57) | (112) |
| Weekly freight | (0) | (1) | (5) | (17) | (38) | (66) |
| Customer support | – | (7) | (39) | (139) | (360) | (718) |
| Sensor field operations | (0) | (2) | (7) | (30) | (85) | (187) |
| Sensor installation | (4) | (7) | (50) | (168) | (364) | (609) |
| Sensor fleet depreciation | (1) | (5) | (23) | (93) | (265) | (588) |
| **Gross profit** | **(8)** | **71** | **394** | **1,329** | **3,389** | **6,760** |
| Gross margin | n/a | 75% | 74% | 73% | 73% | 74% |
| People | (60) | (327) | (636) | (1,097) | (1,639) | (2,211) |
| Marketing | (5) | (39) | (113) | (303) | (643) | (1,167) |
| Office electricity (+40%) | (1) | (5) | (8) | (13) | (18) | (24) |
| Other operating costs | (10) | (45) | (90) | (160) | (230) | (300) |
| **EBITDA** | **(83)** | **(341)** | **(431)** | **(152)** | **1,124** | **3,645** |
| EBITDA margin | n/a | -360% | -81% | -8% | 24% | 40% |
| Depreciation | (1) | (5) | (23) | (93) | (265) | (588) |
| EBIT | (84) | (345) | (453) | (244) | 859 | 3,058 |
| Grants | – | 150 | 100 | – | – | – |
| Interest | (3) | (6) | (6) | (5) | (3) | (1) |
| Profit before tax | (87) | (201) | (359) | (249) | 856 | 3,057 |
| Corporate tax | – | – | – | – | – | (452) |
| **Net profit** | **(87)** | **(201)** | **(359)** | **(249)** | **856** | **2,604** |

Depreciation of the sensor fleet is part of the cost of revenue; it is added back to reach EBITDA.

<div style="page-break-after: always;"></div>

### 9.5 Cash flow statement

| k€ | FY2026 | FY2027 | FY2028 | FY2029 | FY2030 | FY2031 |
|:--|--:|--:|--:|--:|--:|--:|
| Net profit | (87) | (201) | (359) | (249) | 856 | 2,604 |
| Depreciation | 1 | 5 | 23 | 93 | 265 | 588 |
| Change in working capital | 0 | 67 | 228 | 646 | 1,211 | 1,752 |
| **Operating cash flow** | **(86)** | **(129)** | **(109)** | **490** | **2,332** | **4,944** |
| Sensor fleet capex | (9) | (19) | (126) | (432) | (959) | (1,648) |
| **Free cash flow** | **(95)** | **(148)** | **(235)** | **58** | **1,373** | **3,295** |
| Equity raised | 310 | – | 1,500 | – | – | – |
| ENISA loan drawn / (repaid) | 150 | – | – | (50) | (50) | (50) |
| Net change in cash | 365 | (148) | 1,265 | 8 | 1,323 | 3,245 |
| **Cash at year end** | **365** | **217** | **1,482** | **1,490** | **2,813** | **6,059** |

Annual billing in advance makes working capital a source of cash as the company grows: deferred revenue reaches €5.1M in FY2031.

### 9.6 Balance sheet (year end)

| k€ | FY2026 | FY2027 | FY2028 | FY2029 | FY2030 | FY2031 |
|:--|--:|--:|--:|--:|--:|--:|
| Cash | 365 | 217 | 1,482 | 1,490 | 2,813 | 6,059 |
| Trade receivables | – | 12 | 66 | 225 | 571 | 1,131 |
| Inventory: kits in stock and spares | 2 | 4 | 23 | 82 | 195 | 360 |
| Sensor fleet (net) | 8 | 22 | 126 | 465 | 1,159 | 2,219 |
| **Total assets** | **375** | **254** | **1,696** | **2,262** | **4,737** | **9,769** |
| Trade payables | 2 | 9 | 26 | 72 | 152 | 271 |
| Deferred revenue | – | 75 | 358 | 1,178 | 2,767 | 5,126 |
| ENISA loan | 150 | 150 | 150 | 100 | 50 | – |
| Paid-in capital | 310 | 310 | 1,810 | 1,810 | 1,810 | 1,810 |
| Retained earnings | (87) | (289) | (648) | (897) | (41) | 2,563 |
| **Total liabilities and equity** | **375** | **254** | **1,696** | **2,262** | **4,737** | **9,769** |

The balance sheet balances in every year: total assets equal total liabilities and equity.

<div style="page-break-after: always;"></div>

### 9.7 SaaS metrics and KPIs

| Metric | FY2026 | FY2027 | FY2028 | FY2029 | FY2030 | FY2031 |
|:--|--:|--:|--:|--:|--:|--:|
| ARR (k€) | – | 166 | 801 | 2,640 | 6,211 | 11,515 |
| ARR growth | n/a | n/a | 384% | 229% | 135% | 85% |
| Gross margin | n/a | 75% | 74% | 73% | 73% | 74% |
| EBITDA margin | n/a | -360% | -81% | -8% | 24% | 40% |
| Rule of 40 (growth + EBITDA margin) | n/a | n/a | n/a | n/a | 177% | 138% |
| Burn multiple (net burn ÷ net new ARR) | n/a | 0.89x | 0.37x | n/a | n/a | n/a |
| Revenue per FTE (k€) | – | 15 | 49 | 102 | 178 | 270 |
| Sales and marketing ÷ revenue | n/a | 109% | 46% | 31% | 23% | 19% |

A burn multiple below 1.5x and a Rule of 40 above 40% are signs of efficient growth. The Rule of 40 is shown from FY2030, when revenue is large enough for it to be meaningful.

### 9.8 Break-even analysis

- **EBITDA break-even (monthly run rate):** Aug 2029, found by assuming monthly EBITDA
  grows linearly across FY2029 and FY2030 (see appendix).
- **First profitable year:** FY2030, EBITDA €1.12M.
- **Sites needed to cover fixed costs in FY2030:** operating costs of €2.53M
  ÷ gross profit per average site of €2,818 = **898 sites**,
  against 1,202 average sites in the base case.
- **Lowest year-end cash:** €0.22M in FY2027, just before the seed round.

<div style="page-break-after: always;"></div>

### 9.9 Scenarios

| FY2031 | Bear | **Base** | Bull |
|:--|--:|--:|--:|
| Growth versus plan | 60% | **100%** | 130% |
| Price versus plan | 90% | **100%** | 105% |
| Annual churn | 12% | **8%** | 6% |
| Customers | 66 | **110** | 143 |
| Revenue | €5.0M | **€9.2M** | €12.5M |
| EBITDA | €0.6M | **€3.6M** | €6.0M |
| EBITDA margin | 13% | **40%** | 48% |
| Lowest year-end cash | €0.17M | **€0.22M** | €0.26M |
| Cash FY2031 | €0.7M | **€6.1M** | €10.2M |
| DCF value | €0.2M | **€6.5M** | €11.5M |

Even in the bear case the company does not run out of cash with the planned funding and
reaches positive EBITDA by FY2031. The bull case would justify an optional Series A to
enter France and Italy earlier (section 10.4).

### 9.10 Sensitivity: FY2031 EBITDA (k€)

Rows: price versus plan. Columns: customer growth versus plan.

| Price \ Growth | 70% | 85% | 100% | 115% | 130% |
|:--|--:|--:|--:|--:|--:|
| 80% | 686 | 1,459 | 2,174 | 2,888 | 3,660 |
| 90% | 1,201 | 2,088 | 2,910 | 3,729 | 4,617 |
| 100% | 1,716 | 2,718 | **3,645** | 4,571 | 5,573 |
| 110% | 2,231 | 3,347 | 4,381 | 5,413 | 6,529 |
| 120% | 2,746 | 3,976 | 5,117 | 6,255 | 7,486 |

Price has a stronger effect than volume because most costs are fixed: a 10% price change moves FY2031 EBITDA by about €0.74M.

**Sensitivity of LTV/CAC to churn (FY2029)**

| Annual churn | 4% | 8% | 12% | 16% |
|:--|--:|--:|--:|--:|
| LTV/CAC (5-year horizon) | 6.8x | 6.3x | 5.8x | 5.4x |

<div style="page-break-after: always;"></div>

### 9.11 Competition rules and their impact

The plan follows the two rules set by the competition in every year of the forecast:

1. **Electricity is 40% more expensive** than the reference tariff.
2. **Shipping is available only one day a week.**

**Electricity cost**

| k€ | FY2026 | FY2027 | FY2028 | FY2029 | FY2030 | FY2031 |
|:--|--:|--:|--:|--:|--:|--:|
| Electricity at the reference tariff | 1.6 | 4.2 | 10.4 | 25.5 | 53.9 | 96.9 |
| Extra cost from the +40% rule | 0.7 | 1.7 | 4.1 | 10.2 | 21.6 | 38.7 |
| **Total electricity** | **2.3** | **5.9** | **14.5** | **35.7** | **75.5** | **135.6** |
| Electricity ÷ revenue | n/a | 6.2% | 2.7% | 2.0% | 1.6% | 1.5% |

**Weekly shipping**

| k€ | FY2026 | FY2027 | FY2028 | FY2029 | FY2030 | FY2031 |
|:--|--:|--:|--:|--:|--:|--:|
| Inventory held (kits in stock and spares) | 2 | 4 | 23 | 82 | 195 | 360 |
| Extra inventory versus shipping any day | 1 | 3 | 18 | 66 | 158 | 297 |
| Weekly freight | 0 | 1 | 5 | 17 | 38 | 66 |

**The plan with and without the rules**

| | Without the rules | **With the rules** | Difference |
|:--|--:|--:|--:|
| EBITDA FY2029 | (€0.14M) | **(€0.15M)** | (€0.01M) |
| EBITDA FY2031 | €3.68M | **€3.65M** | (€0.04M) |
| Gross margin FY2031 | 74.0% | **73.7%** | (0.3 pts) |
| Lowest year-end cash | €0.22M | **€0.22M** | (€0.01M) |
| Cash FY2031 | €6.42M | **€6.06M** | (€0.36M) |
| DCF value | €6.86M | **€6.46M** | (€0.40M) |
| EBITDA break-even month | Aug 2029 | **Aug 2029** | |

**What this means.** PyraGrid is a software company, so electricity is a small share of
its costs: even at +40% it is 1.5% of revenue in FY2031. The weekly
shipping rule mainly ties up cash in stock rather than adding cost; the company answers it
with planned installation days, local stock and spares on every site. Together the two
rules reduce EBITDA over the six years by €0.08M and do not
change the funding plan or the first profitable year.


<div style="page-break-after: always;"></div>

## 10. Funding and capital structure

### 10.1 Sources and uses, FY2026–FY2028

| Sources | k€ | Uses | k€ |
|:--|--:|:--|--:|
| Founders' capital | 10 | Operating losses FY2026–FY2028 (EBITDA) | 854 |
| Pre-seed (business angels, programme) | 300 | Sensor fleet capex FY2026–FY2028 | 154 |
| ENISA participative loan | 150 | Interest and tax, less the cash from annual billing in advance | (280) |
| Innovation grants (e.g. CDTI, regional) | 250 | Cash at end of FY2028 | 1,482 |
| Seed round | 1,500 | | |
| **Total** | **2,210** | **Total** | **2,210** |

### 10.2 Use of the seed round (€1.5M)

| Use | Share | k€ |
|:--|--:|--:|
| Engineering and product (sensor v2, AI, integrations) | 40% | 600 |
| Sales and partnerships in Spain and Portugal | 30% | 450 |
| Sensor fleet for new customers | 15% | 225 |
| Customer success and field operations | 10% | 150 |
| Working capital and contingency | 5% | 75 |
| **Total** | **100%** | **1,500** |

### 10.3 Capitalisation table

| Shareholder | After pre-seed (FY2026) | After seed (FY2028) |
|:--|--:|--:|
| Founders | 80.0% | 56.0% |
| Pre-seed investors | 20.0% | 14.0% |
| Employee option pool | – | 10.0% |
| Seed investors | – | 20.0% |
| **Total** | **100.0%** | **100.0%** |
| Pre-money valuation | €1.20M | €6.00M |
| Post-money valuation | €1.50M | €7.50M |

The option pool is created before the seed round (included in the pre-money valuation).

### 10.4 Optional Series A

If the bull case materialises, a Series A of about €4–6M in FY2029–FY2030 would fund entry
into France, Italy and Greece. It is not needed for the base case, which is self-funding from FY2030.

### 10.5 Investor returns (exit at year-end FY2031)

Exit value = FY2031 ARR (€11.5M) × ARR multiple. No further dilution assumed.

| ARR multiple | Exit value | Seed proceeds | Seed multiple | Seed IRR | Pre-seed multiple | Pre-seed IRR |
|:--|--:|--:|--:|--:|--:|--:|

| 4x | €46.1M | €9.2M | 6.1x | 62% | 21.5x | 75% |
| 6x | €69.1M | €13.8M | 9.2x | 81% | 32.2x | 88% |
| 8x | €92.1M | €18.4M | 12.3x | 95% | 43.0x | 98% |

Holding periods: seed 3.75 years (Q1 2028 to end of 2031), pre-seed 5.5 years (mid-2026 to end of 2031).

<div style="page-break-after: always;"></div>

## 11. Valuation

### 11.1 Discounted cash flow

Free cash flow is discounted at **25%**, a venture-stage rate that reflects execution risk (a mature SaaS company would use 10–12%). Terminal value uses the Gordon growth model with **3%** long-term growth.

| k€ | FY2027 | FY2028 | FY2029 | FY2030 | FY2031 |
|:--|--:|--:|--:|--:|--:|
| Free cash flow | (148) | (235) | 58 | 1,373 | 3,295 |
| Discount factor | 0.800 | 0.640 | 0.512 | 0.410 | 0.328 |
| Present value | (119) | (151) | 30 | 563 | 1,080 |

| Component | k€ |
|:--|--:|
| Present value of FY2027–FY2031 free cash flow | 1,403 |
| Terminal value at FY2031 (FCF × (1 + g) ÷ (WACC − g)) | 15,429 |
| Present value of terminal value | 5,056 |
| **Enterprise value (DCF)** | **6,459** |

**Sensitivity of the DCF value (k€)**

| Discount rate \ Terminal growth | 2% | 3% | 4% |
|:--|--:|--:|--:|
| 20% | 9,238 | 9,757 | 10,342 |
| 25% | 6,192 | **6,459** | 6,751 |
| 30% | 4,375 | 4,527 | 4,692 |

### 11.2 Market multiples

Listed and private vertical SaaS companies with growth above 40% are commonly valued at
5–10x ARR. Applying 6x to FY2031 ARR gives an exit value of €69.1M,
worth €22.6M today at the same 25% discount rate.

### 11.3 Summary

| Method | Value today |
|:--|--:|
| DCF (Gordon terminal value) | €6.5M |
| ARR multiple exit, discounted (6x FY2031 ARR) | €22.6M |
| Seed post-money used in this plan | €7.5M |

The seed post-money of €7.5M sits between the two methods and leaves room for
investor return, which supports it as a fair entry valuation.

<div style="page-break-after: always;"></div>

## 12. Risks and mitigation

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
| Weekly shipping delays a repair or an installation | High | Medium | 6 weeks of kits in stock; 2 spares on every site; installations planned around delivery day |
| Data protection and security | Low | High | EU hosting, per-customer data isolation, role-based access, audit log |

## 13. Milestones and roadmap

| When | Milestone |
|:--|:--|
| Q4 2026 | Company incorporated; pre-seed and ENISA loan closed; 3 sensor pilot sites in Ourense |
| Q2 2027 | First paying customers; sensor hardware v1 certified (CE, radio) |
| Q4 2027 | 6 customers, 60 sites; grant programme completed |
| Q1 2028 | Seed round of €1.5M closed |
| Q4 2028 | 18 customers, 252 sites; first insurer partnership |
| Q4 2029 | 40 customers, ARR €2.6M; monthly EBITDA positive around Aug 2029 |
| FY2030 | First profitable year; entry into southern France and Italy through partners |
| FY2031 | 110 customers, 2,860 sites, ARR €11.5M |

## 14. Impact

- **Lives and safety:** earlier warning and clear procedures for people working on remote sites.
- **Climate resilience:** protects the renewable energy and grid assets the energy transition depends on.
- **Rural jobs:** field installation and maintenance jobs in rural Galicia and beyond.
- **Public good:** a free shared view for fire services and civil protection.
- **UN Sustainable Development Goals:** 7 (clean energy), 9 (resilient infrastructure),
  11 (safe communities), 13 (climate action) and 15 (life on land).

<div style="page-break-after: always;"></div>

## 15. Appendix: methodology and formulas

**Revenue.** Platform revenue = average sites in the year × blended price. Average sites =
(opening + closing sites) ÷ 2. Blended price = Essential price × (1 − Professional share)
+ Professional price × Professional share.

**ARR.** Closing sites × blended price + closing paying sensor sites × sensor fee.

**Sensor fleet.** Capex = new sensor sites × kit cost + opening sensor sites × replacement
rate × sensor cost. Depreciation is straight-line over 4 years with a
half-year convention in the first and last year.

**EBITDA.** Gross profit + depreciation − operating expenses.

**Tax.** Losses are carried forward and used against later profits; 15% applies to the
first two years with a positive tax base (Spanish rate for new companies), 25% afterwards.
The 70% offset limit for large bases is ignored, as it does not bind at this scale.

**Working capital.** Inventory as in the shipping rule above. Receivables = revenue × 45 ÷ 365. Payables = non-payroll cash
costs × 30 ÷ 365. Deferred revenue = 45% of annual
subscription run rate at year end (annual billing in advance, renewals spread through the year).

**Electricity (+40% rule).** Electricity = (cloud and AI cost × 30%
+ average sensor sites × 150 kWh × €0.20
+ FTE × 2,500 kWh × €0.20) × 1.4.

**Weekly shipping rule.** Inventory = sensor purchases in the year × 6 ÷ 52
+ sensor sites × 2 spares × sensor cost. Inventory is part of working
capital, so it reduces cash but not profit. Freight = 4% of sensor purchases.

**Break-even month.** Monthly EBITDA is modelled as m(t) = a + b·t over the 24 months of
FY2029 and FY2030, fitted so that each year's 12 months add up to its annual
EBITDA. The break-even month is where m(t) = 0.

**DCF.** Enterprise value = Σ FCFₜ ÷ (1 + r)ᵗ + TV ÷ (1 + r)⁵, with TV = FCF₂₀₃₁ × (1 + g) ÷ (r − g).

**LTV and CAC.** LTV = ARPA × gross margin × Σ (1 − churn)ᵗ over t = 0…4, the gross profit a customer brings over five years weighted by retention. CAC is fully
loaded: (sales and marketing + 50% of customer success + 30% of founders' time) ÷ new
customers in the year. The five-year horizon keeps LTV conservative for a young company.

**IRR.** The discount rate at which the net present value of the cash flows is zero,
solved numerically.

**Source of every figure.** All tables are generated from `model.py` in the same folder;
changing an assumption and running `python build_plan.py` regenerates this document.

---

*PyraGrid, September 2026. Forward-looking statements are based on the assumptions above
and are subject to risks and uncertainties; actual results may differ.*
