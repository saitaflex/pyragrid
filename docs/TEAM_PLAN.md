# TEAM_PLAN.md: Wildfire Asset Intelligence (Rural Valley hackathon)

**Plan version:** 2.1.0 · **Contract version:** 2.1.0 · **Model version:** rules-1.0 · **Deploy target:** Vercel (no Docker, no custom domain) · **Written:** 18 Sept 2026

This file merges the team build plan with the *Technical Feasibility & Deployment Specification*, and adds in v2.1: the **AI Advisor** (grounded suggestions for the company, human-approved), the **Firefighter Handoff Pack**, and **Vercel-only deployment**. Section 9 lists where each spec section landed and where we deliberately deviated.

---

## 0. INSTRUCTIONS FOR THE AI AGENT (read first, follow exactly)

You are an AI coding agent working inside a **shared Git repository** used by two people. Each person pastes this same file into their own agent. You build **only one track** and never touch the other.

1. Read this entire file before writing any code.
2. Ask the human exactly this, then wait: **"Which track are you: 1 (Engine / backend) or 2 (Console / frontend)?"**
3. After the answer, work **only** on Section 2 (Shared Contract, obey it character for character), Section 3 (No-Conflict Rules, always), and Section 5 if the answer is **1** or Section 6 if the answer is **2**.
4. Work milestone by milestone. After each milestone, run its "Done when" checks, show the results to the human, commit, and push.
5. If something here seems wrong or impossible, **stop and tell the human**. Never silently change the contract, field names, thresholds, ports, roles or folder names.
6. If an external API behaves differently from what is written here, check its live documentation, adapt **inside your own folder only**, and tell the human what you changed.
7. Read Section 10 (Verification Log): it lists what is already proven and what you must verify on first run.

Default assignment (the humans may swap): **Track 1 = Oussama (@saitaflex)**, **Track 2 = @callmegema**.

---

## 1. What we are building (both tracks)

**One-sentence pitch:** a source-agnostic geospatial decision-support platform that ingests wildfire detections, enriches them with environmental and customer asset data, scores exposure transparently, and turns hundreds of raw observations into a prioritized operational action list.

**Pipeline:**

```text
Wildfire detections (FIRMS or synthetic) ─┐
Customer assets (CSV / GeoJSON import) ───┼─> normalize ─> geospatial matching ─> enrichment (weather, fuel)
Weather (Open-Meteo archive) ─────────────┘        ─> risk engine (rules-1.0) ─> portfolio triage
                                                    ─> alerts (state transitions) ─> SOP actions ─> dashboard + email outbox
                                                    ─> audit log
```

**Hackathon Definition of Done (what a judge must see, on the public Vercel URL):**
1. Log in. 2. Upload 20 assets from CSV. 3. Assets appear on the map. 4. Replay historical detections from August 2025 Ourense. 5. Nearby assets are identified. 6. Risk factors are calculated and shown. 7. Assets are ranked. 8. Levels change over time. 9. Alerts are generated, with the customer's SOP actions, and can be acknowledged. 10. The AI Advisor gives grounded suggestions for an incident, and a human approves or rejects them. 11. A Handoff Pack for the fire service can be printed. 12. The History page shows measured backtest results.

**What the AI Advisor is, and is not.** It advises the **company** (operators, site teams, and what to share with the fire service liaison). It **never** gives firefighting tactics or instructions to the fire service: firefighting command belongs to the public fire service. Every suggestion must cite the data it is based on, and a human approves or rejects it. The approve/reject decisions are stored: over time they become our own dataset of what operators did during real fires.

**Honesty rules (visible in the product):**
- Fire data: NASA FIRMS VIIRS hotspot **detections**, not fire perimeters, or a synthetic fallback, clearly labelled.
- Every factor shows its status: `observed`, `customer_provided`, `assumed` or `unknown`. Missing data is never silently invented.
- Sites, values, personnel and SOPs in the demo are **simulated**, and the UI says so.
- Never write "real-time". Use "near-real-time".
- The score is an **"MVP decision-support model, not a validated prediction model"**. This sentence appears in the UI.
- Never claim an accuracy percentage. Report the measured backtest numbers.
- AI suggestions are labelled as AI-generated, show which engine produced them (`groq`, `ollama` or `template`), and carry the advisor disclaimer.

**Repository layout (final):**

```
/                       ← Track 1 owns root files
├── README.md           ← Track 1
├── .gitignore          ← Track 1
├── docs/TEAM_PLAN.md   ← this file, committed unchanged by Track 1
├── backend/            ← Track 1 ONLY
└── frontend/           ← Track 2 ONLY
```

---

## 2. SHARED CONTRACT v2.1.0 (both tracks must match exactly)

### 2.1 Runtime basics

| Item | Value |
|---|---|
| Backend base URL (local) | `http://localhost:8000` |
| Frontend dev URL (local) | `http://localhost:5173` |
| Production (Vercel) | Engine `https://<engine-project>.vercel.app`, Console `https://<console-project>.vercel.app`. Free `vercel.app` subdomains, no custom domain |
| API prefix | `/api` |
| Time format | ISO 8601 UTC with `Z`, seconds included: `2025-08-14T15:00:00Z` |
| Replay start / end | `2025-08-08T00:00:00Z` / `2025-08-26T00:00:00Z` (end exclusive) |
| Replay step | 3 hours. Grid times 00, 03, ..., 21 UTC. Last step `2025-08-25T21:00:00Z` (144 steps) |
| `at` parameter | Optional. Missing = last step. Backend **clamps** into range and **snaps down** to the grid; responses return the snapped `at` |
| Auth header | `Authorization: Bearer <access_token>` on every endpoint except `GET /api/health` and `POST /api/auth/login` |
| Error bodies | FastAPI default: `{"detail": "<message>"}`. 401 `not authenticated` or `invalid credentials`, 403 `forbidden`, 404 `site not found` / `incident not found` / `alert not found` / `rule not found` |
| CORS | Allow all origins, methods and headers (bearer tokens, no cookies) |
| Money | Integer euros. Distances km, 1 decimal. Angles integer degrees 0..359, 0 = north. Factor points 1 decimal. Score integer 0..100 |

### 2.2 Demo accounts (seeded by the backend on first start)

| Email | Password | customer_id | role |
|---|---|---|---|
| admin@demo.eu | demo1234 | demo | admin |
| operator@demo.eu | demo1234 | demo | operator |
| other@othercorp.eu | demo1234 | othercorp | admin |

Roles: **operator** can read everything of its own customer and acknowledge alerts. **admin** can also import assets, create/edit/delete SOP rules, and read the audit log. A user never sees another customer's data: this is demonstrated with `othercorp`, which owns one asset only.

### 2.3 Risk levels

| Score | Level | Hex colour |
|---|---|---|
| 0–25 | `NORMAL` | `#2E7D32` |
| 26–50 | `ELEVATED` | `#F9A825` |
| 51–75 | `HIGH` | `#EF6C00` |
| 76–100 | `CRITICAL` | `#C62828` |

Rank: NORMAL 0 < ELEVATED 1 < HIGH 2 < CRITICAL 3.

### 2.4 TypeScript types

Track 2 copies this block verbatim into `frontend/src/api/types.ts`. Track 1 mirrors it with Pydantic v2 models using identical field names and `Literal[...]` for string unions.

```ts
export type Level = "NORMAL" | "ELEVATED" | "HIGH" | "CRITICAL";
export type SiteType = "solar_farm" | "wind_farm" | "substation" | "forest_block" | "telecom_tower" | "test_plot";
export type FuelClass = "low" | "medium" | "high" | "very_high";
export type RouteStatus = "available" | "potentially_exposed";
export type DataSource = "firms_sp" | "firms_nrt" | "synthetic_fallback";
export type FactorStatus = "observed" | "customer_provided" | "assumed" | "unknown";
export type SourceState = "ONLINE" | "FALLBACK" | "OFFLINE" | "NOT_CONFIGURED";
export type Role = "admin" | "operator";

export interface Health {
  status: "ok";
  contract_version: "2.1.0";
  model_version: "rules-1.0";
  data_source: DataSource;
  replay_start: string;
  replay_end: string;
  step_hours: 3;
}

export interface User { email: string; name: string; customer_id: string; role: Role }
export interface LoginRequest { email: string; password: string }
export interface LoginResponse { access_token: string; token_type: "bearer"; expires_in: number; user: User }

export interface Component { name: string; value_eur: number }

export interface Site {
  site_id: string;
  name: string;
  type: SiteType;
  lat: number;
  lon: number;
  radius_m: number;
  value_eur: number;
  fuel_class: FuelClass;
  personnel_on_site: number;
  primary_access_bearing_deg: number;
  criticality: number; // 1..5
  components: Component[];
}

export interface ImportReport {
  accepted: number;
  rejected: { row: number; site_id: string | null; reason: string }[];
  total_sites: number;
}

export interface Factors {
  proximity: number | null;      // 0..35
  wind_alignment: number | null; // 0..25
  weather: number | null;        // 0..15
  fuel: number | null;           // 0..15
  vulnerability: number | null;  // 0..10
}
export interface FactorStatuses {
  proximity: FactorStatus;
  wind_alignment: FactorStatus;
  weather: FactorStatus;
  fuel: FactorStatus;
  vulnerability: FactorStatus;
}

export interface AccessRoute { name: "Primary access" | "Secondary access"; bearing_deg: number; status: RouteStatus }

export interface SiteStatus {
  site_id: string;
  name: string;
  type: SiteType;
  lat: number;
  lon: number;
  radius_m: number;
  value_eur: number;
  personnel_on_site: number;
  criticality: number;
  score: number;
  level: Level;
  model_version: "rules-1.0";
  factors: Factors;
  factor_status: FactorStatuses;
  nearest_fire_km: number | null;
  fire_bearing_deg: number | null;
  fire_moving_toward_site: boolean | null;
  triggering_detection_id: string | null;
  wind: { speed_kmh: number; from_deg: number; to_deg: number } | null;
  weather: { temp_c: number; rh_pct: number } | null;
  access_routes: AccessRoute[];
  exposed_components: Component[];
  sop_actions: string[];
}

export interface Portfolio {
  at: string;
  counts: { NORMAL: number; ELEVATED: number; HIGH: number; CRITICAL: number };
  total_exposed_value_eur: number;
  sites: SiteStatus[];
}

export interface Detection {
  id: string;
  source: DataSource;
  external_id: string | null;
  lat: number;
  lon: number;
  observed_at: string;
  received_at: string;
  satellite: string;
  confidence: "n" | "h";
  intensity_frp: number;
}

export interface Alert {
  alert_id: string;
  site_id: string;
  site_name: string;
  at: string;
  kind: "escalation" | "de-escalation";
  from_level: Level;
  to_level: Level;
  score: number;
  headline: string;
  triggering_detection_id: string | null;
  factors: Factors;
  factor_status: FactorStatuses;
  model_version: "rules-1.0";
  processed_at: string;
  actions: string[];
  rule_ids: string[];
  acknowledged: boolean;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
}

export interface AckResponse { alert_id: string; acknowledged: true; acknowledged_by: string; acknowledged_at: string }

export interface Incident {
  incident_id: string;
  site_id: string;
  site_name: string;
  level: "HIGH" | "CRITICAL";
  score: number;
  opened_at: string;
  closed_at: string | null;
  headline: string;
  actions: string[];
  rule_ids: string[];
  disclaimer: string;
}

export interface SopRule {
  rule_id: string;
  name: string;
  enabled: boolean;
  priority: number;
  conditions: {
    min_level: Level;
    asset_types: SiteType[];
    min_criticality: number;
    wind_toward_site: boolean | null;
  };
  actions: string[];
}
export type SopRuleInput = Omit<SopRule, "rule_id">;

export interface TimelinePoint { at: string; score: number; level: Level; nearest_fire_km: number | null }

export interface ReplaySummary {
  start: string;
  end: string;
  step_hours: 3;
  data_source: DataSource;
  model_version: "rules-1.0";
  total_detections: number;
  detections_used: number;
  alerts_raised: number;
  incidents: number;
  sites_ever_high: number;
  sites_ever_critical: number;
  sites_reached_by_fire: number;
  missed_exposures: number;
  median_lead_time_hours: number | null;
  explanation_coverage_pct: number;
}

export interface SourceStatus { name: "FIRMS" | "Weather" | "Vegetation" | "Notification" | "Database" | "AI Advisor"; state: SourceState; detail: string }

export interface IngestionRun {
  run_id: string;
  source: string;
  started_at: string;
  completed_at: string | null;
  records_received: number;
  records_inserted: number;
  records_rejected: number;
  error_message: string | null;
}

export interface AuditEntry { id: number; at: string; actor: string; action: string; details: string }

export interface OutboxEmail { alert_id: string; to: string; subject: string; body: string; channel: "email"; status: "outbox" | "sent" | "failed" }

export type Audience = "operator" | "site_team" | "fire_service_liaison";
export type AdvisorEngine = "groq" | "ollama" | "template";
export type Decision = "approved" | "rejected";

export interface AdvisorSuggestion {
  suggestion_id: string;
  title: string;
  detail: string;
  audience: Audience;
  priority: 1 | 2 | 3;
  evidence: string[];
  decision: Decision | null;
  decided_by: string | null;
  decided_at: string | null;
}

export interface AdvisorResponse {
  incident_id: string;
  at: string;
  generated_by: AdvisorEngine;
  model: string | null;
  created_at: string;
  evidence_keys: string[];
  suggestions: AdvisorSuggestion[];
  rejected_by_guardrails: number;
  fallback_reason: string | null;
  disclaimer: string;
}

export interface DecisionRequest { decision: Decision; note: string }

export interface DecisionRecord {
  suggestion_id: string;
  incident_id: string;
  title: string;
  decision: Decision;
  note: string;
  decided_by: string;
  decided_at: string;
  generated_by: AdvisorEngine;
}

export interface Hazard { name: string; kind: "electrical" | "battery" | "fuel_oil" | "height" | "none"; note: string }
export interface WaterPoint { name: string; lat: number; lon: number; capacity_m3: number }

export interface HandoffPack {
  site_id: string;
  site_name: string;
  type: SiteType;
  at: string;
  generated_at: string;
  lat: number;
  lon: number;
  level: Level;
  score: number;
  headline: string;
  personnel_on_site: number;
  criticality: number;
  access_routes: AccessRoute[];
  hazards: Hazard[];
  water_points: WaterPoint[];
  contact: { role: string; phone: string };
  simulated: true;
  disclaimer: string;
}
```

