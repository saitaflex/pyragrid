// engine.ts — client-side mock replay so the demo is fully interactive on mocks.
// Mirrors the backend contract shapes (§2.4) and the rules-1.0 spirit; numbers are
// illustrative (mock mode), not engine outputs.
import type {
  Alert, Component, Detection, Factors, FactorStatuses, Incident, Level, Portfolio,
  ReplaySummary, Site, SiteStatus, SiteType, TimelinePoint,
} from "./types";
import { compass, levelForScore } from "./levels";

const R = 6371.0088;
const rad = (d: number) => (d * Math.PI) / 180;
const deg = (r: number) => (r * 180) / Math.PI;

function haversine(aLat: number, aLon: number, bLat: number, bLon: number) {
  const dLat = rad(bLat - aLat), dLon = rad(bLon - aLon);
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(rad(aLat)) * Math.cos(rad(bLat)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
}
function bearing(aLat: number, aLon: number, bLat: number, bLon: number) {
  const dl = rad(bLon - aLon);
  const y = Math.sin(dl) * Math.cos(rad(bLat));
  const x = Math.cos(rad(aLat)) * Math.sin(rad(bLat)) - Math.sin(rad(aLat)) * Math.cos(rad(bLat)) * Math.cos(dl);
  return (deg(Math.atan2(y, x)) + 360) % 360;
}
function destination(lat: number, lon: number, brg: number, km: number): [number, number] {
  const d = km / R, b = rad(brg), p1 = rad(lat), l1 = rad(lon);
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b));
  const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [deg(p2), ((deg(l2) + 540) % 360) - 180];
}
const angdiff = (a: number, b: number) => Math.abs(((a - b + 180) % 360) - 180);
const clamp = (x: number) => Math.max(0, Math.min(1, x));

const VULN: Record<SiteType, number> = { solar_farm: 0.8, wind_farm: 0.6, substation: 0.9, forest_block: 1.0, telecom_tower: 0.7, test_plot: 0.5 };
const FUEL: Record<string, number> = { low: 0.2, medium: 0.5, high: 0.8, very_high: 1.0 };
const SHARES: Record<SiteType, [string, number][]> = {
  solar_farm: [["PV array", 0.7], ["Inverter station", 0.15], ["Substation", 0.1], ["Control building", 0.05]],
  wind_farm: [["Turbines", 0.8], ["Substation", 0.15], ["Control building", 0.05]],
  substation: [["Transformers", 0.6], ["Switchgear", 0.3], ["Control building", 0.1]],
  forest_block: [["Standing timber", 0.9], ["Forest roads", 0.1]],
  telecom_tower: [["Tower and antennas", 0.7], ["Power and backup", 0.3]],
  test_plot: [["Weather station", 0.6], ["Camera", 0.4]],
};

function components(value: number, type: SiteType): Component[] {
  const shares = SHARES[type];
  const vals = shares.map(([, s]) => Math.round(value * s));
  vals[0] += value - vals.reduce((a, b) => a + b, 0);
  return shares.map(([name], i) => ({ name, value_eur: vals[i] }));
}

