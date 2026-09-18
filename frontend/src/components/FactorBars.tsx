import { motion } from "framer-motion";
import type { Factors, FactorStatuses } from "../api/types";

const MAX: Record<keyof Factors, number> = { proximity: 35, wind_alignment: 25, weather: 15, fuel: 15, vulnerability: 10 };
const LABEL: Record<keyof Factors, string> = {
  proximity: "Proximity", wind_alignment: "Wind alignment", weather: "Weather", fuel: "Fuel", vulnerability: "Vulnerability",
};

export function FactorBars({ factors, statuses }: { factors: Factors; statuses: FactorStatuses }) {
  const keys = Object.keys(MAX) as (keyof Factors)[];
  return (
    <div className="grid" style={{ gap: 14 }}>
      {keys.map((k) => {
        const v = factors[k];
        const status = statuses[k];
        const pct = v === null ? 0 : (v / MAX[k]) * 100;
        return (
          <div key={k}>
            <div className="between" style={{ marginBottom: 6 }}>
              <span className="small dim">{LABEL[k]}</span>
              <span className="row" style={{ gap: 8 }}>
                <span className={`chip ${status}`}>{status === "unknown" ? "UNKNOWN" : status.replace("_", " ")}</span>
                <span className="mono small">{v === null ? "—" : v.toFixed(1)}<span className="mute"> / {MAX[k]}</span></span>
              </span>
            </div>
            <div className="meter">
              <motion.span initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.7, ease: [0.2, 0.7, 0.2, 1] }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
