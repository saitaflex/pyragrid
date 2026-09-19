import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api/client";
import type { DrillStage, DrillView } from "../api/types";
import { useAuth } from "../state/AuthContext";
import { SiteMap, type MapMark } from "../components/SiteMap";
import { LevelBadge } from "../components/LevelBadge";
import { EstimateLine, SensorLegend } from "../components/Sensors";
import { SENSOR_COLOR } from "../api/levels";

const STAGE_COLOR: Record<DrillStage["kind"], string> = {
  satellite: "#FF8A3D", satellite_clear: "#3FA34D", sensor_warm: SENSOR_COLOR.warm, sensor_fire: SENSOR_COLOR.fire,
  sensor_offline: SENSOR_COLOR.offline, sensor_dropped: SENSOR_COLOR.dropped, sensor_normal: SENSOR_COLOR.ok,
};
const STAGE_TAG: Record<DrillStage["kind"], string> = {
  satellite: "SATELLITE", satellite_clear: "SATELLITE", sensor_warm: "SENSOR", sensor_fire: "SENSOR",
  sensor_offline: "SENSOR", sensor_dropped: "SENSOR", sensor_normal: "SENSOR",
};
const secs = (s: number | null) => (s === null ? "—" : s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`);

function Countdown({ deadline }: { deadline: number }) {
  const [now, setNow] = useState(deadline);
  useEffect(() => {
    const tick = () => setNow(Date.now());
    const t = window.setInterval(tick, 500);
    tick();
    return () => window.clearInterval(t);
  }, [deadline]);
  return <span className="mono">{Math.max(0, Math.ceil((deadline - now) / 1000))}s</span>;
}

function Respond({ d, onDone }: { d: DrillView; onDone: (v: DrillView) => void }) {
  const [chosen, setChosen] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const mine = d.my_response;

  if (!mine?.acked_at) {
    return (
      <div className="card grid" style={{ gap: 12, borderColor: "var(--critical-hot)" }}>
        <div className="eyebrow" style={{ color: "var(--critical-hot)" }}>Step 1 · Acknowledge</div>
        <div className="small dim">The clock started when the alert went out. Acknowledge that you have seen it.</div>
        <button className="btn primary" disabled={busy} onClick={async () => { setBusy(true); try { onDone(await api.ackDrill(d.drill_id)); } finally { setBusy(false); } }}>
          I have seen this alert
        </button>
      </div>
    );
  }
  if (mine.responded_at) {
    const exp = new Set(d.expected_actions ?? []);
    return (
      <div className="card grid" style={{ gap: 12 }}>
        <div className="between"><div className="eyebrow">Your result</div><div className="display" style={{ fontSize: 34, color: "var(--ember-2)" }}>{mine.score}<span className="small mute">/100</span></div></div>
        <div className="small dim">Acknowledged in {secs(mine.ack_seconds)} · responded in {secs(mine.respond_seconds)} · {mine.correct} correct, {mine.wrong} wrong, {mine.missed} missed</div>
        <div className="grid" style={{ gap: 6 }}>
          {d.options.filter((o) => exp.has(o) || mine.actions.includes(o)).map((o) => {
            const picked = mine.actions.includes(o), right = exp.has(o);
            return (
              <div key={o} className="row small" style={{ gap: 8, color: right ? (picked ? "var(--text)" : "var(--elevated)") : "var(--critical-hot)" }}>
                <span style={{ width: 16 }}>{right ? (picked ? "✓" : "○") : "✕"}</span>
                <span>{o}{!picked && right && <span className="mute"> (missed)</span>}{picked && !right && <span className="mute"> (not in protocol)</span>}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }
  return (
    <div className="card grid" style={{ gap: 12 }}>
      <div className="eyebrow">Step 2 · What do you do?</div>
      <div className="small dim">Pick every action you would take now. Wrong actions cost points, and so do missed ones.</div>
      <div className="grid" style={{ gap: 8 }}>
        {d.options.map((o) => {
          const on = chosen.includes(o);
          return (
            <label key={o} className={`check-opt ${on ? "on" : ""}`}>
              <input type="checkbox" checked={on} onChange={() => setChosen(on ? chosen.filter((c) => c !== o) : [...chosen, o])} />
              <span>{o}</span>
            </label>
          );
        })}
      </div>
      <textarea placeholder="Optional note (what would you say on the radio?)" value={note} onChange={(e) => setNote(e.target.value)} rows={2} />
      {err && <div className="small" style={{ color: "var(--critical-hot)" }}>{err}</div>}
      <button className="btn primary" disabled={busy || !chosen.length} onClick={async () => {
        setBusy(true); setErr("");
        try { onDone(await api.respondDrill(d.drill_id, chosen, note)); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
      }}>Submit response</button>
    </div>
  );
}

export function DrillPage() {
  const { drillId = "" } = useParams();
  const { user } = useAuth();
  const [d, setD] = useState<DrillView | null>(null);
  const [err, setErr] = useState("");
  const [deadline, setDeadline] = useState<number | null>(null);
  const admin = user?.role === "admin";

  const apply = (v: DrillView) => {
    setDeadline(v.next_stage_in_s === null ? null : Date.now() + v.next_stage_in_s * 1000);
    setD(v);
  };
  useEffect(() => {
    let alive = true;
    const load = () => api.getDrill(drillId).then((v) => { if (alive) { apply(v); setErr(""); } }).catch((e) => alive && setErr(e.message));
    load();
    const t = window.setInterval(load, 2000);
    return () => { alive = false; window.clearInterval(t); };
  }, [drillId]);

  if (err && !d) return <div className="page"><div className="container"><div className="card">{err}</div></div></div>;
  if (!d) return <div className="page"><div className="container"><span className="spinner" /></div></div>;

  const participant = !!user && d.participants.includes(user.email);
  // satellite signals are placed on the map; sensor signals colour their hexagon
  const marks: MapMark[] = d.stages.filter((s) => s.lat !== null && s.lon !== null && !s.sensor_id)
    .map((s) => ({ lat: s.lat!, lon: s.lon!, label: s.title, color: STAGE_COLOR[s.kind] }));

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div className="between wrap">
        <div>
          <Link to="/drills" className="link small">← Drills</Link>
          <div className="row" style={{ gap: 10, marginTop: 6 }}>
            <span className="chip" style={{ borderColor: "var(--critical-hot)", color: "var(--critical-hot)", fontWeight: 800 }}>DRILL</span>
            <span className="mono small mute">{d.drill_id}</span>
          </div>
          <h1 className="display" style={{ fontSize: "clamp(26px,3.4vw,40px)", marginTop: 6 }}>{d.scenario_title}</h1>
          <div className="dim small">{d.site_name} · started by {d.created_by} · {d.participants.length} people alerted</div>
        </div>
        <div className="row" style={{ gap: 10 }}>
          <LevelBadge level={d.level} />
          {d.status === "running" ? <span className="chip" style={{ borderColor: "var(--critical-hot)", color: "var(--critical-hot)" }}>running · {secs(d.elapsed_s)}</span> : <span className="chip">ended</span>}
          {admin && d.status === "running" && <button className="btn sm ghost" onClick={async () => apply(await api.endDrill(d.drill_id))}>End drill</button>}
        </div>
      </div>

      <div className="card small" style={{ borderColor: "var(--ember)" }}><b>Briefing.</b> {d.briefing} <span className="mute">{d.disclaimer}</span></div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1.2fr", gap: 18, alignItems: "start" }}>
        <div className="grid" style={{ gap: 18 }}>
          <div className="card">
            <div className="between" style={{ marginBottom: 10 }}>
              <div className="eyebrow">Signals · {d.stages.length}/{d.total_stages}</div>
              {deadline !== null && <span className="small dim">next signal in <Countdown deadline={deadline} /></span>}
            </div>
            <div className="grid" style={{ gap: 0 }}>
              <AnimatePresence initial={false}>
                {[...d.stages].reverse().map((s) => (
                  <motion.div key={s.offset_s} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} className="row"
                    style={{ gap: 12, padding: "10px 0", borderBottom: "1px solid var(--border)", alignItems: "flex-start" }}>
                    <span style={{ width: 10, height: 10, borderRadius: 3, marginTop: 5, background: STAGE_COLOR[s.kind], flex: "none" }} />
                    <div style={{ flex: 1 }}>
                      <div className="small"><span className="mono mute">T+{secs(s.offset_s)}</span> <span className="mute">{STAGE_TAG[s.kind]}</span> <b>{s.title}</b></div>
                      <div className="small dim">{s.detail}</div>
                    </div>
                    <LevelBadge level={s.level} />
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
          {participant && d.status === "running" && <Respond d={d} onDone={apply} />}
          {participant && d.status === "ended" && d.my_response?.responded_at && <Respond d={d} onDone={apply} />}
          {participant && d.status === "ended" && !d.my_response?.responded_at && <div className="card small dim">This drill has ended. You did not respond in time.</div>}
        </div>
        <div className="grid" style={{ gap: 10 }}>
          <SiteMap sites={[{ site_id: d.site_id, lat: d.lat, lon: d.lon, level: d.level }]} detections={[]} sensors={d.nodes} estimates={d.fire_estimate ? [d.fire_estimate] : []} marks={marks}
            center={[d.lon, d.lat]} zoom={marks.length ? 10.8 : 12.4} height={440} />
          {d.fire_estimate && <EstimateLine est={d.fire_estimate} />}
          <SensorLegend />
        </div>
      </div>

      {admin && (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div className="eyebrow" style={{ padding: "16px 18px 0" }}>Scoreboard</div>
          <table>
            <thead><tr><th>Employee</th><th>Acknowledged</th><th>Responded</th><th>Correct</th><th>Wrong</th><th>Missed</th><th>Score</th></tr></thead>
            <tbody>
              {d.participants.map((p) => {
                const r = d.responses.find((x) => x.email === p);
                return (
                  <tr key={p}>
                    <td className="small">{d.participant_names[p] ?? p}<div className="mono mute" style={{ fontSize: 11 }}>{p}</div></td>
                    <td className="mono small">{r?.acked_at ? secs(r.ack_seconds) : <span className="mute">waiting</span>}</td>
                    <td className="mono small">{r?.responded_at ? secs(r.respond_seconds) : <span className="mute">waiting</span>}</td>
                    <td className="mono">{r?.responded_at ? r.correct : ""}</td>
                    <td className="mono" style={{ color: r?.wrong ? "var(--critical-hot)" : undefined }}>{r?.responded_at ? r.wrong : ""}</td>
                    <td className="mono">{r?.responded_at ? r.missed : ""}</td>
                    <td className="display" style={{ fontSize: 20, color: "var(--ember-2)" }}>{r?.score ?? ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {d.expected_actions && (
            <div style={{ padding: "12px 18px 18px" }} className="small dim">
              <b className="small" style={{ color: "var(--text)" }}>Answer key (from your SOP rules):</b> {d.expected_actions.join(" · ")}
              <div className="mute" style={{ marginTop: 6 }}>Alert sent in-app and by email (simulated outbox) to: {d.participants.join(", ")}</div>
            </div>
          )}
        </div>
      )}
    </div></div>
  );
}