type Seed = [string, string, SiteType, number, number, number, number, string, number, number, number];
const SEED: Seed[] = [
  ["ES-OU-001", "Solar Trives 01", "solar_farm", 42.33, -7.23, 600, 12400000, "high", 7, 200, 4],
  ["ES-OU-002", "Solar Manzaneda 02", "solar_farm", 42.3, -7.26, 500, 8700000, "high", 4, 90, 4],
  ["ES-OU-003", "Wind Cabeza de Manzaneda", "wind_farm", 42.265, -7.29, 1500, 21000000, "very_high", 3, 0, 4],
  ["ES-OU-004", "Substation Chandrexa 14", "substation", 42.27, -7.34, 150, 8000000, "medium", 2, 180, 5],
  ["ES-OU-005", "Forest Block Queixa A", "forest_block", 42.23, -7.4, 2000, 4200000, "very_high", 5, 270, 3],
  ["ES-OU-006", "Wind Vilariño 01", "wind_farm", 42.17, -7.26, 1500, 18500000, "high", 2, 45, 4],
  ["ES-OU-007", "Telecom Tower Conso", "telecom_tower", 42.16, -7.3, 50, 350000, "high", 0, 120, 3],
  ["ES-OU-008", "Substation Larouco 47", "substation", 42.36, -7.14, 150, 9500000, "medium", 3, 225, 5],
  ["ES-OU-009", "Solar Larouco 03", "solar_farm", 42.33, -7.18, 700, 14000000, "high", 6, 300, 4],
  ["ES-OU-010", "Forest Block Seadur B", "forest_block", 42.38, -7.1, 2500, 5600000, "very_high", 4, 180, 3],
  ["ES-OU-011", "Telecom Tower Pena Trevinca", "telecom_tower", 42.25, -6.85, 50, 420000, "very_high", 0, 90, 3],
  ["ES-OU-012", "Solar A Rua 01", "solar_farm", 42.4, -7.11, 600, 10800000, "medium", 5, 0, 4],
  ["ES-OU-013", "Substation O Barco 09", "substation", 42.415, -6.985, 150, 7200000, "low", 3, 270, 5],
  ["ES-OU-014", "Wind Serra do Eixe", "wind_farm", 42.3, -6.95, 1500, 16000000, "high", 2, 315, 4],
  ["ES-OU-015", "Forest Block Viana C", "forest_block", 42.18, -7.11, 2000, 3900000, "high", 3, 0, 3],
  ["ES-OU-016", "Solar Castro Caldelas 01", "solar_farm", 42.375, -7.415, 500, 7900000, "medium", 4, 135, 4],
  ["ES-OU-017", "Substation Montederramo 05", "substation", 42.28, -7.5, 150, 6100000, "medium", 2, 90, 5],
  ["ES-OU-018", "Solar Xinzo 02", "solar_farm", 42.06, -7.72, 800, 15300000, "low", 8, 45, 4],
  ["ES-OU-019", "Forest Block Oimbra D", "forest_block", 41.9, -7.47, 2000, 3300000, "high", 4, 180, 3],
  ["ES-OU-020", "San Xoan de Rio Test Plot", "test_plot", 42.366, -7.286, 80, 25000, "medium", 1, 90, 1],
];

export const SITES: Site[] = SEED.map((s) => ({
  site_id: s[0], name: s[1], type: s[2], lat: s[3], lon: s[4], radius_m: s[5],
  value_eur: s[6], fuel_class: s[7] as Site["fuel_class"], personnel_on_site: s[8],
  primary_access_bearing_deg: s[9], criticality: s[10], components: components(s[6], s[2]),
}));
const SITE_MAP = new Map(SITES.map((s) => [s.site_id, s]));

export const START = Date.UTC(2025, 7, 8, 0, 0, 0);
export const STEP_MS = 3 * 3600 * 1000;
export const STEPS = 144;
export const stepIso = (i: number) => new Date(START + i * STEP_MS).toISOString().replace(".000Z", "Z");
export const isoToStep = (iso: string) => Math.max(0, Math.min(STEPS - 1, Math.round((Date.parse(iso) - START) / STEP_MS)));
const compactTs = (iso: string) => iso.slice(0, 16).replace(/[-:]/g, "").replace("T", "T");

const FIRES = [
  { lat: 42.245, lon: -7.36, ignite: Date.UTC(2025, 7, 8, 13), speed: 0.25, maxR: 20, stop: Date.UTC(2025, 7, 20, 13) },
  { lat: 42.34, lon: -7.16, ignite: Date.UTC(2025, 7, 13, 13), speed: 0.3, maxR: 25, stop: Date.UTC(2025, 7, 24, 13) },
];
const WIND_FROM = 225; // wind comes from SW → blows toward NE (45)
const WIND_TO = (WIND_FROM + 180) % 360;
const WIND_SPEED = 20;

function activeFires(t: number) {
  return FIRES.filter((f) => t >= f.ignite && t <= f.stop).map((f) => ({
    ...f, radius: Math.min(f.maxR, (f.speed * (t - f.ignite)) / 3600000),
  }));
}
const seededJitter = (id: string) => (([...id].reduce((a, c) => a + c.charCodeAt(0), 0) % 7) - 3) * 0.4;