### 2.5 Endpoints

| Method & path | Role | Query / body | Returns |
|---|---|---|---|
| `GET /api/health` | public | | `Health` |
| `POST /api/auth/login` | public | `LoginRequest` JSON | `LoginResponse` (401 on bad credentials) |
| `GET /api/auth/me` | any | | `User` |
| `GET /api/sites` | any | | `Site[]` sorted by `site_id` |
| `GET /api/assets/sample.csv` | any | | `text/csv`, the 20 demo sites in import format |
| `POST /api/assets/import` | admin | multipart field `file` (`.csv`, `.geojson` or `.json`) | `ImportReport` (422 if 0 accepted or wrong file type; portfolio unchanged then) |
| `GET /api/portfolio` | any | `at?` | `Portfolio`, sites sorted by level rank desc, score desc, `site_id` asc |
| `GET /api/sites/{site_id}/status` | any | `at?` | `SiteStatus` |
| `GET /api/sites/{site_id}/timeline` | any | | `TimelinePoint[]`, all 144 steps ascending |
| `GET /api/detections` | any | `at?`, `window_hours?` int 1..48 default 12 | `Detection[]` with `at - window < observed_at <= at`, confidence filtered, ascending |
| `GET /api/alerts` | any | `at?`, `status?` = `all` (default) or `unacknowledged` | `Alert[]` with `alert.at <= at`, newest first |
| `POST /api/alerts/{alert_id}/acknowledge` | any | no body | `AckResponse`. Idempotent: the first acknowledgement is kept |
| `GET /api/incidents` | any | `at?` | `Incident[]` open at `at`, CRITICAL first then score desc |
| `GET /api/incidents/history` | any | | `Incident[]` all, ascending by `opened_at` |
| `GET /api/incidents/{incident_id}` | any | `at?` | `Incident` |
| `GET /api/sop/rules` | any | | `SopRule[]` sorted by priority asc, then `rule_id` |
| `POST /api/sop/rules` | admin | `SopRuleInput` | `SopRule` (201). Backend assigns `rule_id` `R-###` |
| `PUT /api/sop/rules/{rule_id}` | admin | `SopRuleInput` | `SopRule` |
| `DELETE /api/sop/rules/{rule_id}` | admin | | 204 |
| `GET /api/replay/summary` | any | | `ReplaySummary` |
| `GET /api/status/sources` | any | | `SourceStatus[]` in the order FIRMS, Weather, Vegetation, Notification, Database, AI Advisor |
| `GET /api/ingestion/runs` | any | | `IngestionRun[]` newest first |
| `GET /api/notifications/outbox` | any | `at?` | `OutboxEmail[]` for escalation alerts with `alert.at <= at`, newest first |
| `GET /api/audit` | admin | | `AuditEntry[]` newest first, max 200 |
| `POST /api/advisor/incidents/{incident_id}` | any | `at?` | `AdvisorResponse` (new suggestions are generated and stored every call). 404 if incident unknown |
| `GET /api/advisor/incidents/{incident_id}/latest` | any | | Latest stored `AdvisorResponse` with current decisions. 404 `{"detail":"no advice yet"}` |
| `POST /api/advisor/suggestions/{suggestion_id}/decision` | any | `DecisionRequest` | `DecisionRecord`. Idempotent: the first decision is kept. 404 `{"detail":"suggestion not found"}` |
| `GET /api/advisor/decisions` | admin | | `DecisionRecord[]` newest first |
| `GET /api/sites/{site_id}/handoff` | any | `at?` | `HandoffPack` |

### 2.6 Field rules both sides rely on

- `total_exposed_value_eur` = sum of `value_eur` of sites at HIGH or CRITICAL. `exposed_components` = full `components` at HIGH/CRITICAL, else `[]`.
- `nearest_fire_km`, `fire_bearing_deg`, `triggering_detection_id` are `null` when no used detection is within 25 km of the site edge. `fire_moving_toward_site` is `null` when there is no fire or wind is unknown.
- `wind` and `weather` are `null` when weather is `unknown`. Unknown factors are `null` in `factors`, count as 0 in the score, and show status `unknown`.
- `sop_actions` / `actions`: the actions of all enabled SOP rules that match, in rule priority order, duplicates removed (first occurrence kept). Computed with the **current** rules at request time.
- `alert_id` = `{site_id}_{YYYYMMDDTHHMM}_{to_level}`, e.g. `ES-OU-001_20250814T0900_CRITICAL`. `incident_id` = `{site_id}_{YYYYMMDDTHHMM}` of `opened_at`.
- `headline`: `Fire {km:.1f} km {COMPASS}, wind {toward site | away from site | crosswind | unknown}`, or `No fire within 25 km` when there is no fire.
- `Incident.disclaimer` exactly: `Recommended actions from the customer's approved protocol (simulated for demo). Not an autonomous safety decision.`
- `received_at` of a detection = when our system fetched it; `observed_at` = satellite observation time. `processed_at` of an alert = when the engine computed it.
- Mock mode in the frontend always shows the `demo` customer data.
- `AdvisorResponse.disclaimer` exactly: `AI-generated suggestions for the company's own operations, grounded in the data shown. Not firefighting instructions. A human must approve every suggestion. Always follow the fire service's orders.`
- `HandoffPack.disclaimer` exactly: `Information for the fire service from the site operator (simulated demo data). The fire service decides all firefighting actions.`
- Evidence keys have the form `factor:<name>`, `route:<route name>`, `rule:<rule_id>`, `asset:<field>`, `component:<name>`, `weather:wind`, `detection:<id>`. A suggestion may only cite keys listed in `evidence_keys`.
- `SourceStatus` order: FIRMS, Weather, Vegetation, Notification, Database, AI Advisor.

### 2.7 Canonical mock data

Track 2 saves each of the 18 blocks as `frontend/src/mocks/<name>.json`. Track 1 uses them as shape examples in tests. They were validated against the types above with a strict TypeScript check, and their scores follow the Section 5.5 formula, but they are **not** outputs of the real engine.

`health.json`
```json
{
 "status": "ok",
 "contract_version": "2.1.0",
 "model_version": "rules-1.0",
 "data_source": "synthetic_fallback",
 "replay_start": "2025-08-08T00:00:00Z",
 "replay_end": "2025-08-26T00:00:00Z",
 "step_hours": 3
}
```

`login.json`
```json
{
 "access_token": "mock-token",
 "token_type": "bearer",
 "expires_in": 43200,
 "user": {
  "email": "admin@demo.eu",
  "name": "Demo Admin",
  "customer_id": "demo",
  "role": "admin"
 }
}
```

`sites.json`
```json
[
 {
  "site_id": "ES-OU-001",
  "name": "Solar Trives 01",
  "type": "solar_farm",
  "lat": 42.33,
  "lon": -7.23,
  "radius_m": 600,
  "value_eur": 12400000,
  "fuel_class": "high",
  "personnel_on_site": 7,
  "primary_access_bearing_deg": 200,
  "criticality": 4,
  "components": [
   {
    "name": "PV array",
    "value_eur": 8680000
   },
   {
    "name": "Inverter station",
    "value_eur": 1860000
   },
   {
    "name": "Substation",
    "value_eur": 1240000
   },
   {
    "name": "Control building",
    "value_eur": 620000
   }
  ]
 },
 {
  "site_id": "ES-OU-004",
  "name": "Substation Chandrexa 14",
  "type": "substation",
  "lat": 42.27,
  "lon": -7.34,
  "radius_m": 150,
  "value_eur": 8000000,
  "fuel_class": "medium",
  "personnel_on_site": 2,
  "primary_access_bearing_deg": 180,
  "criticality": 5,
  "components": [
   {
    "name": "Transformers",
    "value_eur": 4800000
   },
   {
    "name": "Switchgear",
    "value_eur": 2400000
   },
   {
    "name": "Control building",
    "value_eur": 800000
   }
  ]
 },
 {
  "site_id": "ES-OU-013",
  "name": "Substation O Barco 09",
  "type": "substation",
  "lat": 42.415,
  "lon": -6.985,
  "radius_m": 150,
  "value_eur": 7200000,
  "fuel_class": "low",
  "personnel_on_site": 3,
  "primary_access_bearing_deg": 270,
  "criticality": 5,
  "components": [
   {
    "name": "Transformers",
    "value_eur": 4320000
   },
   {
    "name": "Switchgear",
    "value_eur": 2160000
   },
   {
    "name": "Control building",
    "value_eur": 720000
   }
  ]
 }
]
```

