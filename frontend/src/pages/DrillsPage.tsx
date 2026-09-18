import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { DrillScenario } from "../api/types";
import { useAuth } from "../state/AuthContext";
import { useTime } from "../state/TimeContext";
import { useAsync } from "../hooks/useAsync";
import { LevelBadge } from "../components/LevelBadge";
import { fmtTime } from "../api/levels";

const SCENARIOS: { id: DrillScenario; title: string; desc: string; needsMesh: boolean }[] = [
  { id: "approaching", title: "Wildfire approaching", desc: "Satellite hotspots move toward the site, then ground sensors confirm fire and one dies.", needsMesh: false },
  { id: "sensor_first", title: "Sensors before satellites", desc: "Night and cloud: only the ground sensors see the fire. Tests trust in the sensor mesh.", needsMesh: true },
  { id: "false_alarm", title: "Possible false alarm", desc: "One sensor warms up and tilts, satellites see nothing. Tests a proportionate response.", needsMesh: true },
];
const PACES = [[15, "Fast demo (15 s per signal)"], [30, "Standard (30 s per signal)"], [60, "Realistic (1 min per signal)"]] as const;

function NewDrill() {
  const nav = useNavigate();
  const { step } = useTime();
  const { data: sit } = useAsync(() => api.getSituation(step), []);
  const { data: staff } = useAsync(() => api.getStaff(), []);
  const [siteId, setSiteId] = useState("");
  const [scenario, setScenario] = useState<DrillScenario>("approaching");
  const [pace, setPace] = useState(30);
  const [picked, setPicked] = useState<string[]>([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (staff) setPicked(staff.map((s) => s.email)); }, [staff]);
  useEffect(() => { if (!siteId && sit) setSiteId(sit.sites.find((s) => s.sensors_installed)?.site_id ?? sit.sites[0]?.site_id ?? ""); }, [sit, siteId]);

  const site = sit?.sites.find((s) => s.site_id === siteId);
  const sc = SCENARIOS.find((s) => s.id === scenario)!;
  const blocked = sc.needsMesh && site && !site.sensors_installed;

  const start = async () => {
    setBusy(true); setErr("");
    try {
      const d = await api.createDrill({ site_id: siteId, scenario, pace_s: pace, participants: picked });
      nav(`/drills/${d.drill_id}`);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <div className="card grid" style={{ gap: 16 }}>
      <div>
        <div className="eyebrow">Start a drill</div>
        <div className="small dim" style={{ marginTop: 4 }}>Pick a real site and a case study. Everyone selected gets a drill alert on every screen, must acknowledge, then choose what they would do. You get a scoreboard.</div>
      </div>
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div>
          <label>Site</label>
          <select value={siteId} onChange={(e) => setSiteId(e.target.value)}>
            {sit?.sites.map((s) => <option key={s.site_id} value={s.site_id}>{s.name}{s.sensors_installed ? " · sensor mesh" : ""}</option>)}
          </select>
        </div>
        <div>
          <label>Pace</label>
          <select value={pace} onChange={(e) => setPace(Number(e.target.value))}>
            {PACES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      </div>
      <div className="grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
        {SCENARIOS.map((s) => (
          <label key={s.id} className={`check-opt ${scenario === s.id ? "on" : ""}`} style={{ display: "block" }}>
            <input type="radio" name="scenario" checked={scenario === s.id} onChange={() => setScenario(s.id)} style={{ display: "none" }} />
            <div style={{ fontWeight: 700, marginBottom: 4 }}>{s.title}</div>
            <div className="small dim">{s.desc}</div>
            {s.needsMesh && <div className="small mute" style={{ marginTop: 6 }}>Needs a sensor mesh</div>}
          </label>
        ))}
      </div>
      <div>
        <label>Who gets alerted ({picked.length})</label>
        <div className="row wrap" style={{ gap: 8, marginTop: 6 }}>
          {staff?.map((u) => {
            const on = picked.includes(u.email);
            return (
              <button key={u.email} type="button" className={`btn sm ${on ? "primary" : "ghost"}`}
                onClick={() => setPicked(on ? picked.filter((p) => p !== u.email) : [...picked, u.email])}>
                {u.name} <span className="mute">· {u.role}</span>
              </button>
            );
          })}
        </div>
      </div>
      {blocked && <div className="small" style={{ color: "var(--elevated)" }}>This site has no sensor mesh. Install one from the site page, or pick another site or scenario.</div>}
      {err && <div className="small" style={{ color: "var(--critical-hot)" }}>{err}</div>}
      <div><button className="btn primary" disabled={busy || !siteId || !picked.length || !!blocked} onClick={start}>{busy ? <span className="spinner" /> : "Start drill and alert everyone"}</button></div>
    </div>
  );
}

export function DrillsPage() {
  const { user } = useAuth();
  const admin = user?.role === "admin";
  const { data: drills, error } = useAsync(() => api.getDrills(), []);

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div>
        <div className="eyebrow">Training</div>
        <h1 className="display" style={{ fontSize: "clamp(28px,3.6vw,42px)" }}>Drills</h1>
        <div className="dim small" style={{ maxWidth: 720 }}>Test the team on a realistic case study: simulated detection signals on a real site, a drill alert to every employee, and a score for speed and for choosing the right protocol actions. Drills never touch real alerts or sensor history.</div>
      </div>
      {admin && <NewDrill />}
      {error && <div className="card dim">{error}</div>}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table>
          <thead><tr><th>Drill</th><th>Site</th><th>Started</th><th>Level</th><th>Responses</th><th>Status</th></tr></thead>
          <tbody>
            {drills?.map((d) => {
              const answered = admin ? d.responses.filter((r) => r.responded_at).length : null;
              const avg = admin && answered ? Math.round(d.responses.filter((r) => r.score !== null).reduce((a, r) => a + (r.score ?? 0), 0) / answered) : null;
              return (
                <tr key={d.drill_id}>
                  <td><Link className="link" to={`/drills/${d.drill_id}`}>{d.scenario_title}</Link><div className="mono small mute">{d.drill_id}</div></td>
                  <td className="small">{d.site_name}</td>
                  <td className="mono small">{fmtTime(d.created_at)}</td>
                  <td><LevelBadge level={d.level} /></td>
                  <td className="small">{admin ? <>{answered}/{d.participants.length}{avg !== null && <span className="dim"> · avg {avg}</span>}</> : d.my_response?.score != null ? `your score ${d.my_response.score}` : d.my_response?.responded_at ? "answered" : "not answered"}</td>
                  <td>{d.status === "running" ? <span className="chip" style={{ borderColor: "var(--critical-hot)", color: "var(--critical-hot)" }}>running</span> : <span className="chip">ended</span>}</td>
                </tr>
              );
            })}
            {drills?.length === 0 && <tr><td colSpan={6} className="dim small" style={{ padding: 24, textAlign: "center" }}>No drills yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div></div>
  );
}
