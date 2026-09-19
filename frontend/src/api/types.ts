// types.ts — Section 2.4 of docs/TEAM_PLAN.md, verbatim. Keep in sync with the backend.

export type Level = "NORMAL" | "ELEVATED" | "HIGH" | "CRITICAL";
export type SiteType = "solar_farm" | "wind_farm" | "substation" | "forest_block" | "telecom_tower" | "test_plot";
export type FuelClass = "low" | "medium" | "high" | "very_high";
export type RouteStatus = "available" | "potentially_exposed";
export type DataSource = "firms_sp" | "firms_nrt" | "synthetic_fallback";
export type FactorStatus = "observed" | "customer_provided" | "assumed" | "unknown";
export type SourceState = "ONLINE" | "FALLBACK" | "OFFLINE" | "NOT_CONFIGURED";
export type Role = "admin" | "operator" | "firefighter" | "government" | "ngo";
export const STAFF_ROLES: Role[] = ["admin", "operator"];

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

// ---- ground sensors (hexagonal mesh) ----
export type SensorState = "ok" | "warm" | "fire" | "offline" | "dropped";
export type SensorKind = "fence" | "structure" | "vegetation" | "grid";
export interface SensorNode {
  sensor_id: string; site_id: string; label: string; ring: number; lat: number; lon: number;
  kind: SensorKind; place: string; name: string; dist_m: number; bearing_deg: number; state: SensorState; temp_c: number | null; battery_pct: number;
  last_seen: string | null; state_since: string | null; note: string;
}
export interface SensorEvent {
  at: string; sensor_id: string; site_id: string; site_name: string; label: string; place: string;
  kind: "warm" | "fire" | "offline" | "dropped" | "recovered"; temp_c: number | null; detail: string;
}
export interface FireEstimate {
  lat: number; lon: number; radius_m: number; sensors: number; confidence: "low" | "medium" | "high";
  distance_m: number; bearing_deg: number; hottest: string;
}
export interface SensorMesh {
  site_id: string; site_name: string; lat: number; lon: number; installed_at: string;
  coverage_m: number; nodes: number; counts: Record<SensorState, number>; placement: Record<SensorKind, number>;
  layout_source: "openstreetmap" | "grid"; ground_fire: boolean; fire_estimate: FireEstimate | null;
}
export interface SensorsResponse { at: string; meshes: SensorMesh[]; nodes: SensorNode[]; events: SensorEvent[] }

// ---- partner sharing ----
export interface SharingPolicy {
  role: Role; label: string; asset_values: boolean; personnel: boolean; access_routes: boolean;
  criticality: boolean; handoff: boolean; company_ops: boolean;
}
export interface SituationSite {
  site_id: string; name: string; type: SiteType; lat: number; lon: number; radius_m: number;
  level: Level; score: number; nearest_fire_km: number | null; fire_bearing_deg: number | null;
  fire_moving_toward_site: boolean | null; criticality: number | null; personnel_on_site: number | null;
  access_routes: AccessRoute[] | null; value_eur: number | null; sensors_installed: boolean; ground_fire: boolean;
}
export interface Situation {
  at: string; viewer_role: Role; policy: SharingPolicy; matrix: SharingPolicy[];
  counts: Record<Level, number>; sites: SituationSite[];
}

// ---- training drills ----
export type DrillScenario = "approaching" | "sensor_first" | "false_alarm";
export interface StaffUser { email: string; name: string; role: Role }
export interface DrillStage {
  offset_s: number; kind: "satellite" | "satellite_clear" | "sensor_warm" | "sensor_fire" | "sensor_offline" | "sensor_dropped" | "sensor_normal";
  title: string; detail: string; level: Level; lat: number | null; lon: number | null; sensor_id: string | null; temp_c: number | null;
}
export interface DrillResponse {
  email: string; name: string; acked_at: string | null; responded_at: string | null; actions: string[]; note: string;
  ack_seconds: number | null; respond_seconds: number | null; correct: number; wrong: number; missed: number; score: number | null;
}
export interface DrillView {
  drill_id: string; site_id: string; site_name: string; lat: number; lon: number; radius_m: number;
  scenario: DrillScenario; scenario_title: string; briefing: string; pace_s: number;
  status: "running" | "ended"; created_by: string; created_at: string; ended_at: string | null; elapsed_s: number;
  level: Level; stages: DrillStage[]; total_stages: number; next_stage_in_s: number | null;
  participants: string[]; participant_names: Record<string, string>; options: string[]; expected_actions: string[] | null;
  my_response: DrillResponse | null; responses: DrillResponse[];
  notifications: { to: string; channel: "in_app" | "email"; subject: string }[];
  nodes: SensorNode[]; fire_estimate: FireEstimate | null; disclaimer: string;
}