export function statusAt(siteId: string, stepIdx: number): { status: SiteStatus; headline: string } {
  const site = SITE_MAP.get(siteId)!;
  const t = START + stepIdx * STEP_MS;
  const fires = activeFires(t);

  let best: { dist: number; brg: number; frontLat: number; frontLon: number } | null = null;
  for (const f of fires) {
    const centre = haversine(site.lat, site.lon, f.lat, f.lon);
    const edge = Math.max(0, centre - f.radius - site.radius_m / 1000);
    if (edge <= 25 && (!best || edge < best.dist)) {
      const brg = bearing(site.lat, site.lon, f.lat, f.lon);
      const [fl, fo] = destination(site.lat, site.lon, brg, edge + site.radius_m / 1000);
      best = { dist: edge, brg, frontLat: fl, frontLon: fo };
    }
  }

  const weatherPts = 15 * ((clamp((32 - 20) / 20) + clamp((60 - 22) / 50) + clamp(WIND_SPEED / 40)) / 3);
  const fuelPts = 15 * FUEL[site.fuel_class];
  const vulnPts = 10 * VULN[site.type];
  let prox = 0, wind = 0, movingToward: boolean | null = null, relation = "unknown";
  let nearest: number | null = null, fireBrg: number | null = null, trig: string | null = null;

  if (best) {
    const dist = Math.max(0, best.dist + seededJitter(siteId) * 0.15);
    prox = 35 * clamp(1 - dist / 25);
    const originToSite = bearing(best.frontLat, best.frontLon, site.lat, site.lon);
    const align = Math.max(0, Math.cos(rad(angdiff(WIND_TO, originToSite))));
    wind = 25 * align * Math.min(1, WIND_SPEED / 30);
    const cosv = Math.cos(rad(angdiff(WIND_TO, originToSite)));
    movingToward = cosv > 0.5;
    relation = cosv > 0.5 ? "toward site" : cosv < -0.5 ? "away from site" : "crosswind";
    nearest = Math.round(dist * 10) / 10;
    fireBrg = Math.round(best.brg) % 360;
    trig = `d-${String(stepIdx * 3 + (siteId.charCodeAt(6) % 3) + 1).padStart(4, "0")}`;
  }

  const r1 = (x: number) => Math.round(x * 10) / 10;
  const factors: Factors = { proximity: r1(prox), wind_alignment: r1(wind), weather: r1(weatherPts), fuel: r1(fuelPts), vulnerability: r1(vulnPts) };
  const total = (factors.proximity ?? 0) + (factors.wind_alignment ?? 0) + (factors.weather ?? 0) + (factors.fuel ?? 0) + (factors.vulnerability ?? 0);
  const score = Math.min(100, Math.floor(total + 0.5));
  const level = levelForScore(score);
  const factor_status: FactorStatuses = { proximity: "observed", wind_alignment: "observed", weather: "observed", fuel: "customer_provided", vulnerability: "customer_provided" };

  const primary = site.primary_access_bearing_deg;
  const secondary = (primary + 180) % 360;
  const routeStatus = (b: number): "available" | "potentially_exposed" =>
    nearest !== null && nearest <= 10 && fireBrg !== null && angdiff(b, fireBrg) <= 45 ? "potentially_exposed" : "available";

  const headline = nearest !== null
    ? `Fire ${nearest.toFixed(1)} km ${compass(fireBrg!)}, wind ${relation}`
    : "No fire within 25 km";

  const status: SiteStatus = {
    site_id: site.site_id, name: site.name, type: site.type, lat: site.lat, lon: site.lon,
    radius_m: site.radius_m, value_eur: site.value_eur, personnel_on_site: site.personnel_on_site,
    criticality: site.criticality, score, level, model_version: "rules-1.0", factors, factor_status,
    nearest_fire_km: nearest, fire_bearing_deg: fireBrg, fire_moving_toward_site: movingToward,
    triggering_detection_id: trig,
    wind: { speed_kmh: WIND_SPEED, from_deg: WIND_FROM, to_deg: WIND_TO },
    weather: { temp_c: 32, rh_pct: 22 },
    access_routes: [
      { name: "Primary access", bearing_deg: primary, status: routeStatus(primary) },
      { name: "Secondary access", bearing_deg: secondary, status: routeStatus(secondary) },
    ],
    exposed_components: level === "HIGH" || level === "CRITICAL" ? site.components : [],
    sop_actions: [],
  };
  return { status, headline };
}

