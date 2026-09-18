// levels.ts — §2.3 level colours and rank.
import type { Level } from "./types";

export const LEVEL_COLOR: Record<Level, string> = {
  NORMAL: "#2E7D32",
  ELEVATED: "#F9A825",
  HIGH: "#EF6C00",
  CRITICAL: "#FF3B30", // hot variant of #C62828 for the dark theme
};

export const LEVEL_RANK: Record<Level, number> = {
  NORMAL: 0, ELEVATED: 1, HIGH: 2, CRITICAL: 3,
};

export const LEVELS: Level[] = ["NORMAL", "ELEVATED", "HIGH", "CRITICAL"];

export function levelForScore(score: number): Level {
  if (score <= 25) return "NORMAL";
  if (score <= 50) return "ELEVATED";
  if (score <= 75) return "HIGH";
  return "CRITICAL";
}

export function eur(n: number): string {
  if (n >= 1_000_000) return `€${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `€${(n / 1_000).toFixed(0)}k`;
  return `€${n}`;
}

const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
export function compass(deg: number): string {
  return COMPASS[Math.floor(((deg + 22.5) % 360) / 45) % 8];
}

export function fmtTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", timeZone: "UTC",
  }).replace(",", "") + " UTC";
}

export const SITE_TYPE_LABEL: Record<string, string> = {
  solar_farm: "Solar farm", wind_farm: "Wind farm", substation: "Substation",
  forest_block: "Forest block", telecom_tower: "Telecom tower", test_plot: "Test plot",
};

// Ground-sensor states (hex mesh). Distinct from risk levels on purpose: grey = silent, cyan = moved.
export const SENSOR_COLOR: Record<string, string> = {
  ok: "#3FA34D", warm: "#F9A825", fire: "#FF3B30", offline: "#6F6B78", dropped: "#4FC3F7",
};
export const SENSOR_LABEL: Record<string, string> = {
  ok: "OK", warm: "Warm", fire: "Fire", offline: "Offline (died)", dropped: "Dropped (moved)",
};
export const SENSOR_STATES = ["fire", "warm", "dropped", "offline", "ok"] as const;
