// firesim.ts — "fire reported now" spread model for the simulator page.
// An elliptical fire shape (standard simplification): the head runs downwind at a rate set
// by fuel, wind, humidity and temperature; the flanks and back spread much slower. Good
// enough to train decisions on; not a validated fire-behaviour model.
import type { FuelClass, Level } from "../api/types";

export interface Conditions {
  wind_kmh: number; wind_from_deg: number; temp_c: number; rh_pct: number; fuel: FuelClass;
  ignition_km: number; ignition_bearing_deg: number;
}
export interface SiteLite { site_id: string; name: string; lat: number; lon: number; radius_m: number }
export interface FireState {
  minutes: number; level: Level; front_km: number; eta_min: number | null; head_ros_m_min: number;
  burned_ha: number; fire_moving_toward_site: boolean;
  perimeter: [number, number][]; front: [number, number][]; ignition: [number, number]; reached: boolean;
}

const FUEL_BASE: Record<FuelClass, number> = { low: 1.5, medium: 4, high: 7, very_high: 10 };   // m/min
export const FUEL_LABEL: Record<FuelClass, string> = { low: "Grass, short", medium: "Grass and shrubs", high: "Shrubland", very_high: "Pine forest, dry" };
const R = 6371008.8;
const rad = (d: number) => (d * Math.PI) / 180;

export function destination(lat: number, lon: number, bearing: number, m: number): [number, number] {
  const d = m / R, b = rad(bearing), p1 = rad(lat), l1 = rad(lon);
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b));
  const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [((l2 * 180) / Math.PI + 540) % 360 - 180, (p2 * 180) / Math.PI];
}
export function distM(a: [number, number], b: [number, number]) {
  const x = rad(b[0] - a[0]) * Math.cos(rad((a[1] + b[1]) / 2)), y = rad(b[1] - a[1]);
  return R * Math.hypot(x, y);
}
export function bearing(a: [number, number], b: [number, number]) {
  const p1 = rad(a[1]), p2 = rad(b[1]), dl = rad(b[0] - a[0]);
  const y = Math.sin(dl) * Math.cos(p2), x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}
const angdiff = (a: number, b: number) => Math.abs(((a - b + 540) % 360) - 180);

/** Head rate of spread in m/min. */
export function headROS(c: Conditions) {
  const windF = 1 + Math.pow(c.wind_kmh / 12, 1.25);
  const dryF = Math.min(1.6, Math.max(0.3, (1.15 - c.rh_pct / 100) * (0.65 + c.temp_c / 80)));
  return FUEL_BASE[c.fuel] * windF * dryF;
}

/** Random but plausible summer conditions in the region, with the fire 3.5–7 km away. */
export function randomConditions(rand = Math.random): Conditions {
  const fuels: FuelClass[] = ["medium", "high", "high", "very_high", "very_high"];
  const windFrom = [180, 202, 225, 247, 270, 292][Math.floor(rand() * 6)];
  return {
    wind_kmh: Math.round(8 + rand() * 37), wind_from_deg: windFrom,
    temp_c: Math.round(26 + rand() * 16), rh_pct: Math.round(10 + rand() * 35),
    fuel: fuels[Math.floor(rand() * fuels.length)],
    ignition_km: Math.round((3.5 + rand() * 3.5) * 10) / 10,
    // usually upwind of the site (the dangerous case), sometimes off to the side
    ignition_bearing_deg: Math.round((windFrom + (rand() - 0.5) * (rand() < 0.75 ? 60 : 160) + 360) % 360),
  };
}

/** The fire `minutes` after the report. `seed` keeps the ragged edge stable during one run. */
export function fireAt(site: SiteLite, c: Conditions, minutes: number, seed: number): FireState {
  const ign = destination(site.lat, site.lon, c.ignition_bearing_deg, c.ignition_km * 1000);
  const ros = headROS(c);
  const windTo = (c.wind_from_deg + 180) % 360;
  const lb = Math.min(5, 1 + 0.9 * Math.pow(c.wind_kmh / 10, 1.1));        // length-to-breadth
  const head = Math.max(25, ros * minutes);                                  // m
  const back = head * 0.08;
  const a = (head + back) / 2, b = Math.max(12, (head + back) / lb / 2);
  const centre = destination(ign[1], ign[0], windTo, (head - back) / 2);

  const perimeter: [number, number][] = [];
  const frontA: [number, number][] = [], frontB: [number, number][] = [];   // head, left and right of the wind axis
  const N = 96;
  for (let k = 0; k <= N; k++) {
    const th = (k / N) * Math.PI * 2;
    const rough = 1 + 0.06 * Math.sin(th * 5 + seed) + 0.04 * Math.sin(th * 11 + seed * 1.7) + 0.03 * Math.sin(th * 23 + seed * 2.3);
    const along = a * Math.cos(th) * rough, across = b * Math.sin(th) * rough;
    const dist = Math.hypot(along, across);
    const brg = (windTo + (Math.atan2(across, along) * 180) / Math.PI + 360) % 360;
    const pt = destination(centre[1], centre[0], brg, dist);
    perimeter.push(pt);
    if (Math.cos(th) > 0.35) (th < Math.PI ? frontA : frontB).push(pt);      // the downwind head
  }
  const frontLine = [...frontB, ...frontA];                                  // one continuous line

  const siteC: [number, number] = [site.lon, site.lat];
  let minD = Infinity;
  for (const p of perimeter) minD = Math.min(minD, distM(p, siteC));
  const inside = pointInPolygon(siteC, perimeter);
  const frontKm = inside ? 0 : Math.max(0, minD - site.radius_m) / 1000;
  const towardSite = angdiff(windTo, bearing(ign, siteC)) < 60;
  const pace = towardSite ? ros : ros / lb;                                  // flank spread is slower
  const eta = frontKm <= 0 ? 0 : Math.round((frontKm * 1000) / pace);
  const level: Level = frontKm < 1 ? "CRITICAL" : frontKm < 3 || (towardSite && frontKm < 5) ? "HIGH" : frontKm < 10 ? "ELEVATED" : "NORMAL";
  return {
    minutes, level, front_km: Math.round(frontKm * 100) / 100, eta_min: eta,
    head_ros_m_min: Math.round(ros * 10) / 10, burned_ha: Math.round((Math.PI * a * b) / 10000),
    fire_moving_toward_site: towardSite, perimeter, front: frontLine, ignition: ign, reached: frontKm <= 0,
  };
}

export function pointInPolygon(pt: [number, number], ring: [number, number][]) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/** Sensor reading from the fire: silent inside the burn, hot near the edge. */
export function sensorReading(pos: [number, number], st: FireState) {
  if (pointInPolygon(pos, st.perimeter)) return { state: "offline" as const, temp: null };
  let d = Infinity;
  for (const p of st.perimeter) d = Math.min(d, distM(pos, p));
  const t = Math.round((29 + 560 * Math.exp(-(d / 1000) / 0.28)) * 10) / 10;
  return { state: t >= 65 ? "fire" as const : t >= 45 ? "warm" as const : "ok" as const, temp: t };
}

/** Sim minutes per real second so the fire reaches the site in about 70 s at 1x. */
export function autoSpeed(site: SiteLite, c: Conditions) {
  const probe = fireAt(site, c, 0, 0);
  const minutes = probe.eta_min ?? 240;
  return Math.min(60, Math.max(1, minutes / 70));
}