// ---- SOP (mirrors the 4 default rules) ----
import type { SopRule } from "./types";
export const DEFAULT_RULES: SopRule[] = [
  { rule_id: "R-001", name: "High exposure: Level 2", enabled: true, priority: 10, conditions: { min_level: "HIGH", asset_types: [], min_criticality: 1, wind_toward_site: null }, actions: ["Notify regional control centre", "Contact site manager and confirm personnel count", "Verify secondary access route is available", "Increase monitoring to every satellite pass"] },
  { rule_id: "R-002", name: "Critical exposure: Level 3", enabled: true, priority: 20, conditions: { min_level: "CRITICAL", asset_types: [], min_criticality: 1, wind_toward_site: null }, actions: ["Notify regional control centre immediately", "Contact site manager and confirm personnel location", "Move personnel to the safest available exit route", "Prepare controlled shutdown if authorised", "Notify emergency services according to company procedure"] },
  { rule_id: "R-003", name: "Substation control room", enabled: true, priority: 30, conditions: { min_level: "HIGH", asset_types: ["substation"], min_criticality: 1, wind_toward_site: null }, actions: ["Notify control room of substation exposure"] },
  { rule_id: "R-004", name: "Critical with wind toward site", enabled: true, priority: 40, conditions: { min_level: "CRITICAL", asset_types: [], min_criticality: 1, wind_toward_site: true }, actions: ["Escalate to emergency protocol"] },
];
const RANK: Record<Level, number> = { NORMAL: 0, ELEVATED: 1, HIGH: 2, CRITICAL: 3 };

export function matchActions(rules: SopRule[], st: SiteStatus): { actions: string[]; rule_ids: string[] } {
  const matched = rules.filter((r) => r.enabled
    && RANK[st.level] >= RANK[r.conditions.min_level]
    && (r.conditions.asset_types.length === 0 || r.conditions.asset_types.includes(st.type))
    && st.criticality >= r.conditions.min_criticality
    && (r.conditions.wind_toward_site === null || r.conditions.wind_toward_site === st.fire_moving_toward_site))
    .sort((a, b) => a.priority - b.priority || a.rule_id.localeCompare(b.rule_id));
  const actions: string[] = [];
  for (const r of matched) for (const a of r.actions) if (!actions.includes(a)) actions.push(a);
  return { actions, rule_ids: matched.map((r) => r.rule_id) };
}

export function portfolioAt(stepIdx: number, rules: SopRule[]): Portfolio {
  const sites = SITES.map((s) => {
    const { status } = statusAt(s.site_id, stepIdx);
    status.sop_actions = matchActions(rules, status).actions;
    return status;
  }).sort((a, b) => RANK[b.level] - RANK[a.level] || b.score - a.score || a.site_id.localeCompare(b.site_id));
  return {
    at: stepIso(stepIdx),
    counts: {
      NORMAL: sites.filter((s) => s.level === "NORMAL").length,
      ELEVATED: sites.filter((s) => s.level === "ELEVATED").length,
      HIGH: sites.filter((s) => s.level === "HIGH").length,
      CRITICAL: sites.filter((s) => s.level === "CRITICAL").length,
    },
    total_exposed_value_eur: sites.filter((s) => s.level === "HIGH" || s.level === "CRITICAL").reduce((a, s) => a + s.value_eur, 0),
    sites,
  };
}

export function timelineFor(siteId: string): TimelinePoint[] {
  return Array.from({ length: STEPS }, (_, i) => {
    const { status } = statusAt(siteId, i);
    return { at: stepIso(i), score: status.score, level: status.level, nearest_fire_km: status.nearest_fire_km };
  });
}

function allAlerts(rules: SopRule[]): Alert[] {
  const out: Alert[] = [];
  for (const site of SITES) {
    let prev: Level = "NORMAL";
    for (let i = 0; i < STEPS; i++) {
      const { status, headline } = statusAt(site.site_id, i);
      if (status.level !== prev && (RANK[status.level] >= 2 || RANK[prev] >= 2)) {
        const at = stepIso(i);
        const { actions, rule_ids } = matchActions(rules, status);
        out.push({
          alert_id: `${site.site_id}_${compactTs(at)}_${status.level}`, site_id: site.site_id,
          site_name: site.name, at, kind: RANK[status.level] > RANK[prev] ? "escalation" : "de-escalation",
          from_level: prev, to_level: status.level, score: status.score, headline,
          triggering_detection_id: status.triggering_detection_id, factors: status.factors,
          factor_status: status.factor_status, model_version: "rules-1.0", processed_at: at,
          actions, rule_ids, acknowledged: false, acknowledged_by: null, acknowledged_at: null,
        });
      }
      prev = status.level;
    }
  }
  return out;
}