`portfolio.json`
```json
{
 "at": "2025-08-14T15:00:00Z",
 "counts": {
  "NORMAL": 1,
  "ELEVATED": 0,
  "HIGH": 1,
  "CRITICAL": 1
 },
 "total_exposed_value_eur": 20400000,
 "sites": [
  {
   "site_id": "ES-OU-001",
   "name": "Solar Trives 01",
   "type": "solar_farm",
   "lat": 42.33,
   "lon": -7.23,
   "radius_m": 600,
   "value_eur": 12400000,
   "personnel_on_site": 7,
   "criticality": 4,
   "score": 83,
   "level": "CRITICAL",
   "model_version": "rules-1.0",
   "factors": {
    "proximity": 30.7,
    "wind_alignment": 21.7,
    "weather": 11.0,
    "fuel": 12.0,
    "vulnerability": 8.0
   },
   "factor_status": {
    "proximity": "observed",
    "wind_alignment": "observed",
    "weather": "observed",
    "fuel": "customer_provided",
    "vulnerability": "customer_provided"
   },
   "nearest_fire_km": 3.1,
   "fire_bearing_deg": 225,
   "fire_moving_toward_site": true,
   "triggering_detection_id": "d-0001",
   "wind": {
    "speed_kmh": 26.0,
    "from_deg": 225,
    "to_deg": 45
   },
   "weather": {
    "temp_c": 34.2,
    "rh_pct": 18.0
   },
   "access_routes": [
    {
     "name": "Primary access",
     "bearing_deg": 200,
     "status": "potentially_exposed"
    },
    {
     "name": "Secondary access",
     "bearing_deg": 20,
     "status": "available"
    }
   ],
   "exposed_components": [
    {
     "name": "PV array",
     "value_eur": 8680000
    },
    {
     "name": "Inverter station",
     "value_eur": 1860000
    },
    {
     "name": "Substation",
     "value_eur": 1240000
    },
    {
     "name": "Control building",
     "value_eur": 620000
    }
   ],
   "sop_actions": [
    "Notify regional control centre",
    "Contact site manager and confirm personnel count",
    "Verify secondary access route is available",
    "Increase monitoring to every satellite pass",
    "Notify regional control centre immediately",
    "Contact site manager and confirm personnel location",
    "Move personnel to the safest available exit route",
    "Prepare controlled shutdown if authorised",
    "Notify emergency services according to company procedure"
   ]
  },
  {
   "site_id": "ES-OU-004",
   "name": "Substation Chandrexa 14",
   "type": "substation",
   "lat": 42.27,
   "lon": -7.34,
   "radius_m": 150,
   "value_eur": 8000000,
   "personnel_on_site": 2,
   "criticality": 5,
   "score": 55,
   "level": "HIGH",
   "model_version": "rules-1.0",
   "factors": {
    "proximity": 22.4,
    "wind_alignment": 5.6,
    "weather": 10.6,
    "fuel": 7.5,
    "vulnerability": 9.0
   },
   "factor_status": {
    "proximity": "observed",
    "wind_alignment": "observed",
    "weather": "observed",
    "fuel": "customer_provided",
    "vulnerability": "customer_provided"
   },
   "nearest_fire_km": 9.0,
   "fire_bearing_deg": 150,
   "fire_moving_toward_site": false,
   "triggering_detection_id": "d-0003",
   "wind": {
    "speed_kmh": 26.0,
    "from_deg": 225,
    "to_deg": 45
   },
   "weather": {
    "temp_c": 33.5,
    "rh_pct": 20.0
   },
   "access_routes": [
    {
     "name": "Primary access",
     "bearing_deg": 180,
     "status": "potentially_exposed"
    },
    {
     "name": "Secondary access",
     "bearing_deg": 0,
     "status": "available"
    }
   ],
   "exposed_components": [
    {
     "name": "Transformers",
     "value_eur": 4800000
    },
    {
     "name": "Switchgear",
     "value_eur": 2400000
    },
    {
     "name": "Control building",
     "value_eur": 800000
    }
   ],
   "sop_actions": [
    "Notify regional control centre",
    "Contact site manager and confirm personnel count",
    "Verify secondary access route is available",
    "Increase monitoring to every satellite pass",
    "Notify control room of substation exposure"
   ]
  },
  {
   "site_id": "ES-OU-013",
   "name": "Substation O Barco 09",
   "type": "substation",
   "lat": 42.415,
   "lon": -6.985,
   "radius_m": 150,
   "value_eur": 7200000,
   "personnel_on_site": 3,
   "criticality": 5,
   "score": 17,
   "level": "NORMAL",
   "model_version": "rules-1.0",
   "factors": {
    "proximity": 0.0,
    "wind_alignment": 0.0,
    "weather": 4.8,
    "fuel": 3.0,
    "vulnerability": 9.0
   },
   "factor_status": {
    "proximity": "observed",
    "wind_alignment": "observed",
    "weather": "observed",
    "fuel": "customer_provided",
    "vulnerability": "customer_provided"
   },
   "nearest_fire_km": null,
   "fire_bearing_deg": null,
   "fire_moving_toward_site": null,
   "triggering_detection_id": null,
   "wind": {
    "speed_kmh": 12.0,
    "from_deg": 225,
    "to_deg": 45
   },
   "weather": {
    "temp_c": 27.0,
    "rh_pct": 45.0
   },
   "access_routes": [
    {
     "name": "Primary access",
     "bearing_deg": 270,
     "status": "available"
    },
    {
     "name": "Secondary access",
     "bearing_deg": 90,
     "status": "available"
    }
   ],
   "exposed_components": [],
   "sop_actions": []
  }
 ]
}
```

`detections.json`
```json
[
 {
  "id": "d-0001",
  "source": "synthetic_fallback",
  "external_id": null,
  "lat": 42.312,
  "lon": -7.258,
  "observed_at": "2025-08-14T13:12:00Z",
  "received_at": "2026-09-18T10:00:00Z",
  "satellite": "N20",
  "confidence": "h",
  "intensity_frp": 41.3
 },
 {
  "id": "d-0002",
  "source": "synthetic_fallback",
  "external_id": null,
  "lat": 42.305,
  "lon": -7.262,
  "observed_at": "2025-08-14T13:12:00Z",
  "received_at": "2026-09-18T10:00:00Z",
  "satellite": "N20",
  "confidence": "n",
  "intensity_frp": 18.9
 },
 {
  "id": "d-0003",
  "source": "synthetic_fallback",
  "external_id": null,
  "lat": 42.241,
  "lon": -7.371,
  "observed_at": "2025-08-14T02:30:00Z",
  "received_at": "2026-09-18T10:00:00Z",
  "satellite": "N20",
  "confidence": "h",
  "intensity_frp": 55.0
 }
]
```

`alerts.json`
```json
[
 {
  "alert_id": "ES-OU-001_20250814T0900_CRITICAL",
  "site_id": "ES-OU-001",
  "site_name": "Solar Trives 01",
  "at": "2025-08-14T09:00:00Z",
  "kind": "escalation",
  "from_level": "HIGH",
  "to_level": "CRITICAL",
  "score": 79,
  "headline": "Fire 4.4 km SW, wind toward site",
  "triggering_detection_id": "d-0001",
  "factors": {
   "proximity": 28.8,
   "wind_alignment": 21.7,
   "weather": 8.5,
   "fuel": 12.0,
   "vulnerability": 8.0
  },
  "factor_status": {
   "proximity": "observed",
   "wind_alignment": "observed",
   "weather": "observed",
   "fuel": "customer_provided",
   "vulnerability": "customer_provided"
  },
  "model_version": "rules-1.0",
  "processed_at": "2026-09-18T10:00:03Z",
  "actions": [
   "Notify regional control centre",
   "Contact site manager and confirm personnel count",
   "Verify secondary access route is available",
   "Increase monitoring to every satellite pass",
   "Notify regional control centre immediately",
   "Contact site manager and confirm personnel location",
   "Move personnel to the safest available exit route",
   "Prepare controlled shutdown if authorised",
   "Notify emergency services according to company procedure"
  ],
  "rule_ids": [
   "R-001",
   "R-002"
  ],
  "acknowledged": false,
  "acknowledged_by": null,
  "acknowledged_at": null
 },
 {
  "alert_id": "ES-OU-001_20250814T0600_HIGH",
  "site_id": "ES-OU-001",
  "site_name": "Solar Trives 01",
  "at": "2025-08-14T06:00:00Z",
  "kind": "escalation",
  "from_level": "ELEVATED",
  "to_level": "HIGH",
  "score": 55,
  "headline": "Fire 8.7 km SW, wind toward site",
  "triggering_detection_id": "d-0003",
  "factors": {
   "proximity": 22.8,
   "wind_alignment": 7.5,
   "weather": 4.7,
   "fuel": 12.0,
   "vulnerability": 8.0
  },
  "factor_status": {
   "proximity": "observed",
   "wind_alignment": "observed",
   "weather": "observed",
   "fuel": "customer_provided",
   "vulnerability": "customer_provided"
  },
  "model_version": "rules-1.0",
  "processed_at": "2026-09-18T10:00:03Z",
  "actions": [
   "Notify regional control centre",
   "Contact site manager and confirm personnel count",
   "Verify secondary access route is available",
   "Increase monitoring to every satellite pass"
  ],
  "rule_ids": [
   "R-001"
  ],
  "acknowledged": true,
  "acknowledged_by": "operator@demo.eu",
  "acknowledged_at": "2026-09-18T10:05:00Z"
 }
]
```

`incidents.json`
```json
[
 {
  "incident_id": "ES-OU-001_20250814T0600",
  "site_id": "ES-OU-001",
  "site_name": "Solar Trives 01",
  "level": "CRITICAL",
  "score": 83,
  "opened_at": "2025-08-14T06:00:00Z",
  "closed_at": null,
  "headline": "Fire 3.1 km SW, wind toward site",
  "actions": [
   "Notify regional control centre",
   "Contact site manager and confirm personnel count",
   "Verify secondary access route is available",
   "Increase monitoring to every satellite pass",
   "Notify regional control centre immediately",
   "Contact site manager and confirm personnel location",
   "Move personnel to the safest available exit route",
   "Prepare controlled shutdown if authorised",
   "Notify emergency services according to company procedure"
  ],
  "rule_ids": [
   "R-001",
   "R-002"
  ],
  "disclaimer": "Recommended actions from the customer's approved protocol (simulated for demo). Not an autonomous safety decision."
 }
]
```

`rules.json`
```json
[
 {
  "rule_id": "R-001",
  "name": "High exposure: Level 2",
  "enabled": true,
  "priority": 10,
  "conditions": {
   "min_level": "HIGH",
   "asset_types": [],
   "min_criticality": 1,
   "wind_toward_site": null
  },
  "actions": [
   "Notify regional control centre",
   "Contact site manager and confirm personnel count",
   "Verify secondary access route is available",
   "Increase monitoring to every satellite pass"
  ]
 },
 {
  "rule_id": "R-002",
  "name": "Critical exposure: Level 3",
  "enabled": true,
  "priority": 20,
  "conditions": {
   "min_level": "CRITICAL",
   "asset_types": [],
   "min_criticality": 1,
   "wind_toward_site": null
  },
  "actions": [
   "Notify regional control centre immediately",
   "Contact site manager and confirm personnel location",
   "Move personnel to the safest available exit route",
   "Prepare controlled shutdown if authorised",
   "Notify emergency services according to company procedure"
  ]
 },
 {
  "rule_id": "R-003",
  "name": "Substation control room",
  "enabled": true,
  "priority": 30,
  "conditions": {
   "min_level": "HIGH",
   "asset_types": [
    "substation"
   ],
   "min_criticality": 1,
   "wind_toward_site": null
  },
  "actions": [
   "Notify control room of substation exposure"
  ]
 },
 {
  "rule_id": "R-004",
  "name": "Critical with wind toward site",
  "enabled": true,
  "priority": 40,
  "conditions": {
   "min_level": "CRITICAL",
   "asset_types": [],
   "min_criticality": 1,
   "wind_toward_site": true
  },
  "actions": [
   "Escalate to emergency protocol"
  ]
 }
]
```

`timeline.json`
```json
[
 {
  "at": "2025-08-14T03:00:00Z",
  "score": 38,
  "level": "ELEVATED",
  "nearest_fire_km": 14.2
 },
 {
  "at": "2025-08-14T06:00:00Z",
  "score": 55,
  "level": "HIGH",
  "nearest_fire_km": 8.7
 },
 {
  "at": "2025-08-14T09:00:00Z",
  "score": 79,
  "level": "CRITICAL",
  "nearest_fire_km": 4.4
 },
 {
  "at": "2025-08-14T12:00:00Z",
  "score": 82,
  "level": "CRITICAL",
  "nearest_fire_km": 3.4
 },
 {
  "at": "2025-08-14T15:00:00Z",
  "score": 83,
  "level": "CRITICAL",
  "nearest_fire_km": 3.1
 }
]
```

`summary.json`
```json
{
 "start": "2025-08-08T00:00:00Z",
 "end": "2025-08-26T00:00:00Z",
 "step_hours": 3,
 "data_source": "synthetic_fallback",
 "model_version": "rules-1.0",
 "total_detections": 720,
 "detections_used": 720,
 "alerts_raised": 43,
 "incidents": 30,
 "sites_ever_high": 17,
 "sites_ever_critical": 6,
 "sites_reached_by_fire": 7,
 "missed_exposures": 0,
 "median_lead_time_hours": 60.0,
 "explanation_coverage_pct": 100.0
}
```

`sources.json`
```json
[
 {
  "name": "FIRMS",
  "state": "FALLBACK",
  "detail": "Synthetic demo detections (FIRMS not reachable at data build time)"
 },
 {
  "name": "Weather",
  "state": "ONLINE",
  "detail": "Open-Meteo historical archive"
 },
 {
  "name": "Vegetation",
  "state": "FALLBACK",
  "detail": "Fuel class from customer asset data; no land-cover dataset yet"
 },
 {
  "name": "Notification",
  "state": "FALLBACK",
  "detail": "Email outbox only (SMTP not configured)"
 },
 {
  "name": "Database",
  "state": "ONLINE",
  "detail": "PostgreSQL"
 },
 {
  "name": "AI Advisor",
  "state": "ONLINE",
  "detail": "Groq openai/gpt-oss-120b"
 }
]
```

