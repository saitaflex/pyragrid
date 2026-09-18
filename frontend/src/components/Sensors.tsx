import type { SensorEvent, SensorMesh } from "../api/types";
import { SENSOR_COLOR, SENSOR_LABEL, SENSOR_STATES, fmtTime } from "../api/levels";

export function SensorLegend() {
  return (
    <div className="row wrap" style={{ gap: 12 }}>
      {SENSOR_STATES.map((s) => (
        <span key={s} className="row small" style={{ gap: 6 }}>
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden><polygon points="7,1 12.2,4 12.2,10 7,13 1.8,10 1.8,4" fill={SENSOR_COLOR[s]} fillOpacity={s === "ok" ? 0.35 : 0.8} stroke={SENSOR_COLOR[s]} /></svg>
          <span className="dim">{SENSOR_LABEL[s]}</span>
        </span>
      ))}
    </div>
  );
}

export function MeshCounts({ mesh }: { mesh: SensorMesh }) {
  return (
    <div className="row wrap" style={{ gap: 6 }}>
      {SENSOR_STATES.filter((s) => mesh.counts[s] > 0).map((s) => (
        <span key={s} className="chip" style={{ borderColor: SENSOR_COLOR[s], color: s === "ok" ? "var(--text-dim)" : SENSOR_COLOR[s] }}>
          {mesh.counts[s]} {SENSOR_LABEL[s].split(" ")[0].toLowerCase()}
        </span>
      ))}
    </div>
  );
}

const KIND_ICON: Record<SensorEvent["kind"], string> = { fire: "▲", warm: "●", offline: "✕", dropped: "↘", recovered: "✓" };

export function SensorEventList({ events, showSite = true, max = 40 }: { events: SensorEvent[]; showSite?: boolean; max?: number }) {
  const shown = events.filter((e) => e.kind !== "recovered").slice(0, max);
  if (!shown.length) return <div className="dim small">No sensor events up to this time.</div>;
  return (
    <div className="grid" style={{ gap: 0 }}>
      {shown.map((e) => {
        const color = SENSOR_COLOR[e.kind === "recovered" ? "ok" : e.kind];
        return (
          <div key={`${e.sensor_id}-${e.at}-${e.kind}`} className="row" style={{ gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)", alignItems: "flex-start" }}>
            <span style={{ color, width: 14, textAlign: "center", fontWeight: 700 }} aria-hidden>{KIND_ICON[e.kind]}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="small"><b>{e.label}</b>{showSite && <span className="dim"> · {e.site_name}</span>} <span style={{ color }}>{SENSOR_LABEL[e.kind === "recovered" ? "ok" : e.kind]}</span></div>
              <div className="small dim">{e.detail}</div>
            </div>
            <span className="mono small mute" style={{ whiteSpace: "nowrap" }}>{fmtTime(e.at).replace(" UTC", "")}</span>
          </div>
        );
      })}
    </div>
  );
}