export function alertsUpTo(stepIdx: number, rules: SopRule[]): Alert[] {
  const at = stepIso(stepIdx);
  return allAlerts(rules).filter((a) => a.at <= at).sort((a, b) => (a.at < b.at ? 1 : -1));
}

function episodes() {
  const eps: { site_id: string; i: number; j: number }[] = [];
  for (const site of SITES) {
    const levels = Array.from({ length: STEPS }, (_, i) => statusAt(site.site_id, i).status.level);
    let i = 0;
    while (i < STEPS) {
      if (RANK[levels[i]] >= 2) {
        let j = i;
        while (j < STEPS && RANK[levels[j]] >= 2) j++;
        eps.push({ site_id: site.site_id, i, j });
        i = j;
      } else i++;
    }
  }
  return eps;
}

function buildIncident(ep: { site_id: string; i: number; j: number }, rules: SopRule[], atStep: number | null): Incident {
  const openedIso = stepIso(ep.i);
  const k = atStep !== null && atStep >= ep.i && atStep < ep.j ? atStep : ep.j - 1;
  const { status, headline } = statusAt(ep.site_id, k);
  const { actions, rule_ids } = matchActions(rules, status);
  return {
    incident_id: `${ep.site_id}_${compactTs(openedIso)}`, site_id: ep.site_id, site_name: status.name,
    level: status.level as "HIGH" | "CRITICAL", score: status.score, opened_at: openedIso,
    closed_at: ep.j < STEPS ? stepIso(ep.j) : null, headline, actions, rule_ids,
    disclaimer: "Recommended actions from the customer's approved protocol (simulated for demo). Not an autonomous safety decision.",
  };
}

export function incidentsOpenAt(stepIdx: number, rules: SopRule[]): Incident[] {
  const at = stepIso(stepIdx);
  return episodes().filter((ep) => stepIso(ep.i) <= at && (ep.j >= STEPS || at < stepIso(ep.j)))
    .map((ep) => buildIncident(ep, rules, stepIdx))
    .sort((a, b) => (a.level === b.level ? b.score - a.score : a.level === "CRITICAL" ? -1 : 1));
}

export function incidentsHistory(rules: SopRule[]): Incident[] {
  return episodes().map((ep) => buildIncident(ep, rules, null)).sort((a, b) => (a.opened_at < b.opened_at ? -1 : 1));
}

export function incidentById(id: string, rules: SopRule[], stepIdx: number): Incident | null {
  const ep = episodes().find((e) => `${e.site_id}_${compactTs(stepIso(e.i))}` === id);
  return ep ? buildIncident(ep, rules, stepIdx) : null;
}

export function detectionsAt(stepIdx: number, windowH = 12): Detection[] {
  const t = START + stepIdx * STEP_MS;
  const out: Detection[] = [];
  let n = 1;
  for (const f of activeFires(t)) {
    for (let k = 0; k < 14; k++) {
      const ang = f === FIRES[0] ? 45 : 300;
      const jitterAng = ang + ((k * 37) % 120) - 60;
      const dist = Math.max(0.3, f.radius + (((k * 53) % 20) / 10 - 1));
      const [lat, lon] = destination(f.lat, f.lon, jitterAng, dist);
      out.push({
        id: `d-${String(stepIdx * 30 + n).padStart(4, "0")}`, source: "synthetic_fallback",
        external_id: null, lat: Math.round(lat * 1e5) / 1e5, lon: Math.round(lon * 1e5) / 1e5,
        observed_at: stepIso(Math.max(0, stepIdx - (k % 4))), received_at: stepIso(stepIdx),
        satellite: "N20", confidence: k % 3 === 0 ? "h" : "n", intensity_frp: Math.round((10 + (k * 47) % 70) * 10) / 10,
      });
      n++;
    }
  }
  void windowH;
  return out;
}

