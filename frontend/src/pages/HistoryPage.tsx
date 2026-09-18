import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { StatTile } from "../components/StatTile";
import { LevelBadge } from "../components/LevelBadge";
import { Reveal } from "../components/Reveal";
import { fmtTime } from "../api/levels";

export function HistoryPage() {
  const { data: s } = useAsync(() => api.getSummary(), []);
  const { data: incidents } = useAsync(() => api.getIncidentsHistory(), []);

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div><div className="eyebrow">History</div><h1 className="display" style={{ fontSize: "clamp(28px,3.6vw,42px)" }}>Measured backtest</h1></div>

      {s && (
        <Reveal>
          <div className="card pad-lg" style={{ fontSize: "clamp(18px,2.4vw,26px)", fontFamily: "var(--display)", letterSpacing: "-0.02em" }}>
            <span className="mute">{s.total_detections} satellite detections became </span>
            <span style={{ color: "var(--ember-2)" }}>{s.alerts_raised} alerts</span>
            <span className="mute"> across </span>
            <span style={{ color: "var(--ember-2)" }}>{s.incidents} incidents</span>.
          </div>
        </Reveal>
      )}

      <div className="grid" style={{ gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
        <StatTile label="Sites ever HIGH" value={s?.sites_ever_high ?? 0} accent="var(--high)" />
        <StatTile label="Sites ever CRITICAL" value={s?.sites_ever_critical ?? 0} accent="var(--critical-hot)" />
        <StatTile label="Reached by fire" value={s?.sites_reached_by_fire ?? 0} accent="var(--ember)" />
        <StatTile label="Missed exposures" value={s?.missed_exposures ?? 0} />
        <StatTile label="Median lead time" value={s?.median_lead_time_hours ?? 0} suffix="h" accent="var(--normal)" hint="first HIGH → contact" />
        <StatTile label="Explanation coverage" value={s?.explanation_coverage_pct ?? 0} suffix="%" accent="var(--normal)" />
        <StatTile label="Detections used" value={s?.detections_used ?? 0} />
        <StatTile label="Incidents" value={s?.incidents ?? 0} accent="var(--ember)" />
      </div>

      <Reveal>
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table>
            <thead><tr><th>Opened</th><th>Site</th><th>Level</th><th>Headline</th><th>Closed</th><th></th></tr></thead>
            <tbody>
              {incidents?.map((inc) => (
                <tr key={inc.incident_id}>
                  <td className="mono small">{fmtTime(inc.opened_at)}</td>
                  <td>{inc.site_name}</td>
                  <td><LevelBadge level={inc.level} score={inc.score} /></td>
                  <td className="small dim">{inc.headline}</td>
                  <td className="mono small mute">{inc.closed_at ? fmtTime(inc.closed_at) : "open"}</td>
                  <td><Link className="link small" to={`/incidents/${inc.incident_id}`}>Open →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Reveal>
      {s && <div className="small mute">Data source: {s.data_source} · model {s.model_version} · {s.start.slice(0, 10)} → {s.end.slice(0, 10)}</div>}
    </div></div>
  );
}
