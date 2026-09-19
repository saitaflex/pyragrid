import type { FireEstimate, SensorEvent, SensorKind, SensorMesh } from "../api/types";
import { SENSOR_COLOR, SENSOR_KIND_LABEL, SENSOR_LABEL, SENSOR_STATES, compass, fmtTime } from "../api/levels";

const SHAPE_PATH: Record<SensorKind, string> = {
  structure: "M11 2 L20 10 L17 10 L17 19 L5 19 L5 10 L2 10 Z",
  vegetation: "M11 1.5 L19 15 L13 15 L13 20 L9 20 L9 15 L3 15 Z",
  fence: "M5 5 H17 V17 H5 Z",
  grid: "M18 11 A7 7 0 1 1 4 11 A7 7 0 1 1 18 11 Z",
};

export function SensorShape({ kind, color, size = 14 }: { kind: SensorKind; color: string; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 22 22" aria-hidden><path d={SHAPE_PATH[kind]} fill={color} stroke="rgba(10,10,12,.9)" strokeWidth="1.6" strokeLinejoin="round" /></svg>;
}

/** Colour = state, shape = what the sensor is mounted on. */
export function SensorLegend({ shapes = true }: { shapes?: boolean }) {
  return (
    <div className="grid" style={{ gap: 6, justifyItems: "end" }}>
      <div className="row wrap" style={{ gap: 12 }}>
        {SENSOR_STATES.map((s) => (
          <span key={s} className="row small" style={{ gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: SENSOR_COLOR[s] }} aria-hidden />
            <span className="dim">{SENSOR_LABEL[s]}</span>
          </span>
        ))}
      </div>
      {shapes && (
        <div className="row wrap" style={{ gap: 12 }}>
          {(["structure", "vegetation", "fence", "grid"] as SensorKind[]).map((k) => (
            <span key={k} className="row small" style={{ gap: 6 }}><SensorShape kind={k} color="#a7a3ad" /><span className="mute">{SENSOR_KIND_LABEL[k]}</span></span>
          ))}
          <span className="row small" style={{ gap: 6 }}>
            <span style={{ width: 12, height: 12, borderRadius: "50%", border: "2px dashed #FF3B30", background: "rgba(255,59,48,.15)" }} aria-hidden />
            <span className="mute">Estimated fire position</span>
          </span>
        </div>
      )}
    </div>
  );
}

export function EstimateLine({ est }: { est: FireEstimate }) {
  return (
    <div className="small" style={{ color: "var(--critical-hot)" }}>
      <b>Estimated fire position:</b> {est.distance_m} m {compass(est.bearing_deg)} of the site centre, ± {est.radius_m} m
      <span className="dim"> · combined from {est.sensors} sensor{est.sensors > 1 ? "s" : ""} ({est.confidence} confidence) · hottest {est.hottest}</span>
    </div>
  );
}

export function PlacementLine({ mesh }: { mesh: SensorMesh }) {
  const p = mesh.placement;
  return (
    <div className="row wrap small dim" style={{ gap: 10 }}>
      {p.structure > 0 && <span className="row" style={{ gap: 5 }}><SensorShape kind="structure" color="#a7a3ad" size={12} />{p.structure} at buildings</span>}
      {p.vegetation > 0 && <span className="row" style={{ gap: 5 }}><SensorShape kind="vegetation" color="#a7a3ad" size={12} />{p.vegetation} at vegetation edges</span>}
      <span className="row" style={{ gap: 5 }}><SensorShape kind="fence" color="#a7a3ad" size={12} />{p.fence} on the fence</span>
      {p.grid > 0 && <span className="row" style={{ gap: 5 }}><SensorShape kind="grid" color="#a7a3ad" size={12} />{p.grid} on open ground</span>}
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
              <div className="small"><b>{e.label}</b> <span className="dim">{e.place}</span>{showSite && <span className="mute"> · {e.site_name}</span>} <span style={{ color }}>{SENSOR_LABEL[e.kind === "recovered" ? "ok" : e.kind]}</span></div>
              <div className="small dim">{e.detail}</div>
            </div>
            <span className="mono small mute" style={{ whiteSpace: "nowrap" }}>{fmtTime(e.at).replace(" UTC", "")}</span>
          </div>
        );
      })}
    </div>
  );
}