export function summary(rules: SopRule[]): ReplaySummary {
  const alerts = allAlerts(rules);
  const eps = episodes();
  let high = 0, crit = 0;
  for (const s of SITES) {
    const levels = Array.from({ length: STEPS }, (_, i) => statusAt(s.site_id, i).status.level);
    if (levels.some((l) => RANK[l] >= 2)) high++;
    if (levels.some((l) => l === "CRITICAL")) crit++;
  }
  return {
    start: stepIso(0), end: new Date(START + STEPS * STEP_MS).toISOString().replace(".000Z", "Z"),
    step_hours: 3, data_source: "synthetic_fallback", model_version: "rules-1.0",
    total_detections: 718, detections_used: 718,
    alerts_raised: alerts.filter((a) => a.kind === "escalation").length, incidents: eps.length,
    sites_ever_high: high, sites_ever_critical: crit, sites_reached_by_fire: 7,
    missed_exposures: 0, median_lead_time_hours: 60.0, explanation_coverage_pct: 100.0,
  };
}

export function siteById(id: string) { return SITE_MAP.get(id) ?? null; }

// ---- Handoff Pack (§5.11) ----
import type { AdvisorResponse, AdvisorSuggestion, HandoffPack, Hazard } from "./types";

const HAZARDS: Record<SiteType, [string, Hazard["kind"], string][]> = {
  solar_farm: [["PV modules", "electrical", "PV modules produce DC voltage whenever they are exposed to light and cannot be fully de-energised in daylight."], ["Inverter station", "electrical", "High-voltage equipment."]],
  substation: [["Transformers", "electrical", "High-voltage equipment."], ["Transformer insulating oil", "fuel_oil", "Oil-filled transformers contain flammable insulating oil."]],
  wind_farm: [["Turbines", "height", "Falling debris possible if a nacelle burns; keep clear of the tower base."], ["Substation", "electrical", "High-voltage equipment."]],
  telecom_tower: [["Backup batteries", "battery", "Backup batteries and electrical equipment."], ["Tower", "height", "Height hazard."]],
  forest_block: [["No built hazards", "none", "Standing timber; limited road access."]],
  test_plot: [["Weather station and camera", "electrical", "Low-voltage equipment only."]],
};

export function buildHandoff(siteId: string, stepIdx: number): HandoffPack {
  const site = SITE_MAP.get(siteId)!;
  const { status, headline } = statusAt(siteId, stepIdx);
  const primary = site.primary_access_bearing_deg;
  const distKm = site.radius_m / 1000 + 0.3;
  const [aLat, aLon] = destination(site.lat, site.lon, (primary + 90) % 360, distKm);
  const [bLat, bLon] = destination(site.lat, site.lon, (primary + 270) % 360, distKm);
  const digits = siteId.replace(/\D/g, "");
  return {
    site_id: siteId, site_name: site.name, type: site.type, at: stepIso(stepIdx),
    generated_at: new Date().toISOString().replace(/\.\d+Z$/, "Z"), lat: site.lat, lon: site.lon,
    level: status.level, score: status.score, headline, personnel_on_site: site.personnel_on_site,
    criticality: site.criticality, access_routes: status.access_routes,
    hazards: HAZARDS[site.type].map(([name, kind, note]) => ({ name, kind, note })),
    water_points: [
      { name: "Water tank A", lat: Math.round(aLat * 1e5) / 1e5, lon: Math.round(aLon * 1e5) / 1e5, capacity_m3: 50 },
      { name: "Water tank B", lat: Math.round(bLat * 1e5) / 1e5, lon: Math.round(bLon * 1e5) / 1e5, capacity_m3: 30 },
    ],
    contact: { role: "Site manager (simulated)", phone: "+34 600 000 " + (digits.length >= 3 ? digits.slice(-3) : "000") },
    simulated: true,
    disclaimer: "Information for the fire service from the site operator (simulated demo data). The fire service decides all firefighting actions.",
  };
}

// ---- AI Advisor template engine (§5.10) ----
const ADVISOR_DISCLAIMER = "AI-generated suggestions for the company's own operations, grounded in the data shown. Not firefighting instructions. A human must approve every suggestion. Always follow the fire service's orders.";

