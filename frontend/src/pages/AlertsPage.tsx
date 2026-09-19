import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api/client";
import { useTime } from "../state/TimeContext";
import { useAsync } from "../hooks/useAsync";
import { TimeSlider } from "../components/TimeSlider";
import { LevelBadge } from "../components/LevelBadge";
import { fmtTime, LEVEL_RANK as RANK } from "../api/levels";

export function AlertsPage() {
  const { step } = useTime();
  const [filter, setFilter] = useState<"all" | "unacknowledged">("all");
  const [open, setOpen] = useState<string | null>(null);
  const [minLevel, setMinLevel] = useState<0 | 2 | 3>(0);          // 0 all, 2 high and up, 3 critical only
  const [serious, setSerious] = useState(false);                    // sort most serious first
  const { data: all, reload } = useAsync(() => api.getAlerts(step, filter), [step, filter]);
  const alerts = all?.filter((a) => RANK[a.to_level] >= minLevel)
    .sort((a, b) => (serious ? RANK[b.to_level] - RANK[a.to_level] || b.score - a.score : 0) || b.at.localeCompare(a.at));

  const ack = async (id: string) => { await api.acknowledge(id); reload(); };

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div className="between wrap">
        <div><div className="eyebrow">Alerts</div><h1 className="display" style={{ fontSize: "clamp(28px,3.6vw,42px)" }}>Level transitions</h1></div>
        <div className="row wrap" style={{ gap: 8 }}>
          {(["all", "unacknowledged"] as const).map((f) => (
            <button key={f} className={`btn sm ${filter === f ? "primary" : "ghost"}`} aria-pressed={filter === f} onClick={() => setFilter(f)}>{f}</button>
          ))}
          <span style={{ width: 1, height: 22, background: "var(--border-2)" }} aria-hidden />
          {([[0, "All levels"], [2, "High and up"], [3, "Critical only"]] as const).map(([v, label]) => (
            <button key={v} className={`btn sm ${minLevel === v ? "primary" : "ghost"}`} aria-pressed={minLevel === v} onClick={() => setMinLevel(v)}>{label}</button>
          ))}
          <button className={`btn sm ${serious ? "primary" : "ghost"}`} aria-pressed={serious} onClick={() => setSerious((x) => !x)}>Most serious first</button>
        </div>
      </div>
      <TimeSlider />

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table>
          <thead><tr><th>Time</th><th>Site</th><th>Transition</th><th>Score</th><th>Headline</th><th></th></tr></thead>
          <tbody>
            {alerts?.map((a) => (
              <>
                <tr key={a.alert_id} style={{ cursor: "pointer" }} onClick={() => setOpen(open === a.alert_id ? null : a.alert_id)}>
                  <td className="mono small">{fmtTime(a.at)}</td>
                  <td>{a.site_name}</td>
                  <td><span className="row" style={{ gap: 6 }}><LevelBadge level={a.from_level} /><span className="mute">→</span><LevelBadge level={a.to_level} /></span></td>
                  <td className="mono">{a.score}</td>
                  <td className="small dim">{a.headline}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    {a.acknowledged ? <span className="chip observed">ack · {a.acknowledged_by}</span>
                      : <button className="btn sm" onClick={() => ack(a.alert_id)}>Acknowledge</button>}
                  </td>
                </tr>
                <AnimatePresence>
                  {open === a.alert_id && (
                    <tr><td colSpan={6} style={{ padding: 0 }}>
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} style={{ overflow: "hidden" }}>
                        <div style={{ padding: 16, background: "var(--bg-1)" }} className="grid" >
                          <div className="row wrap" style={{ gap: 8 }}>
                            {a.rule_ids.map((r) => <span key={r} className="chip">{r}</span>)}
                            <span className="mono small mute">detection {a.triggering_detection_id ?? "—"}</span>
                          </div>
                          <div className="grid" style={{ gap: 6, marginTop: 10 }}>
                            {a.actions.map((ac, i) => <div key={i} className="small row" style={{ gap: 8 }}><span style={{ color: "var(--ember-2)" }}>▸</span>{ac}</div>)}
                          </div>
                          <Link to={`/sites/${a.site_id}`} className="link small" style={{ marginTop: 10 }}>Open site →</Link>
                        </div>
                      </motion.div>
                    </td></tr>
                  )}
                </AnimatePresence>
              </>
            ))}
            {alerts?.length === 0 && <tr><td colSpan={6} className="dim small" style={{ padding: 24, textAlign: "center" }}>{minLevel ? "No alerts at this level up to this time." : "No alerts up to this time."}</td></tr>}
          </tbody>
        </table>
      </div>
    </div></div>
  );
}