`runs.json`
```json
[
 {
  "run_id": "run-0001",
  "source": "synthetic_fallback",
  "started_at": "2026-09-18T10:00:00Z",
  "completed_at": "2026-09-18T10:00:02Z",
  "records_received": 720,
  "records_inserted": 720,
  "records_rejected": 0,
  "error_message": null
 }
]
```

`audit.json`
```json
[
 {
  "id": 2,
  "at": "2026-09-18T10:05:00Z",
  "actor": "operator@demo.eu",
  "action": "alert_acknowledge",
  "details": "ES-OU-001_20250814T0600_HIGH"
 },
 {
  "id": 1,
  "at": "2026-09-18T10:01:00Z",
  "actor": "admin@demo.eu",
  "action": "login",
  "details": ""
 }
]
```

`outbox.json`
```json
[
 {
  "alert_id": "ES-OU-001_20250814T0900_CRITICAL",
  "to": "control-room@demo.eu",
  "subject": "[CRITICAL] Solar Trives 01: Fire 4.4 km SW, wind toward site",
  "body": "Solar Trives 01 escalated HIGH -> CRITICAL at 2025-08-14T09:00:00Z (score 79). Open the platform for factors and actions.",
  "channel": "email",
  "status": "outbox"
 }
]
```

`import_report.json`
```json
{
 "accepted": 19,
 "rejected": [
  {
   "row": 7,
   "site_id": "ES-OU-007",
   "reason": "invalid fuel_class"
  }
 ],
 "total_sites": 19
}
```

`advisor.json`
```json
{
 "incident_id": "ES-OU-001_20250814T0600",
 "at": "2025-08-14T15:00:00Z",
 "generated_by": "groq",
 "model": "openai/gpt-oss-120b",
 "created_at": "2026-09-18T10:06:00Z",
 "evidence_keys": [
  "asset:criticality",
  "asset:personnel_on_site",
  "asset:type",
  "asset:value_eur",
  "component:Control building",
  "component:Inverter station",
  "component:PV array",
  "component:Substation",
  "detection:d-0001",
  "factor:fuel",
  "factor:proximity",
  "factor:vulnerability",
  "factor:weather",
  "factor:wind_alignment",
  "route:Primary access",
  "route:Secondary access",
  "rule:R-001",
  "rule:R-002",
  "rule:R-004",
  "weather:wind"
 ],
 "suggestions": [
  {
   "suggestion_id": "sug_1a2b3c4d",
   "title": "Confirm headcount of the 7 people on site",
   "detail": "Wind is carrying the fire toward the site and the site is CRITICAL. Confirm every person's location with the site manager now.",
   "audience": "site_team",
   "priority": 1,
   "evidence": [
    "asset:personnel_on_site",
    "weather:wind",
    "factor:wind_alignment"
   ],
   "decision": "approved",
   "decided_by": "operator@demo.eu",
   "decided_at": "2026-09-18T10:07:00Z"
  },
  {
   "suggestion_id": "sug_5e6f7a8b",
   "title": "Use Secondary access for any movement",
   "detail": "Primary access points toward the fire and is potentially exposed; Secondary access is currently available.",
   "audience": "site_team",
   "priority": 1,
   "evidence": [
    "route:Primary access",
    "route:Secondary access"
   ],
   "decision": null,
   "decided_by": null,
   "decided_at": null
  },
  {
   "suggestion_id": "sug_9c0d1e2f",
   "title": "Send the handoff pack to the fire service liaison",
   "detail": "The site has PV modules and an inverter station. Share hazards, water points and access routes so responders have the site information.",
   "audience": "fire_service_liaison",
   "priority": 2,
   "evidence": [
    "asset:type",
    "component:PV array",
    "component:Inverter station"
   ],
   "decision": null,
   "decided_by": null,
   "decided_at": null
  }
 ],
 "rejected_by_guardrails": 1,
 "fallback_reason": null,
 "disclaimer": "AI-generated suggestions for the company's own operations, grounded in the data shown. Not firefighting instructions. A human must approve every suggestion. Always follow the fire service's orders."
}
```

`decisions.json`
```json
[
 {
  "suggestion_id": "sug_1a2b3c4d",
  "incident_id": "ES-OU-001_20250814T0600",
  "title": "Confirm headcount of the 7 people on site",
  "decision": "approved",
  "note": "Site manager confirmed 7/7",
  "decided_by": "operator@demo.eu",
  "decided_at": "2026-09-18T10:07:00Z",
  "generated_by": "groq"
 }
]
```

`handoff.json`
```json
{
 "site_id": "ES-OU-001",
 "site_name": "Solar Trives 01",
 "type": "solar_farm",
 "at": "2025-08-14T15:00:00Z",
 "generated_at": "2026-09-18T10:08:00Z",
 "lat": 42.33,
 "lon": -7.23,
 "level": "CRITICAL",
 "score": 83,
 "headline": "Fire 3.1 km SW, wind toward site",
 "personnel_on_site": 7,
 "criticality": 4,
 "access_routes": [
  {
   "name": "Primary access",
   "bearing_deg": 200,
   "status": "potentially_exposed"
  },
  {
   "name": "Secondary access",
   "bearing_deg": 20,
   "status": "available"
  }
 ],
 "hazards": [
  {
   "name": "PV modules",
   "kind": "electrical",
   "note": "PV modules produce DC voltage whenever they are exposed to light and cannot be fully de-energised in daylight."
  },
  {
   "name": "Inverter station",
   "kind": "electrical",
   "note": "High-voltage equipment."
  }
 ],
 "water_points": [
  {
   "name": "Water tank A",
   "lat": 42.33277,
   "lon": -7.24029,
   "capacity_m3": 50
  },
  {
   "name": "Water tank B",
   "lat": 42.32723,
   "lon": -7.21971,
   "capacity_m3": 30
  }
 ],
 "contact": {
  "role": "Site manager (simulated)",
  "phone": "+34 600 000 001"
 },
 "simulated": true,
 "disclaimer": "Information for the fire service from the site operator (simulated demo data). The fire service decides all firefighting actions."
}
```

### 2.8 Changing the contract

Only the two humans can change Section 2, together. Then: update `docs/TEAM_PLAN.md`, bump `contract_version` on both sides the same day, and each agent re-reads Section 2. Agents never change it alone.

---

## 3. NO-CONFLICT RULES (both tracks, always)

1. **Folder ownership is absolute.** Track 1 writes only `backend/`, root `README.md`, root `.gitignore` and `docs/`. Track 2 writes only `frontend/`. Never edit, format, rename or delete anything outside your area, not even a typo.
2. **Branches:** `t1/<topic>` and `t2/<topic>`, merged into `main` by pull request (or direct push after `git pull --rebase origin main`). Folders never overlap, so rebases cannot conflict. A conflict means rule 1 was broken: **stop and tell the human.**
3. **Commit messages** start with `[T1]` or `[T2]`.
4. **Empty repo:** Track 1 makes the first commit (README, .gitignore, `docs/TEAM_PLAN.md`). If Track 2 is first, it commits `frontend/` only; the other rebases on top without conflict.
5. **Ignores:** Track 2 uses `frontend/.gitignore` only.
6. **Secrets never committed.** `backend/.env` is ignored; `backend/.env.example` is committed.
7. **Independence:** Track 2 must work fully on mocks before the backend exists. Track 1 must be testable with `pytest` and `curl` before the frontend exists.
8. **Contract mismatch?** Report the exact field, expected vs actual, to your human. Never patch around it silently.
9. **No root tooling** (no root `package.json`, no root venv).

---

## 4. Architecture decisions (both tracks read)

| Topic | Decision for the hackathon MVP | Why |
|---|---|---|
| Database | One adapter, two modes: **PostgreSQL** when `DATABASE_URL` is set (Neon, free, one click from the Vercel Marketplace), otherwise **SQLite** (`backend/data/app.db` locally, `/tmp/wai.db` on Vercel) | Vercel's disk is read-only except `/tmp`, which is wiped on restarts, so acknowledgements and rule edits need Postgres to survive on the demo URL. Same SQL tested on both. PostGIS is pilot phase |
| Geospatial | Pure Python haversine/bearing/buffers (Section 5.4) | Same maths as PostGIS `ST_Distance` for points; tested |
| Providers | `WildfireProvider`, `WeatherProvider`, `VegetationProvider`, `NotificationProvider` interfaces | Source-agnostic: FIRMS today, FireSat/cameras later without touching the risk engine |
| Risk engine | Transparent rules, `model_version = "rules-1.0"` | Explainable; bump version on any formula change |
| SOP | Rules choose **actions**; they do **not** change the score | Keeps scores comparable across customers |
| Alerts | Created on level **transitions** (Section 5.7), never on re-ingestion | Avoids alert spam |
| Notifications | Email **outbox** only in the MVP. Replay never sends real email | Safe demo, no mail setup |
| AI Advisor | LLM via **Groq** (HTTP, OpenAI-compatible) on Vercel; **Ollama** for local dev; **template** engine as final fallback. Output validated against evidence keys and a tactics filter | Demo never fails; suggestions stay grounded and inside the company's role |
| Auth | JWT HS256 (PyJWT), PBKDF2-SHA256 password hashes, tenant = `customer_id` on every row | Tested |
| Frontend | React + TypeScript + Vite, MapLibre, Recharts, **plain CSS** (no Tailwind) | Tested build; fewer config failure points |
| Deployment | **Two Vercel projects from the same repo**: Engine (root `backend`, FastAPI zero-config) and Console (root `frontend`, Vite). No Docker, no custom domain | Simplest public demo; each track deploys its own folder |
| Background jobs | None. Data built by scripts; live ingestion is an admin-triggered stretch | No Redis/Celery needed at this scale |

---

## 5. TRACK 1: ENGINE (backend) · default owner: Oussama