export function evidenceKeys(st: SiteStatus, ruleIds: string[]): string[] {
  const keys = ["proximity", "wind_alignment", "weather", "fuel", "vulnerability"].map((n) => `factor:${n}`);
  st.access_routes.forEach((r) => keys.push(`route:${r.name}`));
  ruleIds.forEach((r) => keys.push(`rule:${r}`));
  keys.push("asset:personnel_on_site", "asset:type", "asset:criticality", "asset:value_eur");
  st.exposed_components.forEach((c) => keys.push(`component:${c.name}`));
  if (st.wind) keys.push("weather:wind");
  if (st.triggering_detection_id) keys.push(`detection:${st.triggering_detection_id}`);
  return [...new Set(keys)].sort();
}

export function generateAdvice(incidentId: string, siteId: string, stepIdx: number, rules: SopRule[]): AdvisorResponse {
  const { status } = statusAt(siteId, stepIdx);
  const { rule_ids } = matchActions(rules, status);
  const keys = evidenceKeys(status, rule_ids);
  const routes = Object.fromEntries(status.access_routes.map((r) => [r.name, r.status]));
  const exposed = status.access_routes.filter((r) => r.status === "potentially_exposed").map((r) => r.name);
  const available = status.access_routes.filter((r) => r.status === "available").map((r) => r.name);
  const isHigh = status.level === "HIGH" || status.level === "CRITICAL";
  const ruleKeys = rule_ids.map((r) => `rule:${r}`);
  const raw: Omit<AdvisorSuggestion, "suggestion_id" | "decision" | "decided_by" | "decided_at">[] = [];

  if (status.personnel_on_site > 0 && isHigh)
    raw.push({ title: `Confirm headcount of the ${status.personnel_on_site} people on site`, detail: `${status.personnel_on_site} people are recorded on site at level ${status.level}. Confirm every person's location with the site manager.`, audience: "site_team", priority: 1, evidence: ["asset:personnel_on_site"] });
  if (exposed.length && available.length)
    raw.push({ title: `Use ${available[0]} for any movement`, detail: `${exposed[0]} is potentially exposed; ${available[0]} is available.`, audience: "site_team", priority: 1, evidence: [`route:${exposed[0]}`, `route:${available[0]}`] });
  else if (exposed.length === 2)
    raw.push({ title: "Both access routes may be exposed: keep people away from the perimeter and ask the fire service liaison for guidance", detail: "Both Primary and Secondary access are potentially exposed.", audience: "site_team", priority: 1, evidence: Object.keys(routes).map((n) => `route:${n}`) });
  if (status.fire_moving_toward_site === true && ruleKeys.length)
    raw.push({ title: "Wind is carrying the fire toward the site: prepare the protocol actions now", detail: "The wind is carrying the fire toward the site. Prepare the protocol actions from the matching rules.", audience: "operator", priority: 1, evidence: ["weather:wind", ...ruleKeys] });
  if (status.level === "CRITICAL" && ["solar_farm", "substation", "wind_farm", "telecom_tower"].includes(status.type))
    raw.push({ title: "Send the handoff pack to the fire service liaison", detail: `This ${status.type.replace("_", " ")} is at CRITICAL. Share the handoff pack (hazards, water points, access) with the fire service liaison.`, audience: "fire_service_liaison", priority: 2, evidence: ["asset:type"] });
  if (isHigh && ruleKeys.length)
    raw.push({ title: "Review the protocol actions and record which were taken", detail: "Review the matching protocol actions and record which were taken.", audience: "operator", priority: 3, evidence: ruleKeys });

  const suggestions: AdvisorSuggestion[] = raw.slice(0, 6).map((s, i) => ({
    ...s, suggestion_id: `sug_${(Date.now().toString(16) + i).slice(-8)}`, decision: null, decided_by: null, decided_at: null,
  }));
  return {
    incident_id: incidentId, at: stepIso(stepIdx), generated_by: "template", model: null,
    created_at: new Date().toISOString().replace(/\.\d+Z$/, "Z"), evidence_keys: keys, suggestions,
    rejected_by_guardrails: 0, fallback_reason: "no LLM configured", disclaimer: ADVISOR_DISCLAIMER,
  };
}
