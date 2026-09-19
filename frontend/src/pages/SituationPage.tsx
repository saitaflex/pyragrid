import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { SharingPolicy } from "../api/types";
import { useTime } from "../state/TimeContext";
import { useAsync } from "../hooks/useAsync";
import { TimeSlider } from "../components/TimeSlider";
import { SiteMap } from "../components/SiteMap";
import { StatTile } from "../components/StatTile";
import { LevelBadge } from "../components/LevelBadge";
import { SensorEventList, SensorLegend } from "../components/Sensors";
import { SITE_TYPE_LABEL, compass, eur } from "../api/levels";

const FIELDS: [keyof SharingPolicy, string][] = [
  ["asset_values", "Asset values (€)"], ["personnel", "Personnel on site"], ["access_routes", "Access routes"],
  ["criticality", "Criticality"], ["handoff", "Firefighter handoff pack"], ["company_ops", "Company operations (alerts, rules, drills)"],
];

export function SituationPage() {
  const { step } = useTime();
  const { data: sit, error } = useAsync(() => api.getSituation(step), [step]);
  const { data: sensors } = useAsync(() => api.getSensors(step), [step]);
  const { data: dets } = useAsync(() => api.getDetections(step), [step]);
  const pol = sit?.policy;

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div className="between wrap">
        <div>
          <div className="eyebrow">Shared situation · {pol?.label ?? "…"}</div>
          <h1 className="display" style={{ fontSize: "clamp(28px,3.6vw,42px)" }}>Wildfire picture around the sites</h1>
        </div>
        <SensorLegend />
      </div>
      {error && <div className="card dim">{error}</div>}
      {pol && !pol.company_ops && (
        <div className="card small" style={{ borderColor: "var(--ember)" }}>
          You are viewing as <b>{pol.label}</b>. The operating company shares satellite detections, ground-sensor
          readings and site risk levels with you{pol.personnel ? ", plus personnel counts" : ""}{pol.access_routes ? " and access routes" : ""}.
          Asset values and internal operations stay private.
        </div>
      )}
      <TimeSlider />

      <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
        <StatTile label="Critical sites" value={sit?.counts.CRITICAL ?? 0} accent="var(--critical-hot)" hint="now" />
        <StatTile label="High" value={sit?.counts.HIGH ?? 0} accent="var(--high)" hint="now" />
        <StatTile label="Fire confirmed by sensors" value={sit?.sites.filter((s) => s.ground_fire).length ?? 0} accent="var(--ember)" hint="sites" />
        <StatTile label="Satellite detections" value={dets?.length ?? 0} accent="var(--ember-2)" hint="last 12 h" />
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1.5fr 1fr", gap: 18, alignItems: "start" }}>
        <SiteMap sites={sit?.sites ?? []} detections={dets ?? []} sensors={sensors?.nodes ?? []} estimates={(sensors?.meshes ?? []).flatMap((m) => (m.fire_estimate ? [m.fire_estimate] : []))} height={500} />
        <div className="card" style={{ maxHeight: 500, overflow: "auto" }}>
          <div className="eyebrow" style={{ marginBottom: 8 }}>Ground sensor events</div>
          <SensorEventList events={sensors?.events ?? []} max={25} />
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: "auto" }}>
        <table>
          <thead><tr>
            <th>Site</th><th>Risk</th><th>Nearest fire</th><th>Sensors</th>
            {pol?.personnel && <th>People</th>}{pol?.access_routes && <th>Access</th>}
            {pol?.asset_values && <th>Value</th>}{pol?.handoff && <th></th>}
          </tr></thead>
          <tbody>
            {sit?.sites.map((s) => (
              <tr key={s.site_id}>
                <td>{s.name}<div className="small mute">{SITE_TYPE_LABEL[s.type]}{s.criticality !== null && ` · criticality ${s.criticality}/5`}</div></td>
                <td><LevelBadge level={s.level} score={s.score} /></td>
                <td className="small">{s.nearest_fire_km === null ? <span className="dim">none within 25 km</span> : <>{s.nearest_fire_km.toFixed(1)} km {compass(s.fire_bearing_deg ?? 0)}{s.fire_moving_toward_site && <span style={{ color: "var(--critical-hot)" }}> · moving toward</span>}</>}</td>
                <td className="small">{s.ground_fire ? <span style={{ color: "var(--critical-hot)", fontWeight: 700 }}>FIRE detected</span> : s.sensors_installed ? <span className="dim">installed</span> : <span className="mute">none</span>}</td>
                {pol?.personnel && <td className="mono">{s.personnel_on_site}</td>}
                {pol?.access_routes && <td className="small">{s.access_routes?.map((r) => <div key={r.name} style={{ color: r.status === "potentially_exposed" ? "var(--high)" : undefined }}>{r.name}: {r.status === "potentially_exposed" ? "exposed" : "open"}</div>)}</td>}
                {pol?.asset_values && <td className="mono small">{s.value_eur !== null && eur(s.value_eur)}</td>}
                {pol?.handoff && <td><Link className="link small" to={`/sites/${s.site_id}/handoff`}>Handoff pack →</Link></td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {sit && (
        <div className="card" style={{ padding: 0, overflow: "auto" }}>
          <div className="eyebrow" style={{ padding: "16px 18px 0" }}>Who sees what</div>
          <table>
            <thead><tr><th>Data</th>{sit.matrix.map((p) => <th key={p.role} style={{ color: p.role === sit.viewer_role ? "var(--ember-2)" : undefined }}>{p.label}</th>)}</tr></thead>
            <tbody>
              <tr><td className="small">Satellite detections, sensor mesh, risk level</td>{sit.matrix.map((p) => <td key={p.role}>✓</td>)}</tr>
              {FIELDS.map(([k, label]) => (
                <tr key={k}><td className="small">{label}</td>{sit.matrix.map((p) => <td key={p.role} style={{ color: p[k] ? "var(--text)" : "var(--text-mute)" }}>{p[k] ? "✓" : "—"}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div></div>
  );
}