**Stack:** Python 3.12 (Vercel's default), FastAPI, Uvicorn, Pydantic v2, httpx, PyJWT, **python-multipart** (required by FastAPI for file uploads; without it the import endpoint crashes at startup), **psycopg[binary]** (Postgres), python-dotenv. Stdlib `sqlite3`, `csv`, `json`, `math`, `statistics`, `hashlib`, `secrets`. No pandas.

`requirements.txt` (runtime only, it is deployed to Vercel): `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `httpx`, `pyjwt`, `python-multipart`, `psycopg[binary]`, `python-dotenv`.
`requirements-dev.txt`: `-r requirements.txt` and `pytest`.
`.python-version`: `3.12`.

### 5.1 Folder structure

```
backend/
├── .env.example         FIRMS_MAP_KEY=  JWT_SECRET=  ASSUMED_WEATHER=true  DATABASE_URL=
│                        GROQ_API_KEY=  GROQ_MODEL=openai/gpt-oss-120b  OLLAMA_URL=  OLLAMA_MODEL=llama3.1
├── .python-version      3.12
├── vercel.json
├── requirements.txt  requirements-dev.txt
├── README.md
├── app/
│   ├── main.py            FastAPI app named `app` (Vercel entrypoint), CORS, routers. No startup work: see 5.9
│   ├── config.py          constants
│   ├── models.py          Pydantic mirrors of Section 2.4
│   ├── db.py              DB adapter (Postgres or SQLite, Section 5.3) + repository functions (all filter by customer_id)
│   ├── auth.py            hashing, JWT, get_current_user, require_admin
│   ├── geo.py             haversine, bearing, angdiff, compass, destination point
│   ├── providers/
│   │   ├── wildfire.py    WildfireProvider base, FileDetectionsProvider (reads data/detections.csv)
│   │   ├── weather.py     WeatherProvider base, ArchiveFileWeatherProvider, AssumedWeatherProvider
│   │   ├── vegetation.py  VegetationProvider base, AssetFuelClassProvider
│   │   ├── notification.py NotificationProvider base, OutboxProvider
│   │   └── llm.py         LLMProvider base, GroqProvider, OllamaProvider
│   ├── scoring.py         rules-1.0
│   ├── sop.py             rule matching
│   ├── replay.py          grid, per-customer precompute, alerts, incidents, summary
│   ├── importer.py        CSV/GeoJSON validation
│   ├── advisor.py         context, prompt, validation, template engine (5.10)
│   ├── handoff.py         handoff pack builder (5.11)
│   └── routes/            auth.py, assets.py, risk.py, alerts.py, sop.py, system.py, advisor.py
├── data/
│   ├── seed_sites.csv      the 20 demo sites (Section 5.3), also served as sample.csv
│   ├── detections.csv      committed output of the fetch script
│   ├── ingestion_runs.json committed output of the fetch scripts
│   ├── meta.json           {"data_source": ..., "fetched_at": ...}
│   └── weather/ES-OU-001.json ...
├── scripts/
│   ├── fetch_firms.py
│   ├── generate_synthetic_detections.py
│   └── fetch_weather.py
└── tests/
    ├── test_geo.py  test_scoring.py  test_sop.py  test_import.py
    ├── test_auth_tenancy.py  test_alerts.py  test_api_contract.py
    ├── test_db_both.py  test_advisor.py  test_handoff.py
```

All file paths are built from `Path(__file__).resolve()`, never from the working directory. `app.db` is ignored by Git.

### 5.2 Constants (`app/config.py`)

```python
CONTRACT_VERSION = "2.1.0"
MODEL_VERSION = "rules-1.0"
REPLAY_START = "2025-08-08T00:00:00Z"
REPLAY_END = "2025-08-26T00:00:00Z"   # exclusive
STEP_HOURS = 3
DETECTION_WINDOW_HOURS = 12
FIRE_RADIUS_KM = 25.0
CONTACT_KM = 1.0
ROUTE_EXPOSURE_KM = 10.0
BBOX = {"west": -7.9, "south": 41.8, "east": -6.7, "north": 42.6}
EARTH_RADIUS_KM = 6371.0088
LEVELS = [(25, "NORMAL"), (50, "ELEVATED"), (75, "HIGH"), (100, "CRITICAL")]
MAX_IMPORT_ROWS = 200    # keeps replay recompute well under Vercel limits (5.9)
TOKEN_HOURS = 12
ASSUMED_WEATHER = {"temp_c": 32.0, "rh_pct": 22.0, "speed_kmh": 20.0, "from_deg": 225}
NOTIFY_TO = {"demo": "control-room@demo.eu", "othercorp": "ops@othercorp.eu"}
LLM_TIMEOUT_S = 15
MAX_SUGGESTIONS = 6
```

### 5.3 Database adapter, schema and seed

**Adapter (tested on SQLite and PostgreSQL 16 with identical SQL):** if `DATABASE_URL` is set, use `psycopg` (`psycopg.connect(url, autocommit=True, row_factory=dict_row)`, one lazily created module-level connection, reconnect once on `OperationalError`). Otherwise SQLite: `/tmp/wai.db` when the `VERCEL` env var is set or `backend/data` is not writable, else `backend/data/app.db`. SQL is written with `?` placeholders; the adapter converts them to `%s` for Postgres. Only portable SQL is allowed: `insert ... on conflict do nothing`, `insert ... on conflict(cols) do update set data = excluded.data`. The only dialect difference is the audit id column: `integer primary key autoincrement` (SQLite) vs `bigserial primary key` (Postgres). Do not name a column `by` (reserved word in Postgres).

```sql
create table if not exists users(email text primary key, name text, customer_id text, role text, salt text, hash text);
create table if not exists assets(customer_id text, site_id text, data text, primary key(customer_id, site_id));
create table if not exists sop_rules(customer_id text, rule_id text, data text, primary key(customer_id, rule_id));
create table if not exists acks(customer_id text, alert_id text, acked_by text, acked_at text, primary key(customer_id, alert_id));
create table if not exists audit(id <AUTO>, customer_id text, at text, actor text, action text, details text);
create table if not exists advisor_suggestions(customer_id text, suggestion_id text, incident_id text, data text, created_at text, primary key(customer_id, suggestion_id));
create table if not exists advisor_decisions(customer_id text, suggestion_id text, decision text, note text, decided_by text, decided_at text, primary key(customer_id, suggestion_id));
```

Every query filters by the caller's `customer_id` from the token. Seeds use `on conflict do nothing`, so two instances starting at once cannot collide. Passwords: `hashlib.pbkdf2_hmac("sha256", password, salt, 200_000)` with a random salt per user. JWT payload `{"sub": email, "cid": customer_id, "role": role, "exp": now + 12h}`, HS256, secret from `JWT_SECRET` (dev default `dev-only-change-me`, log a warning if used). Open SQLite with `check_same_thread=False`.

**Seed on first use (only if the tables are empty):** the 3 users of Section 2.2; `demo` gets the 20 sites below and the 4 rules of `rules.json` (Section 2.7); `othercorp` gets one site `OC-001 Other Corp Depot`, substation, 42.340, -7.864, radius 100, value 2000000, fuel low, personnel 1, bearing 0, criticality 3, plus the same 4 rules.

| site_id | name | type | lat | lon | radius_m | value_eur | fuel_class | personnel | primary_access_bearing_deg | criticality |
|---|---|---|---|---|---|---|---|---|---|---|
| ES-OU-001 | Solar Trives 01 | solar_farm | 42.330 | -7.230 | 600 | 12400000 | high | 7 | 200 | 4 |
| ES-OU-002 | Solar Manzaneda 02 | solar_farm | 42.300 | -7.260 | 500 | 8700000 | high | 4 | 90 | 4 |
| ES-OU-003 | Wind Cabeza de Manzaneda | wind_farm | 42.265 | -7.290 | 1500 | 21000000 | very_high | 3 | 0 | 4 |
| ES-OU-004 | Substation Chandrexa 14 | substation | 42.270 | -7.340 | 150 | 8000000 | medium | 2 | 180 | 5 |
| ES-OU-005 | Forest Block Queixa A | forest_block | 42.230 | -7.400 | 2000 | 4200000 | very_high | 5 | 270 | 3 |
| ES-OU-006 | Wind Vilariño 01 | wind_farm | 42.170 | -7.260 | 1500 | 18500000 | high | 2 | 45 | 4 |
| ES-OU-007 | Telecom Tower Conso | telecom_tower | 42.160 | -7.300 | 50 | 350000 | high | 0 | 120 | 3 |
| ES-OU-008 | Substation Larouco 47 | substation | 42.360 | -7.140 | 150 | 9500000 | medium | 3 | 225 | 5 |
| ES-OU-009 | Solar Larouco 03 | solar_farm | 42.330 | -7.180 | 700 | 14000000 | high | 6 | 300 | 4 |
| ES-OU-010 | Forest Block Seadur B | forest_block | 42.380 | -7.100 | 2500 | 5600000 | very_high | 4 | 180 | 3 |
| ES-OU-011 | Telecom Tower Pena Trevinca | telecom_tower | 42.250 | -6.850 | 50 | 420000 | very_high | 0 | 90 | 3 |
| ES-OU-012 | Solar A Rua 01 | solar_farm | 42.400 | -7.110 | 600 | 10800000 | medium | 5 | 0 | 4 |
| ES-OU-013 | Substation O Barco 09 | substation | 42.415 | -6.985 | 150 | 7200000 | low | 3 | 270 | 5 |
| ES-OU-014 | Wind Serra do Eixe | wind_farm | 42.300 | -6.950 | 1500 | 16000000 | high | 2 | 315 | 4 |
| ES-OU-015 | Forest Block Viana C | forest_block | 42.180 | -7.110 | 2000 | 3900000 | high | 3 | 0 | 3 |
| ES-OU-016 | Solar Castro Caldelas 01 | solar_farm | 42.375 | -7.415 | 500 | 7900000 | medium | 4 | 135 | 4 |
| ES-OU-017 | Substation Montederramo 05 | substation | 42.280 | -7.500 | 150 | 6100000 | medium | 2 | 90 | 5 |
| ES-OU-018 | Solar Xinzo 02 | solar_farm | 42.060 | -7.720 | 800 | 15300000 | low | 8 | 45 | 4 |
| ES-OU-019 | Forest Block Oimbra D | forest_block | 41.900 | -7.470 | 2000 | 3300000 | high | 4 | 180 | 3 |
| ES-OU-020 | San Xoan de Rio Test Plot | test_plot | 42.366 | -7.286 | 80 | 25000 | medium | 1 | 90 | 1 |

ES-OU-020 is the team's real 2 ha plot (radius 80 m ≈ 2 ha): replace its coordinates with the real ones. Total demo value: €173,195,000.

**Import format** (CSV header, exact order; GeoJSON = FeatureCollection of Point features with the same properties minus lat/lon, taken from `coordinates` `[lon, lat]`):
`site_id,name,type,lat,lon,radius_m,value_eur,fuel_class,personnel_on_site,primary_access_bearing_deg,criticality`

**Validation per row** (row numbers start at 1 for the first data row): `site_id` matches `^[A-Za-z0-9_-]{1,40}$` and is unique in the file; `name` non-empty; `type` and `fuel_class` valid enums; lat −90..90, lon −180..180; `radius_m` 10..10000; `value_eur` ≥ 0; `personnel_on_site` ≥ 0; bearing 0..359; `criticality` 1..5. Decode with `utf-8-sig` (Excel BOM). Max 200 rows (422). If at least one row is valid: **replace** the customer's portfolio with the valid rows, recompute that customer's replay, write an audit entry. If none is valid: 422 with the report as `detail`, nothing changes.

**Components** are generated from `value_eur` by type (`round(value × share)`, rounding remainder added to the first component so the sum is exact):

| type | components (name: share) |
|---|---|
| solar_farm | PV array 0.70, Inverter station 0.15, Substation 0.10, Control building 0.05 |
| wind_farm | Turbines 0.80, Substation 0.15, Control building 0.05 |
| substation | Transformers 0.60, Switchgear 0.30, Control building 0.10 |
| forest_block | Standing timber 0.90, Forest roads 0.10 |
| telecom_tower | Tower and antennas 0.70, Power and backup 0.30 |
| test_plot | Weather station 0.60, Camera 0.40 |

**Vulnerability by type:** solar_farm 0.8, wind_farm 0.6, substation 0.9, forest_block 1.0, telecom_tower 0.7, test_plot 0.5. **Fuel factor:** low 0.2, medium 0.5, high 0.8, very_high 1.0 (provided by `AssetFuelClassProvider`; a land-cover provider can replace it later).

### 5.4 Geometry (`app/geo.py`)

- `haversine_km` with `EARTH_RADIUS_KM`.
- `bearing_deg(lat1, lon1, lat2, lon2)` = `(degrees(atan2(sin Δλ·cos φ2, cos φ1·sin φ2 − sin φ1·cos φ2·cos Δλ)) + 360) % 360`.
- `angdiff(a, b)` = `abs((a - b + 180) % 360 - 180)`.
- `compass(deg)` = `["N","NE","E","SE","S","SW","W","NW"][int((deg + 22.5) // 45) % 8]`.
- `edge_distance_km(site, det)` = `max(0, haversine_km(...) - radius_m / 1000)`.
- `destination(lat, lon, bearing, km)`: standard great-circle destination formula (used by the synthetic generator).

### 5.5 Scoring rules-1.0 (`app/scoring.py`)

Inputs: site, weather at `at` (with status), used detections with `at − 12h < observed_at <= at`. Used = confidence `n` or `h`.

```
Weather status: "observed" (archive file has the hour) | "assumed" (ASSUMED_WEATHER=true, constants) | "unknown"
c(x) = clamp(x, 0, 1)

weather_pts = 15 * mean(c((temp-20)/20), c((60-rh)/50), c(speed/40))   if weather known, else null
fuel_pts    = 15 * fuel_factor            status customer_provided
vuln_pts    = 10 * vulnerability          status customer_provided

candidates = detections with edge_distance_km <= 25
for each d in candidates:
    dist = edge_distance_km(site, d)
    prox = 35 * c(1 - dist/25)
    if weather known:
        wind_to = (from_deg + 180) % 360
        align = max(0, cos(radians(angdiff(wind_to, bearing_deg(d → site)))))
        wind_pts = 25 * align * min(1, speed/30)
    else: wind_pts = 0 (reported as null, status unknown)
    key = prox + wind_pts
choose max key; ties → smaller dist, then smaller detection id
no candidates → prox 0.0, wind 0.0 (status observed if weather known), fire fields null

total = sum of non-null points; score = min(100, floor(total + 0.5)); level from LEVELS
factor values rounded to 1 decimal

chosen detection d*:
  nearest_fire_km = round(dist*, 1); fire_bearing_deg = round(bearing_deg(site → d*)) % 360
  triggering_detection_id = d*.id
  if weather known: cosv = cos(radians(angdiff(wind_to, bearing_deg(d* → site))))
      fire_moving_toward_site = cosv > 0.5
      relation = "toward site" if cosv > 0.5 else "away from site" if cosv < -0.5 else "crosswind"
  else: fire_moving_toward_site = null, relation = "unknown"

access routes: primary from asset, secondary = (primary + 180) % 360;
  "potentially_exposed" if nearest_fire_km <= 10 and angdiff(route, fire_bearing_deg) <= 45, else "available"
```

Without a fire the maximum score is 40, so HIGH/CRITICAL (and therefore alerts) require a fire within 25 km. This is intentional.

### 5.6 SOP matching (`app/sop.py`)

A rule matches when it is enabled **and** `rank(level) >= rank(min_level)` **and** (`asset_types` empty or contains the site type) **and** `criticality >= min_criticality` **and** (`wind_toward_site` is null or equals `fire_moving_toward_site`; a null `fire_moving_toward_site` never matches a non-null condition). Sort matching rules by (`priority`, `rule_id`), concatenate their actions, drop duplicates keeping the first. Return `(actions, rule_ids)`.

### 5.7 Replay, alerts, incidents, summary (`app/replay.py`)

- Precompute per customer at startup and after every import: status of every site at all 144 steps. Keep in memory keyed by `customer_id`.
- **Alerts:** walk each site's steps with `prev = NORMAL` before the first step. At each step where `level != prev` and (`rank(level) >= 2` or `rank(prev) >= 2`), create an alert: `kind` = `escalation` if rank increases else `de-escalation`; `from_level = prev`, `to_level = level`; score, factors, headline, triggering detection of that step; `processed_at` = the precompute time; actions/rule_ids from current SOP rules; ack fields from the `acks` table.
- **Incidents:** consecutive steps at HIGH or CRITICAL. `opened_at` = first step; `closed_at` = first later step below HIGH or null. `level`/`score`/`headline` from the requested `at` if open, else the last open step.
- **Outbox:** one email per escalation alert: to `NOTIFY_TO[customer_id]`, subject `[{to_level}] {site_name}: {headline}`, body `{site_name} escalated {from_level} -> {to_level} at {at} (score {score}). Open the platform for factors and actions.`, status `outbox`. No real email is sent in the MVP.
- **Summary:** `total_detections` = rows in range; `detections_used` = after confidence filter; `alerts_raised` = escalation alerts; `incidents` = episodes; `sites_ever_high` / `sites_ever_critical`; reached by fire = first step with `nearest_fire_km <= 1.0`; lead time = hours from first ≥ HIGH step to that contact step if the HIGH came at or before it, otherwise `missed_exposures += 1`; `median_lead_time_hours` = median, 1 decimal, null if none; `explanation_coverage_pct` = share of alerts whose factors contain no `unknown` status, 1 decimal (100.0 if no alerts).
- **Audit actions:** `login`, `assets_import`, `sop_rule_create`, `sop_rule_update`, `sop_rule_delete`, `alert_acknowledge`, `advisor_generate`, `advisor_decision`.
- **Source status:** FIRMS `ONLINE` if `data_source` starts with `firms`, else `FALLBACK`; Weather `ONLINE` if every site has archive data, `FALLBACK` if any uses assumed values, `OFFLINE` if any is unknown; Vegetation `FALLBACK` "Fuel class from customer asset data; no land-cover dataset yet"; Notification `ONLINE` if SMTP env is set, else `FALLBACK` "Email outbox only (SMTP not configured)"; Database: Postgres → `ONLINE` "PostgreSQL"; SQLite in `/tmp` → `FALLBACK` "Temporary storage: resets when the server restarts. Connect Neon Postgres for the demo."; local SQLite file → `ONLINE` "SQLite (local file)"; failing `select 1` → `OFFLINE`. AI Advisor: `ONLINE` "Groq {model}" if `GROQ_API_KEY` is set, else `ONLINE` "Ollama {model}" if `OLLAMA_URL` is set, else `FALLBACK` "Template suggestions (no LLM configured)".

### 5.8 Data scripts (run once, commit the outputs)

**`scripts/fetch_firms.py`** (needs `FIRMS_MAP_KEY`, free from the FIRMS website)
- URL: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{west},{south},{east},{north}/1/{YYYY-MM-DD}`, one call per date (2025-08-08 to 2025-08-25) and source, 1 s sleep between calls.
- Sources `VIIRS_SNPP_SP`, `VIIRS_NOAA20_SP`; if both give zero rows for every date, retry with `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`.
- A valid response's first line starts with `latitude`; anything else is an error message: log it, count it as rejected, continue.
- `acq_time` is HHMM UTC and may lose leading zeros: `str(acq_time).zfill(4)`. `observed_at = {acq_date}T{HH}:{MM}:00Z`; `received_at` = fetch time; `external_id` = null; keep `satellite`, `confidence`, `frp` → `intensity_frp`.
- Deduplicate on (lat 4 dp, lon 4 dp, observed_at). Sort by `observed_at`, ids `d-0001`, `d-0002`, ...
- Write `data/detections.csv` with header `id,source,external_id,lat,lon,observed_at,received_at,satellite,confidence,intensity_frp`, append an `IngestionRun` to `data/ingestion_runs.json`, update `meta.json`. Cite NASA FIRMS in the README.
- If no rows can be produced, run the synthetic generator.

**`scripts/generate_synthetic_detections.py`** (offline, deterministic, `random.seed(42)`)
- Overpasses daily at 02:00 and 13:00 UTC.
- Fire A: ignition 42.245, −7.360 at `2025-08-08T13:00:00Z`, bearing 45°, 0.25 km/h, max radius 20 km, stops after `2025-08-20T13:00:00Z`.
- Fire B: ignition 42.340, −7.160 at `2025-08-13T13:00:00Z`, bearing 300°, 0.30 km/h, max radius 25 km, stops after `2025-08-24T13:00:00Z`.
- Per overpass after ignition: `r = min(max_radius, speed × hours)`; 15 points at `max(0.2, r + uniform(-1, 1))` km and bearing `main + uniform(-60, 60)` via `destination`. Confidence `h` with probability 0.6 else `n`; `intensity_frp = round(uniform(5, 80), 1)`; satellite `N20`; source `synthetic_fallback`.
- Same CSV format, an `IngestionRun` with source `synthetic_fallback`, `meta.json` data_source `synthetic_fallback`. Expected: 720 detections.

**`scripts/fetch_weather.py`**
- Per site: `https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-08-08&end_date=2025-08-25&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m&wind_speed_unit=kmh&timezone=GMT`
- Save `hourly` to `data/weather/{site_id}.json`. Times are `2025-08-08T00:00` in GMT = UTC. `wind_direction_10m` is where the wind comes **from**.
- Imported sites without a file use `AssumedWeatherProvider` if `ASSUMED_WEATHER=true`, else weather is `unknown`.

### 5.9 Running on Vercel (serverless rules)

- **No startup work.** Do not rely on startup/lifespan events. Every route calls `ensure_ready()` first: under a `threading.Lock`, it creates the schema, seeds, and loads data once per server instance (module-level flag). Cold starts must stay fast.
- **Replay is computed lazily per customer** on first request and cached in memory per instance; recomputed after an import.
- **Required optimization (measured):** bucket detections per grid step once (`at − 12h < observed_at <= at`), then per site keep only detections inside a lat/lon box of `(25 km + radius) / 111` degrees latitude and the same divided by `cos(lat)` in longitude before computing exact distances. Reference timings: 0.16 s for 20 sites, 2.2 s for 500 sites; without it, about 1.6 s for 20 sites and roughly 40 s for 500.
- `backend/vercel.json`:
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "app/main.py": { "maxDuration": 60, "excludeFiles": "{tests/**,scripts/**}" }
  }
}
```
- `data/` must stay in the bundle (it is read at runtime); never write to it on Vercel.
- Environment variables are set in the Vercel project settings (Section 7), never committed.

### 5.10 AI Advisor (`app/advisor.py`, `app/providers/llm.py`)

**Flow for `POST /api/advisor/incidents/{incident_id}?at=`:**
1. Load the incident and the site's `SiteStatus` at `at` (the incident's `at` rules apply).
2. Build the **context** (JSON) and the list of `evidence_keys`: `factor:` each factor name; `route:` each route name; `rule:` each matching rule id; `asset:personnel_on_site`, `asset:type`, `asset:criticality`, `asset:value_eur`; `component:` each exposed component; `weather:wind` if wind is known; `detection:<id>` if there is a triggering detection. Sort keys alphabetically.
3. Try engines in order, stopping at the first that yields at least one valid suggestion: **Groq** if `GROQ_API_KEY` is set, **Ollama** if `OLLAMA_URL` is set, then the **template engine** (always works). Record `fallback_reason` when a later engine was used: `"no LLM configured"`, `"LLM error: <short message>"` or `"LLM output failed validation"`.
4. Store each suggestion in `advisor_suggestions` (data = JSON of the response entry plus `generated_by`, `incident_id`, `title`), write audit `advisor_generate`, return `AdvisorResponse` with `created_at` = now, `at` = snapped `at`.

**Groq call:** `POST https://api.groq.com/openai/v1/chat/completions`, header `Authorization: Bearer $GROQ_API_KEY`, body `{"model": GROQ_MODEL, "temperature": 0.2, "max_tokens": 1200, "response_format": {"type": "json_object"}, "messages": [system, user]}`; text in `choices[0].message.content`. Default model `openai/gpt-oss-120b` (a Groq production model as of Sept 2026; if Groq has retired it, pick a current production model from the Groq console and set `GROQ_MODEL`). Timeout `LLM_TIMEOUT_S`.
**Ollama call (local dev only):** `POST {OLLAMA_URL}/api/chat` with `{"model": OLLAMA_MODEL, "stream": false, "format": "json", "messages": [...]}`; text in `message.content`.

**System prompt (use verbatim):**
```text
You advise the operations team of a company that owns the site described in the context. A wildfire may threaten the site.
Rules:
1. Give at most 6 suggestions for the company's own operations: the operator in the control room, the site team, or what information to share with the fire service liaison.
2. Never give firefighting tactics or instructions to firefighters. Never suggest approaching the fire. The fire service decides all firefighting actions; the company follows its orders.
3. Base every suggestion only on the context. Each suggestion must cite one or more evidence keys, copied exactly from EVIDENCE_KEYS.
4. Be concrete and short. No speculation about how the fire will spread.
Return only JSON: {"suggestions":[{"title": string (max 120 chars), "detail": string (max 600 chars), "audience": "operator"|"site_team"|"fire_service_liaison", "priority": 1|2|3, "evidence": [string]}]}
```
**User message:** `EVIDENCE_KEYS: <json list>\nCONTEXT: <json>` where the context holds site name, type, criticality, personnel, level, score, factors with statuses, wind, weather, nearest fire km and compass, fire moving toward site, access routes, exposed components, matching rules with their actions.

**Validation (tested; a suggestion is dropped and counted in `rejected_by_guardrails` if any check fails):** valid JSON with a `suggestions` list; non-empty `title` (≤ 120 chars) and `detail` (≤ 600); `audience` in the three allowed values; `priority` 1–3; `evidence` non-empty and every key in `evidence_keys`; title + detail do **not** match this case-insensitive regex: `back[- ]?burn|backfire|contrafuego|firebreak|fire ?line|cortafuego|extinguish|suppress|attack the fire|water drop|drop water|approach the fire|fight the fire|tactic`. Keep at most 10 input items, return at most 6 valid ones sorted by priority. If none is valid, move to the next engine. Suggestion ids: `sug_` + 8 hex chars (`secrets.token_hex(4)`).

**Template engine (deterministic, used when no LLM works).** Emit in this order, skipping those whose condition is false, max 6:

| # | Condition | Title | Audience | Priority | Evidence |
|---|---|---|---|---|---|
| T1 | personnel > 0 and level ≥ HIGH | `Confirm headcount of the {n} people on site` | site_team | 1 | asset:personnel_on_site |
| T2 | a route is potentially_exposed and another is available | `Use {available route} for any movement` | site_team | 1 | both route keys |
| T3 | both routes potentially_exposed | `Both access routes may be exposed: keep people away from the perimeter and ask the fire service liaison for guidance` | site_team | 1 | both route keys |
| T4 | fire_moving_toward_site is true | `Wind is carrying the fire toward the site: prepare the protocol actions now` | operator | 1 | weather:wind, each rule key |
| T5 | level CRITICAL and type is solar_farm, substation, wind_farm or telecom_tower | `Send the handoff pack to the fire service liaison` | fire_service_liaison | 2 | asset:type |
| T6 | weather status is assumed or unknown | `Weather for this site is {assumed|unknown}: verify local wind before acting` | operator | 2 | factor:weather |
| T7 | level ≥ HIGH | `Review the protocol actions and record which were taken` | operator | 3 | each rule key (skip T7 if there are no rules) |

`detail` for template items: one sentence restating the evidence values (e.g. "Primary access points toward the fire (potentially exposed); Secondary access is available."). `generated_by = "template"`, `model = null`.

**Decisions:** `POST /api/advisor/suggestions/{id}/decision` inserts into `advisor_decisions` with `on conflict do nothing`, reads back the stored row (first decision wins), writes audit `advisor_decision`, returns `DecisionRecord`. `GET .../latest` returns the most recent response for that incident with decision fields filled from `advisor_decisions`.

### 5.11 Handoff Pack (`app/handoff.py`)

`GET /api/sites/{site_id}/handoff?at=` builds from the site status at `at`:
- `headline`, `level`, `score`, `access_routes`, `personnel_on_site`, `criticality` from the status.
- **Hazards by type** (factual, generic):

| type | hazards (name · kind · note) |
|---|---|
| solar_farm | PV modules · electrical · PV modules produce DC voltage whenever they are exposed to light and cannot be fully de-energised in daylight. / Inverter station · electrical · High-voltage equipment. |
| substation | Transformers · electrical · High-voltage equipment. / Transformer insulating oil · fuel_oil · Oil-filled transformers contain flammable insulating oil. |
| wind_farm | Turbines · height · Falling debris possible if a nacelle burns; keep clear of the tower base. / Substation · electrical · High-voltage equipment. |
| telecom_tower | Backup batteries · battery · Backup batteries and electrical equipment. / Tower · height · Height hazard. |
| forest_block | No built hazards · none · Standing timber; limited road access. |
| test_plot | Weather station and camera · electrical · Low-voltage equipment only. |

- **Water points (simulated):** "Water tank A" 50 m³ at bearing `(primary + 90) % 360` and "Water tank B" 30 m³ at bearing `(primary + 270) % 360`, both at `radius_m/1000 + 0.3` km from the site centre (use `destination`), coordinates rounded to 5 decimals.
- **Contact:** role `Site manager (simulated)`, phone `+34 600 000 ` + the last 3 digits of `site_id` (or `000` if it has fewer than 3 digits).
- `generated_at` = now; `simulated = true`; `disclaimer` from Section 2.6.

### 5.12 Milestones (Track 1)

**T1-M1 · Skeleton** (`[T1] skeleton`): root README, `.gitignore` (Python, `.env`, `*.db`, `node_modules/`, `dist/`), `docs/TEAM_PLAN.md`; FastAPI app, `models.py`, `/api/health`. Done when `uvicorn app.main:app --port 8000` runs and `curl localhost:8000/api/health` matches `Health`.

**T1-M2 · Data** (`[T1] data`): three scripts run; `detections.csv`, `ingestion_runs.json`, `meta.json`, `weather/*.json`, `seed_sites.csv` committed. Done when detections lie inside BBOX and dates, and `meta.json` states the true source.

**T1-M3 · Engine** (`[T1] engine`): `geo.py`, providers, `scoring.py`, `sop.py`, `replay.py` with the 5.9 optimization. Tests that must pass:
- `bearing_deg(42,-7,43,-7)` ≈ 0 and `bearing_deg(42,-7,42,-6)` ≈ 90 (±1°); `angdiff(350,10) == 20`; `compass(225) == "SW"`, `compass(350) == "N"`.
- Level edges 25/26/50/51/75/76.
- No detections → score ≤ 40. Detection at the site edge with wind straight at the site at 30 km/h → proximity 35.0, wind_alignment 25.0.
- Weather unknown → `weather` and `wind_alignment` null with status `unknown`, `fire_moving_toward_site` null, headline ends `wind unknown`.
- Components sum to `value_eur`.
- SOP: with rules R-001..R-004 from the mocks, a CRITICAL substation with wind toward site returns actions of R-001, R-002, R-003, R-004 in that order with duplicates removed; a disabled rule never matches; ELEVATED returns `[]`.
- Alerts: a sequence NORMAL, ELEVATED, HIGH, CRITICAL, HIGH, ELEVATED produces escalations to HIGH and CRITICAL and de-escalations CRITICAL→HIGH and HIGH→ELEVATED (4 alerts).
- With synthetic data: 720 detections, some sites reach CRITICAL, `missed_exposures` is reported (reference run gave 17 sites HIGH, 6 CRITICAL, 7 reached, 0 missed, 43 escalations).

**T1-M4 · Auth, tenancy, import** (`[T1] auth-import`): `db.py` (both modes), `auth.py`, seed, `importer.py`. `test_db_both.py` runs the same assertions on SQLite and, when `TEST_DATABASE_URL` is set, on Postgres: idempotent seed, rule upsert, first-ack-wins, audit autoincrement and tenant filter. Other tests: wrong password 401; no/garbage token 401; operator import 403; admin CSV import with one valid and two invalid rows → accepted 1, rejected rows `[2, 3]`; GeoJSON import works; `.txt` → 422; `othercorp` sees only `OC-001` and gets 404 for `ES-OU-001`; audit shows login, import and acknowledgement, only for the own customer.

**T1-M5 · Full API** (`[T1] api`): every endpoint of Section 2.5. `test_api_contract.py` calls each one with `TestClient`, validates with the Pydantic models, checks sorting, `at` snapping (`2025-08-14T16:40:00Z` → `2025-08-14T15:00:00Z`) and clamping (`2030-01-01T00:00:00Z` → `2025-08-25T21:00:00Z`), 404 bodies, and that acknowledging an alert twice keeps the first acknowledgement. Done when `pytest` passes and `curl` with a token returns 20 sites from `/api/portfolio`.

**T1-M6 · AI Advisor and Handoff** (`[T1] advisor`): 5.10 and 5.11. Tests: the validator keeps a good suggestion and drops one with tactics wording, one citing an unknown key and one with a wrong audience (`rejected_by_guardrails == 3`); invalid JSON, `{}` and all-invalid output raise and fall through to the next engine; with no LLM env vars the response has `generated_by == "template"` and `fallback_reason == "no LLM configured"`; a CRITICAL solar site with 7 people, one exposed and one available route, wind toward site yields T1, T2, T4, T5, T7 in that order; decisions are first-wins and audited; handoff water points for ES-OU-001 are (42.33277, -7.24029) and (42.32723, -7.21971). Mock the HTTP calls in tests; never call Groq in CI.

**T1-M7 · Vercel deploy and docs** (`[T1] deploy`): `vercel.json`, `.python-version`, README (local run, demo accounts, env vars, data sources with citations, model disclaimer, advisor limits). Deploy as in Section 7. Done when `https://<engine>.vercel.app/api/health` returns `contract_version` 2.1.0 and the source status shows Database `ONLINE` (Postgres).

**Stretch (after M7):** (1) `POST /api/ingestion/firms/live` (admin): fetch `VIIRS_NOAA20_NRT` last day for BBOX into a separate live dataset; must never alter the replay. (2) PostGIS queries behind the same `db.py` functions. Neither may change the contract.

---

## 6. TRACK 2: CONSOLE (frontend) · default owner: @callmegema

**Stack:** **Node 22 LTS** (also what Vercel builds with by default for new projects; if the project setting shows an older version, set it to 22.x) (Vite 8 requires Node `^20.19.0 || >=22.12.0`; older Node 20 releases fail), Vite + React + TypeScript, `react-router-dom@6`, `maplibre-gl@4`, `recharts@2`, plain CSS with CSS variables. No state library.

Create from the repo root: `npm create vite@latest frontend -- --template react-ts --no-interactive` (if a prompt still appears: React + TypeScript, and **No** to "install and start now"), then `cd frontend && npm install react-router-dom@6 maplibre-gl@4 recharts@2`.

### 6.1 Folder structure

```
frontend/
├── .gitignore  .env.example (VITE_API_BASE_URL=http://localhost:8000, VITE_USE_MOCKS=true)
├── vercel.json
└── src/
    ├── main.tsx  App.tsx  styles.css
    ├── api/ types.ts (2.4 verbatim) · client.ts · levels.ts
    ├── mocks/ the 18 JSON files of 2.7
    ├── state/ AuthContext.tsx · TimeContext.tsx
    ├── components/ TopBar · LevelBadge · SiteMap · FactorBars · FactorStatusChip · Disclaimer · Banner · RequireAuth · AdminOnly · AdvisorPanel · EvidenceChip
    └── pages/ LoginPage · PortfolioPage · SitePage · IncidentPage · AlertsPage · HistoryPage · AssetsPage · RulesPage · SystemPage · FieldPage · HandoffPage
```

### 6.2 API client (`api/client.ts`)

- `BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"`; `USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true"`.
- One typed function per endpoint of 2.5. Sends `Authorization: Bearer <token>` from `AuthContext` (token kept in `sessionStorage` under `wai_token`).
- **Importing mock JSON (tested, required):** TypeScript widens JSON strings to `string`, so `const p: Portfolio = portfolioJson` does not compile. Always cast `portfolioJson as unknown as Portfolio`.
- Mock mode: login accepts the three accounts of 2.2 with `demo1234` (role from the table), returns `login.json` with that user; all reads return mocks (demo customer); acknowledge, rule edits, import and advisor decisions update in-memory copies so the UI behaves realistically until reload; "Generate advice" returns `advisor.json` after an artificial 800 ms delay; unknown ids throw "not found".
- Live mode: 401 → clear token, go to `/login`. 403 → toast "Admin only". Network error or 5xx → fall back to mocks and show banner "Engine offline: showing mock data".
- On start, `GET /api/health`: if `contract_version !== "2.1.0"`, red banner "Contract mismatch: engine {x}, console 2.1.0", keep working.
- Debounce time-driven requests 250 ms; ignore responses for an outdated `at`.

### 6.3 Time control

Range and step from `/api/health`. `at` lives in the URL (`?at=`) and survives navigation. Slider over all steps, ◀ 3h, ▶ 3h, Play/Pause (1 step per second). Display `14 Aug 2025, 15:00 UTC`.

### 6.4 Pages

- **Login `/login`:** email, password, error message on 401, demo accounts listed under the form.
- **Portfolio `/`:** level count tiles, exposed value, list in API order (never re-sort), map with sites (colour by level, size by value) and 12 h detections; "Open incidents" strip; unacknowledged-alerts counter linking to `/alerts`.
- **Site `/sites/:siteId`:** map zoom 11; factor bars with a status chip per factor (`observed`, `customer_provided`, `assumed`, `unknown`; unknown shows "UNKNOWN", never 0); weather and wind (or "Weather unknown"); fire moving toward site (yes / no / unknown); access routes; exposed components; personnel; criticality; triggering detection id with observed and received times; current SOP actions; timeline chart 0–100 with reference lines at 25/50/75 and a marker at `at`; link to Field view.
- **Incident `/incidents/:incidentId`:** banner in level colour; blocks Threat, Exposure, Why (factor bars), Action (SOP actions as local checkboxes) and the `disclaimer` verbatim. Below: **AdvisorPanel** and a "Handoff pack" button → `/sites/:siteId/handoff?at=`.
- **AdvisorPanel:** on open, `GET .../latest` (404 → empty state). Button "Generate advice" (spinner, disabled while running; the call can take up to ~15 s). Header shows engine badge (`Groq`, `Ollama` or `Template (no AI)`), model, `created_at`, "{rejected_by_guardrails} suggestions blocked by safety rules" when > 0, and `fallback_reason` when present. Each suggestion: priority, audience label (Operator / Site team / Fire service liaison), title, detail, evidence chips (`route:Primary access` shows as "Route: Primary access"), and **Approve / Reject** buttons with an optional note; after deciding, show "Approved by {decided_by}" instead of buttons. Show the advisor `disclaimer` verbatim at the bottom. Label the panel "AI Advisor (suggestions need human approval)".
- **Handoff `/sites/:siteId/handoff`:** printable A4 page: site name, level and headline, coordinates, personnel, access routes with status, hazards table, water points with coordinates, contact, `generated_at`, disclaimer. Buttons: "Print" (`window.print()`) and "Copy as text" (plain-text version via `navigator.clipboard.writeText`). Print CSS hides navigation, TopBar and footer.
- **Alerts `/alerts`:** table newest first: time, site, from → to (coloured), score, headline, rules, acknowledged by/at or an "Acknowledge" button; filter all/unacknowledged; row expands to factors and actions.
- **History `/history`:** summary cards (all `ReplaySummary` numbers, lead time "n/a" if null), the sentence "{total_detections} satellite detections became {alerts_raised} alerts across {incidents} incidents", incident history table, data-source line.
- **Assets `/assets`:** "Download sample CSV" (fetch with token, save as `sample_assets.csv`); admin: file input (.csv/.geojson/.json) + Import button, then show `ImportReport` (accepted, rejected table with row and reason); operator: read-only asset table. Warn before import: "This replaces your portfolio."
- **Rules `/rules`:** list of SOP rules; admin can create, edit (name, enabled, priority, min level, asset types multi-select, min criticality 1–5, wind toward site any/yes/no, actions one per line) and delete with confirmation; operator read-only.
- **System `/system`:** source status list with coloured dots (ONLINE green, FALLBACK amber, OFFLINE red, NOT_CONFIGURED grey); ingestion runs table; email outbox for the current `at`; audit log and **AI decisions** table from `/api/advisor/decisions` (admin only) with the caption "Human decisions on AI suggestions: our learning dataset".
- **Field `/field/:siteId`:** mobile card (max 420 px): level block, "{km} km {compass}", "Wind {from} → {to}" or "Wind unknown", secondary route status, "Contact: Operations Centre".

**Always visible:** TopBar with data-source badge (`firms_sp` "NASA FIRMS", `firms_nrt` "NASA FIRMS (NRT)", `synthetic_fallback` "Synthetic demo data"), `model_version`, user email + role + Logout. Footer on every page: "MVP decision-support model, not a validated prediction model. Sites, values, personnel and protocols are simulated. Fire data is near-real-time detections, not perimeters." Map attribution `© OpenStreetMap contributors`.

### 6.5 Map (MapLibre, no key)

```ts
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
const style: StyleSpecification = {
  version: 8,
  sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256,
                    attribution: "© OpenStreetMap contributors" } },
  layers: [{ id: "osm", type: "raster", source: "osm" }]
};
// portfolio: center [-7.25, 42.28], zoom 9. MapLibre uses [lon, lat].
```
Update GeoJSON sources with `setData`; never recreate the map per time step.

### 6.6 Vercel files (Track 2 owns these)

`frontend/vercel.json` (client-side routes survive a page refresh):
```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/" }] }
```
Commit `package-lock.json`. `VITE_*` variables are baked in **at build time**: after changing them in Vercel, redeploy.

### 6.7 Milestones (Track 2)

**T2-M1 · Skeleton on mocks** (`[T2] skeleton`): app, routes, types, 15 mocks, client with mock mode, AuthContext + login, TimeContext + TopBar, footer. Done when `npm run dev` lets you log in as admin@demo.eu and see 3 mock sites, and `npx tsc --noEmit -p tsconfig.app.json` passes.

**T2-M2 · Portfolio, Site, map** (`[T2] portfolio-site`): done when both pages render from mocks with factor status chips and `?at=` persists.

**T2-M3 · Incident, Alerts, Field, Advisor, Handoff** (`[T2] alerts-advisor`): done when acknowledging an alert in mock mode updates the row, the AdvisorPanel generates (mock), approves and rejects, the Handoff page prints cleanly (check print preview), and the Field page fits a 390 px wide screen.

**T2-M4 · History, Assets, Rules, System** (`[T2] admin`): done when an operator account cannot see edit controls, admin can edit a rule in mock mode, and `npm run build` succeeds.

**T2-M5 · Resilience and Vercel** (`[T2] deploy`): done when, with `VITE_USE_MOCKS=false` and no backend, the app shows the offline banner and mock data without crashing; `vercel.json` committed; the Console is deployed as in Section 7 and a hard refresh on `/alerts` still loads.

---

## 7. VERCEL DEPLOYMENT AND INTEGRATION CHECK

### 7.1 Deploy (both humans, 15 minutes, free Hobby plan, no domain)

1. **Engine project (Track 1's human):** vercel.com → Add New → Project → import the repo → **Root Directory = `backend`** → framework is detected as FastAPI → Deploy.
2. **Database:** in the Engine project → Storage (Marketplace) → **Neon Postgres** → create (free) → connect to the project. `DATABASE_URL` is injected automatically.
3. **Engine env vars** (Settings → Environment Variables): `JWT_SECRET` (a long random string), `GROQ_API_KEY` (free key from console.groq.com), `GROQ_MODEL=openai/gpt-oss-120b`, `ASSUMED_WEATHER=true`. Redeploy.
4. Check `https://<engine>.vercel.app/api/health` and `/api/status/sources` (after login) show contract 2.1.0, Database ONLINE, AI Advisor ONLINE.
5. **Console project (Track 2's human):** Add New → Project → same repo → **Root Directory = `frontend`** → framework Vite → env vars `VITE_API_BASE_URL=https://<engine>.vercel.app` (no trailing slash) and `VITE_USE_MOCKS=false` → Deploy.
6. Share the **Production** URLs (from the `main` branch). Vercel may protect *preview* deployments behind a Vercel login, so judges must get the Production URL.
7. Optional safety net: a third project (or a preview) of the Console with `VITE_USE_MOCKS=true` works even if the Engine is down.

### 7.2 Local check (after T1-M5 and T2-M4)

1. `cd backend && pip install -r requirements-dev.txt && uvicorn app.main:app --port 8000`
2. `cd frontend && VITE_USE_MOCKS=false npm run dev`

### 7.3 Checklist (run locally, then again on the Vercel URLs)
   - [ ] No offline or contract-mismatch banner.
   - [ ] Login as admin@demo.eu: 20 sites, correct data-source badge.
   - [ ] Slider 8 → 20 Aug turns sites near the fires from green to red; alerts appear; acknowledge one as operator@demo.eu and see it in the audit log as admin.
   - [ ] Import `sample_assets.csv` from the Assets page: 20 accepted.
   - [ ] Edit a rule's actions; the Incident page shows the new actions.
   - [ ] Login as other@othercorp.eu: only `OC-001` is visible.
   - [ ] History numbers equal `/api/replay/summary`.
   - [ ] Stop the backend: offline banner, no crash.
   - [ ] On an incident, "Generate advice" returns suggestions with evidence chips; approve one; it appears in System → AI decisions. With `GROQ_API_KEY` removed, the engine badge shows "Template (no AI)" and it still works.
   - [ ] The Handoff pack prints on one or two pages and "Copy as text" works.
   - [ ] On Vercel: acknowledge an alert, wait 15 minutes, reload: the acknowledgement is still there (proves Postgres is connected).
4. A failure is fixed by the owner of the failing folder. Contract ambiguity → humans decide and update Section 2.

---

## 8. DEMO SCRIPT (2 minutes)

1. Log in as operator. Portfolio at 8 Aug 00:00: no fire yet, sites NORMAL or ELEVATED only. "20 sites, €173M of assets, one screen."
2. Press Play. Detections appear near Chandrexa; sites turn orange then red; the alert counter climbs.
3. Pause around 14 Aug. Open the top incident: threat, exposure, why (with factor status), actions from the customer's own rules.
4. Acknowledge the alert. Click "Generate advice": the AI suggests what the company should do, each point citing its evidence. Approve one, reject one. "Every decision is logged: that's how the model learns from real operators."
5. Open the Handoff pack: "This is what we send the fire service: hazards, water points, access. We inform firefighters; we never tell them how to fight the fire."
6. System page: sources, outbox email, audit entry, AI decisions.
7. Field view on a phone.
8. History: "{total_detections} detections became {alerts_raised} alerts, median lead time {x} h, {missed_exposures} missed." Read the real numbers.
9. Close: "The last site on the list is our own 2 hectares in San Xoán de Río."

---

## 9. Spec traceability (where the technical specification landed)

| Spec section | Status in this plan |
|---|---|
| §2.1 core features 1–14 | All in MVP: ingestion (5.8), CSV/GeoJSON import (5.3), map (6.4), distances and buffers (5.4–5.5), enrichment (providers), explainable score (5.5), triage (2.5), alerts (5.7), SOP (5.6), backtest (5.7), audit (5.7), auth + tenancy (2.2, 5.3), deployment (Vercel, Section 7) |
| §2.2 out of scope | Respected |
| §3, §7 PostgreSQL + PostGIS | PostgreSQL (Neon) on Vercel, SQLite locally, one adapter. PostGIS spatial queries are pilot phase |
| §4 Tailwind, Pandas, Redis, Celery | **Deviation:** plain CSS; no Pandas/Redis/Celery (not needed at 20–500 assets) |
| §5–6 FIRMS, normalized FireDetection | `Detection` type with `observed_at`/`received_at`, `external_id`, intensity; raw FIRMS CSV kept by the script run log |
| §8 geospatial processing | Python equivalents of `ST_DWithin`/`ST_Distance` for points (5.4–5.5) |
| §9 risk engine | rules-1.0 with visible factors; SOP adjustment **not** in the score (Section 4) |
| §11 SOP engine | `SopRule` with conditions from the spec examples (R-003, R-004 in mocks) |
| §15–16, §18 provider interfaces | `WeatherProvider`, `VegetationProvider`, `WildfireProvider`, `NotificationProvider` |
| §19 ingestion runs | `IngestionRun` + `/api/ingestion/runs` |
| §20 detection vs fire event | Detection dedup in scripts; incidents group detections per site. Cross-site fire-event clustering is pilot phase |
| §21–22 alert transitions, channels | Transition-based alerts; email outbox; SMTP/SMS/WhatsApp later |
| §23 API | Covered with `/api` prefix and the names in 2.5 |
| §24–25 auth, tenancy, security | JWT, PBKDF2, roles, `customer_id` filtering, secrets in env. HTTPS and rate limiting are pilot phase (use the hosting provider's HTTPS) |
| §32 unknown data | `factor_status` and null factors; Weather source OFFLINE when unknown |
| §33 timestamps | `observed_at`, `received_at`, `processed_at` |
| §34 reproducibility | `model_version` on every status, alert and summary |
| §35 observability | Pilot phase (logs only in MVP) |
| §26 Docker | **Deviation (team decision):** replaced by Vercel-only deployment |
| §46 Definition of Done | Section 1 and Section 7 checklist |
| New in v2.1 | AI Advisor (5.10), Handoff Pack (5.11), decision logging as the future training dataset |

---

## 10. VERIFICATION LOG

Tested in a sandbox on 18 Sept 2026 before sharing:

- **Contract:** all 15 mock files type-check **strictly** against the Section 2.4 types (literal objects assigned to typed constants, not casts). Scores of every mock status and alert equal the floor-rounded sum of their factors; levels and exposed values are consistent.
- **Engine:** scoring, synthetic generator, replay, alerts and summary implemented from this spec and run over 144 steps: 720 detections, 17 sites reach HIGH, 6 CRITICAL, 7 reached by fire, 0 missed, median lead 60 h, 43 escalation alerts, 41 de-escalations.
- **Backend mechanics:** a FastAPI prototype of login (PBKDF2 + PyJWT), bearer auth, roles, tenant isolation, CSV and GeoJSON import with per-row rejection, SOP matching, idempotent acknowledgement and audit passed its tests (FastAPI 0.141, Pydantic 2.13, PyJWT 2.7). `python-multipart` is required for uploads.
- **Frontend:** Vite 8 + React 19 + TypeScript + react-router-dom 6 + maplibre-gl 4 + recharts 2 install together, type-check and `npm run build` succeeds. Vite 8 needs Node 20.19+ or 22.12+.

- **v2.1 additions:** the database adapter passed identical tests on SQLite and PostgreSQL 16 (idempotent seed, rule upsert, first-ack-wins, audit autoincrement, tenant filter). Advisor validation and the tactics filter passed their tests; the `advisor.json` mock passes the same validator. All 18 mocks type-check strictly. Replay timing with the 5.9 optimization: 0.16 s (20 sites), 2.2 s (500 sites).
- **Vercel facts used (from Vercel docs, Sept 2026):** FastAPI is detected with zero configuration from `app/main.py` exposing `app`; Python 3.12 is the default; the function filesystem is read-only except a `/tmp` scratch space; `maxDuration` is set per entrypoint in `vercel.json`.

**Not testable in the sandbox, verify on first run:** NASA FIRMS API, Open-Meteo archive API, the Groq API and model availability, the actual Vercel deployments and Neon connection. Each has a fallback: synthetic detections, assumed weather flagged `assumed`, template advisor, SQLite in `/tmp` (flagged FALLBACK), and a mock-mode Console.
