// sim.ts — the landing page's "drag the fire" illustration. Same ideas as the Engine
// (sensor states, heat-weighted fire position, protocol by level), on a toy map.
import type { Level, SensorKind, SensorState } from "../api/types";

export const W = 800;
export const H = 480;
export const M_PER_PX = 12;                  // 1 px = 12 m on the toy map
export const SITE = { x: 520, y: 215, r: 62 };
export const WIND_FROM_DEG = 225;            // blowing from the south-west

export interface ToySensor { id: string; kind: SensorKind; place: string; x: number; y: number }
export interface Reading extends ToySensor { state: SensorState; temp: number | null }

const fence: ToySensor[] = Array.from({ length: 6 }, (_, i) => {
  const a = (i * 60 * Math.PI) / 180;
  return { id: `F${i}`, kind: "fence", place: "Site fence", x: SITE.x + (SITE.r + 8) * Math.sin(a), y: SITE.y - (SITE.r + 8) * Math.cos(a) };
});

export const SENSORS: ToySensor[] = [
  ...fence,
  { id: "H1", kind: "structure", place: "Farmhouse", x: 395, y: 300 },
  { id: "H2", kind: "structure", place: "Cabin", x: 330, y: 205 },
  { id: "H3", kind: "structure", place: "House", x: 640, y: 330 },
  { id: "V1", kind: "vegetation", place: "Forest edge", x: 300, y: 320 },
  { id: "V2", kind: "vegetation", place: "Forest edge", x: 255, y: 262 },
  { id: "V3", kind: "vegetation", place: "Forest edge", x: 350, y: 372 },
  { id: "V4", kind: "vegetation", place: "Scrubland", x: 445, y: 385 },
  { id: "V5", kind: "vegetation", place: "Forest edge", x: 660, y: 120 },
  { id: "G1", kind: "grid", place: "Open ground", x: 520, y: 330 },
  { id: "G2", kind: "grid", place: "Open ground", x: 420, y: 140 },
  { id: "G3", kind: "grid", place: "Open ground", x: 640, y: 225 },
];

export const FIRE_START = { x: 95, y: 440 };   // upwind, south-west of the site
export const AMBIENT = 29;

/** Heat a sensor feels from the fire front, in °C above ambient. */
function heat(sx: number, sy: number, fx: number, fy: number) {
  const km = (Math.hypot(sx - fx, sy - fy) * M_PER_PX) / 1000;
  return 560 * Math.exp(-km / 0.28);
}

/** Readings for a fire at (fx, fy); `burned` keeps sensors that melted offline. */
export function readings(fx: number, fy: number, burned: Set<string>): Reading[] {
  return SENSORS.map((s) => {
    if (burned.has(s.id)) return { ...s, state: "offline", temp: null };
    const t = Math.round((AMBIENT + heat(s.x, s.y, fx, fy)) * 10) / 10;
    const state: SensorState = t >= 65 ? "fire" : t >= 45 ? "warm" : "ok";
    return { ...s, state, temp: t };
  });
}
export const DESTROY_C = 150;

export interface Estimate { x: number; y: number; r: number; n: number }

/** Heat-weighted centroid of the warm and fire sensors (the Engine's method). */
export function estimate(rs: Reading[]): Estimate | null {
  const hot = rs.filter((r) => (r.state === "warm" || r.state === "fire") && r.temp !== null);
  if (!hot.length) return null;
  const temps = rs.filter((r) => r.temp !== null).map((r) => r.temp!).sort((a, b) => a - b);
  const base = temps[Math.floor(temps.length / 2)];
  const w = hot.map((r) => Math.max(1, r.temp! - base) ** 2);
  const tw = w.reduce((a, b) => a + b, 0);
  const x = hot.reduce((a, r, i) => a + r.x * w[i], 0) / tw;
  const y = hot.reduce((a, r, i) => a + r.y * w[i], 0) / tw;
  const spread = Math.sqrt(hot.reduce((a, r, i) => a + w[i] * ((r.x - x) ** 2 + (r.y - y) ** 2), 0) / tw);
  return { x, y, r: hot.length > 1 ? Math.max(12, spread + 10) : 25, n: hot.length };
}

/** Distance from the fire to the site edge, in km. */
export function distanceKm(fx: number, fy: number) {
  return Math.max(0, Math.hypot(fx - SITE.x, fy - SITE.y) - SITE.r) * M_PER_PX / 1000;
}

/** Illustrative level: proximity plus whether the wind carries the fire toward the site. */
export function level(fx: number, fy: number): Level {
  const km = distanceKm(fx, fy);
  const bearingToSite = (Math.atan2(SITE.x - fx, fy - SITE.y) * 180) / Math.PI;
  const windTo = (WIND_FROM_DEG + 180) % 360;
  const toward = Math.cos(((bearingToSite - windTo) * Math.PI) / 180) > 0.5;
  const pts = 35 * Math.max(0, 1 - km / 6) + (toward ? 25 : 5) + 22;
  return pts > 75 ? "CRITICAL" : pts > 50 ? "HIGH" : pts > 25 ? "ELEVATED" : "NORMAL";
}

export const ACTIONS: Record<Level, string[]> = {
  NORMAL: [],
  ELEVATED: ["Watch the next satellite pass"],
  HIGH: ["Notify the regional control centre", "Confirm the headcount with the site manager",
    "Check the secondary access route"],
  CRITICAL: ["Move people to the safest exit route", "Share the fire position with the fire service",
    "Prepare a controlled shutdown if authorised"],
};
