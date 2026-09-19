import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api, type SimStateBody } from "../api/client";
import type { FuelClass, Level, SensorNode, SimAdvice, Site } from "../api/types";
import { LEVEL_COLOR, compass } from "../api/levels";
import { useAsync } from "../hooks/useAsync";
import { SiteMap, type MapFire } from "../components/SiteMap";
import { LevelBadge } from "../components/LevelBadge";
import { SensorLegend } from "../components/Sensors";
import { notify, clearToasts } from "../components/Toasts";
import {
  FUEL_LABEL, autoSpeed, bearing, distM, fireAt, randomConditions, sensorReading,
  type Conditions, type FireState, type SiteLite,
} from "../sim/firesim";

type Phase = "setup" | "running" | "paused" | "over" | "response" | "logged";
const RANK: Record<Level, number> = { NORMAL: 0, ELEVATED: 1, HIGH: 2, CRITICAL: 3 };
const AUDIENCE: Record<string, string> = { operator: "Control room", site_team: "Site team", fire_service_liaison: "Fire service liaison" };
const MAX_MIN = 12 * 60;           // the run ends after 12 simulated hours if the fire never arrives
const hhmm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(Math.floor(m % 60)).padStart(2, "0")}`;

export function SimulatePage() {
  const { data: sites } = useAsync(() => api.getSites(), []);
  const [siteId, setSiteId] = useState("ES-OU-001");
  const site = sites?.find((s) => s.site_id === siteId);
  const lite: SiteLite | null = site ? { site_id: site.site_id, name: site.name, lat: site.lat, lon: site.lon, radius_m: site.radius_m } : null;
  const { data: sensorData } = useAsync(() => api.getSensors(0, siteId).catch(() => null), [siteId]);

  const [cond, setCond] = useState<Conditions>(() => randomConditions());
  const [placing, setPlacing] = useState(false);
  const [phase, setPhase] = useState<Phase>("setup");
  const [minutes, setMinutes] = useState(0);
  const [mult, setMult] = useState(1);
  const [seed, setSeed] = useState(() => Math.random() * 10);
  const [warning, setWarning] = useState(false);
  const [advice, setAdvice] = useState<SimAdvice | null>(null);
  const [adviceBusy, setAdviceBusy] = useState(false);
  const [adviceErr, setAdviceErr] = useState("");
  const [done, setDone] = useState<Record<string, string>>({});
  const [respStart, setRespStart] = useState(0);
  const [logMsg, setLogMsg] = useState("");
  const seen = useRef<{ level: Level; warm: boolean; fire: boolean; dead: number; eta: number[]; routes: string }>({ level: "NORMAL", warm: false, fire: false, dead: 0, eta: [], routes: "" });

  const st: FireState | null = useMemo(() => (lite && phase !== "setup" ? fireAt(lite, cond, minutes, seed) : null), [lite?.site_id, cond, minutes, seed, phase]);
  const nodes: SensorNode[] = useMemo(() => {
    const base = sensorData?.nodes ?? [];
    if (!st) return base.map((n) => ({ ...n, state: "ok", temp_c: 28, note: "Normal" }));
    return base.map((n) => {
      const r = sensorReading([n.lon, n.lat], st);
      return { ...n, state: r.state, temp_c: r.temp, note: r.state === "offline" ? "Destroyed by fire" : r.state === "fire" ? "Fire temperature" : r.state === "warm" ? "Heat nearby" : "Normal" };
    });
  }, [sensorData, st]);
  const counts = { fire: nodes.filter((n) => n.state === "fire").length, warm: nodes.filter((n) => n.state === "warm").length, dead: nodes.filter((n) => n.state === "offline").length };
  const level: Level = st?.level ?? "NORMAL";
  const intensity = st ? Math.min(1, 0.15 + RANK[level] * 0.28) : 0;
  const speed = lite ? autoSpeed(lite, cond) * mult : 1;

  // the clock: simulated minutes advance while running
  useEffect(() => {
    if (phase !== "running") return;
    const t = window.setInterval(() => setMinutes((m) => Math.min(MAX_MIN, m + speed * 0.2)), 200);
    return () => window.clearInterval(t);
  }, [phase, speed]);

  const body = (s: FireState): SimStateBody => ({
    minutes: Math.round(s.minutes), level: s.level, front_km: s.front_km, eta_min: s.eta_min,
    head_ros_m_min: s.head_ros_m_min, burned_ha: s.burned_ha, fire_moving_toward_site: s.fire_moving_toward_site,
    sensors_fire: counts.fire, sensors_warm: counts.warm, sensors_offline: counts.dead,
  });
  const askAI = async (s: FireState) => {
    setAdviceBusy(true); setAdviceErr("");
    try { setAdvice(await api.simAdvice(siteId, cond, body(s))); }
    catch (e) { setAdviceErr((e as Error).message); }
    finally { setAdviceBusy(false); }
  };

  // events: notifications and fresh AI advice when the situation changes
  useEffect(() => {
    if (!st || (phase !== "running" && phase !== "paused")) return;
    const k = seen.current;
    if (RANK[st.level] > RANK[k.level]) {
      k.level = st.level;
      notify(st.level === "CRITICAL" ? "critical" : "warn", `${site?.name}: level ${st.level.toLowerCase()}`,
        `Front ${st.front_km} km from the fence${st.eta_min ? `, about ${st.eta_min} min away` : ""}. Updating the response plan.`);
      askAI(st);
    }
    if (!k.warm && counts.warm) { k.warm = true; notify("info", "A ground sensor is warming up", "Heat is reaching the sensors around the site."); }
    if (!k.fire && counts.fire) { k.fire = true; notify("critical", "A ground sensor reports fire", "The fire is confirmed on the ground."); }
    // one notice for the first lost sensor, then one per five more, so the feed stays readable
    if (counts.dead > 0 && (k.dead === 0 || counts.dead >= k.dead + 5)) {
      k.dead = counts.dead;
      notify("warn", `${counts.dead} sensor${counts.dead > 1 ? "s" : ""} went silent`, "Destroyed by the fire. Those areas are no longer monitored.");
    }
    for (const limit of [60, 30, 10]) {
      if (st.eta_min !== null && st.eta_min > 0 && st.eta_min <= limit && !k.eta.includes(limit)) {
        k.eta.push(limit); notify(limit <= 10 ? "critical" : "warn", `Fire at the fence in about ${st.eta_min} min`, "At the current spread rate.");
      }
    }
    if (st.reached || minutes >= MAX_MIN) {
      setPhase("over");
      notify(st.reached ? "critical" : "info", st.reached ? "The fire reached the site fence" : "12 hours simulated",
        st.reached ? "The simulation stops here. Start the response." : `The front stopped ${st.front_km} km from the fence.`, 15000);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [st?.minutes, st?.level, counts.warm, counts.fire, counts.dead]);

  useEffect(() => {
    const exposed = advice ? Object.entries(advice.access_routes).filter(([, v]) => v === "potentially_exposed").map(([k]) => k).join(",") : "";
    if (exposed && exposed !== seen.current.routes) { seen.current.routes = exposed; notify("warn", `${exposed.replace(",", " and ")} faces the fire`, "Use the other route for any movement."); }
  }, [advice]);

  const start = () => {
    if (!lite) return;
    clearToasts();
    seen.current = { level: "NORMAL", warm: false, fire: false, dead: 0, eta: [], routes: "" };
    setSeed(Math.random() * 10); setMinutes(0); setAdvice(null); setDone({}); setLogMsg("");
    setPhase("running"); setWarning(true);
    const s0 = fireAt(lite, cond, 0, 0);
    seen.current.level = s0.level;
    notify("critical", `Fire reported ${cond.ignition_km} km ${compass(cond.ignition_bearing_deg)} of ${lite.name}`,
      `Wind ${cond.wind_kmh} km/h from ${compass(cond.wind_from_deg)}, ${cond.rh_pct} % humidity. Level ${s0.level.toLowerCase()}.`);
    askAI(s0);
    window.setTimeout(() => setWarning(false), 4500);
  };
  const reset = () => { setPhase("setup"); setMinutes(0); setAdvice(null); clearToasts(); };

  const onMapClick = (lon: number, lat: number) => {
    if (!placing || !lite) return;
    const km = Math.round((distM([lite.lon, lite.lat], [lon, lat]) / 1000) * 10) / 10;
    setCond((c) => ({ ...c, ignition_km: Math.max(0.8, km), ignition_bearing_deg: Math.round(bearing([lite.lon, lite.lat], [lon, lat])) }));
    setPlacing(false);
  };

  // the response checklist: the AI plan plus the protocol for the final level
  const tasks = useMemo(() => {
    const t = (advice?.suggestions ?? []).map((s) => ({ id: s.suggestion_id, text: s.title, who: AUDIENCE[s.audience], from: "AI plan" }));
    for (const a of advice?.protocol_actions ?? []) if (!t.some((x) => x.text === a)) t.push({ id: `p:${a}`, text: a, who: "Protocol", from: "Protocol" });
    return t;
  }, [advice]);
  const finish = async () => {
    const secs = Math.round((Date.now() - respStart) / 1000);
    const summary = st ? `${st.reached ? "Front reached the fence" : `Front stopped ${st.front_km} km out`} after ${hhmm(st.minutes)}, ${st.burned_ha} ha.` : "";
    try {
      await api.simComplete({ site_id: siteId, summary, actions_done: tasks.filter((t) => done[t.id]).map((t) => t.text), actions_total: tasks.length, duration_s: secs });
      setLogMsg(`Response logged: ${Object.keys(done).length} of ${tasks.length} actions in ${Math.floor(secs / 60)} min ${secs % 60} s.`);
      setPhase("logged");
    } catch (e) { setLogMsg((e as Error).message); }
  };

  const ign = lite ? fireAt(lite, cond, 0, 0).ignition : null;
  const fire: MapFire | null = st ? { perimeter: st.perimeter, front: st.front, intensity } : null;
  const mapSite = site ? [{ site_id: site.site_id, lat: site.lat, lon: site.lon, level, value_eur: site.value_eur }] : [];
  const zoom = cond.ignition_km > 5.5 ? 11.2 : cond.ignition_km > 3.5 ? 11.7 : 12.3;
  const running = phase === "running" || phase === "paused";

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div className="between wrap">
        <div>
          <div className="eyebrow">Simulation · fire reported now</div>
          <h1 className="display" style={{ fontSize: "clamp(28px,3.6vw,42px)" }}>What if a fire started right now?</h1>
          <div className="dim small" style={{ maxWidth: 720 }}>Report a fire near a site, watch it spread with the wind, and get an AI response plan built from the conditions. Nothing here touches real alerts.</div>
        </div>
        {running && (
          <div className="row" style={{ gap: 8 }}>
            <button className="btn sm ghost" onClick={() => setPhase(phase === "running" ? "paused" : "running")}>{phase === "running" ? "Pause" : "Resume"}</button>
            {[1, 2, 4].map((m) => <button key={m} className={`btn sm ${mult === m ? "primary" : "ghost"}`} onClick={() => setMult(m)}>{m}x</button>)}
            <button className="btn sm ghost" onClick={() => { setPhase("over"); }}>Stop</button>
          </div>
        )}
      </div>

      {phase === "setup" && sites && (
        <SetupPanel sites={sites} siteId={siteId} setSiteId={setSiteId} cond={cond} setCond={setCond}
          placing={placing} setPlacing={setPlacing} onStart={start} />
      )}

      <div className="sim-grid">
        <div className={`sim-map ${running && level === "CRITICAL" ? "alarm" : ""}`}>
          {st && (
            <div className="sim-hud" aria-live="polite">
              <span className="sim-pill" style={{ background: LEVEL_COLOR[level] }}>{level.toLowerCase()}</span>
              <span>T+{hhmm(st.minutes)}</span>
              <span>{st.reached ? "front at the fence" : `front ${st.front_km} km from the fence`}</span>
              {!!st.eta_min && <span>arrives in ~{st.eta_min} min</span>}
              <span>{st.burned_ha} ha</span>
              <span>head {st.head_ros_m_min} m/min</span>
            </div>
          )}
          {site && (
            <SiteMap key={`${siteId}-${zoom}`} sites={mapSite} detections={[]} sensors={nodes} fire={fire}
              marks={ign ? [{ lat: ign[1], lon: ign[0], label: "Fire reported here", color: "#FF5A1F" }] : []}
              center={[site.lon, site.lat]} zoom={zoom} height="min(62vh, 560px)" onMapClick={onMapClick} />
          )}
          {placing && <div className="sim-placing">Click the map where the fire is</div>}
          <div className="row wrap" style={{ gap: 12, marginTop: 8 }}><SensorLegend shapes={false} />
            {!sensorData?.nodes.length && <span className="small mute">No ground sensors on this site: satellites only.</span>}</div>
        </div>

        <aside className="sim-side">
          {phase === "over" && st && (
            <motion.div className="card grid" style={{ gap: 12, borderColor: "var(--ember)" }} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
              <div className="eyebrow">Simulation over</div>
              <div className="small">
                {st.reached ? <>The fire reached the fence after <b>{hhmm(st.minutes)}</b>.</> : <>The front is <b>{st.front_km} km</b> from the fence after {hhmm(st.minutes)}.</>}{" "}
                {st.burned_ha} ha burned, {counts.fire} sensors in fire, {counts.dead} lost.
              </div>
              <div className="small dim">That was the warning. Now handle it: work through the plan, action by action, as you would in the control room.</div>
              <button className="btn primary" onClick={() => { clearToasts(); setPhase("response"); setRespStart(Date.now()); }}>Start the response</button>
            </motion.div>
          )}

          {phase === "setup" ? (
            <div className="card small dim">
              <b style={{ color: "var(--text)" }}>How it works.</b> The fire spreads as an ellipse: its head runs downwind at a speed set by the vegetation, wind, heat and humidity. Sensors around the site react, the level rises, and the AI rebuilds the response plan each time the level changes.
            </div>
          ) : (
            <AIPanel advice={advice} busy={adviceBusy} err={adviceErr} level={level} />
          )}

          {(phase === "response" || phase === "logged") && (
            <div className="card grid" style={{ gap: 10 }}>
              <div className="between"><div className="eyebrow">Response checklist</div><span className="small mute">{Object.keys(done).length}/{tasks.length} done</span></div>
              <div className="meter" style={{ height: 6 }}><span style={{ width: `${tasks.length ? (Object.keys(done).length / tasks.length) * 100 : 0}%`, background: "var(--normal)" }} /></div>
              {tasks.map((t) => (
                <label key={t.id} className={`check-opt ${done[t.id] ? "on" : ""}`}>
                  <input type="checkbox" disabled={phase === "logged"} checked={!!done[t.id]}
                    onChange={() => setDone((d) => { const n = { ...d }; if (n[t.id]) delete n[t.id]; else n[t.id] = new Date().toLocaleTimeString("en-GB"); return n; })} />
                  <span style={{ flex: 1 }}>{t.text}<span className="small mute" style={{ display: "block" }}>{t.who}{done[t.id] ? ` · done at ${done[t.id]}` : ""}</span></span>
                </label>
              ))}
              <Link className="btn ghost" to={`/sites/${siteId}/handoff`} target="_blank">Open the fire-service handoff pack</Link>
              {phase === "response" && <button className="btn primary" onClick={finish}>Finish and log the response</button>}
              {logMsg && <div className="small" style={{ color: "var(--normal)" }}>{logMsg} It is in the audit log on the System page.</div>}
              {phase === "logged" && <button className="btn ghost" onClick={reset}>Run another simulation</button>}
            </div>
          )}
          {running && <button className="btn ghost sm" onClick={reset}>Cancel and set up again</button>}
        </aside>
      </div>

      <AnimatePresence>
        {warning && lite && (
          <motion.div className="sim-warning" role="alertdialog" aria-modal="true" aria-labelledby="sim-warning-title"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setWarning(false)}>
            <motion.div className="sim-warning-card" initial={{ scale: 0.92 }} animate={{ scale: 1 }} exit={{ scale: 0.96 }} onClick={(e) => e.stopPropagation()}>
              <div className="sim-warning-tag">Simulation · not a real fire</div>
              <h2 id="sim-warning-title">Fire reported near {lite.name}</h2>
              <p>{cond.ignition_km} km {compass(cond.ignition_bearing_deg)} of the site. Wind {cond.wind_kmh} km/h from {compass(cond.wind_from_deg)}, {cond.temp_c} °C, {cond.rh_pct} % humidity, {FUEL_LABEL[cond.fuel].toLowerCase()}.</p>
              <p className="dim">Watch it spread. The AI is preparing the response plan.</p>
              <button className="btn primary" autoFocus onClick={() => setWarning(false)}>Go to the map</button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div></div>
  );
}

function SetupPanel({ sites, siteId, setSiteId, cond, setCond, placing, setPlacing, onStart }: {
  sites: Site[]; siteId: string; setSiteId: (s: string) => void; cond: Conditions; setCond: (f: (c: Conditions) => Conditions) => void;
  placing: boolean; setPlacing: (b: boolean) => void; onStart: () => void;
}) {
  const set = <K extends keyof Conditions>(k: K, v: Conditions[K]) => setCond((c) => ({ ...c, [k]: v }));
  const slider = (k: "wind_kmh" | "temp_c" | "rh_pct", label: string, min: number, max: number, unit: string) => (
    <div><label htmlFor={`sim-${k}`}>{label}: <b style={{ color: "var(--text)" }}>{cond[k]} {unit}</b></label>
      <input id={`sim-${k}`} type="range" min={min} max={max} value={cond[k]} onChange={(e) => set(k, Number(e.target.value))} /></div>
  );
  return (
    <div className="card grid" style={{ gap: 14 }}>
      <div className="sim-setup">
        <div><label>Site</label>
          <select value={siteId} onChange={(e) => setSiteId(e.target.value)}>{sites.map((s) => <option key={s.site_id} value={s.site_id}>{s.name}</option>)}</select></div>
        {slider("wind_kmh", "Wind", 0, 60, "km/h")}
        <div><label>Wind from: <b style={{ color: "var(--text)" }}>{compass(cond.wind_from_deg)}</b></label>
          <input type="range" min={0} max={359} step={22.5} value={cond.wind_from_deg} onChange={(e) => set("wind_from_deg", Number(e.target.value))} /></div>
        {slider("temp_c", "Temperature", 15, 45, "°C")}
        {slider("rh_pct", "Humidity", 5, 70, "%")}
        <div><label>Vegetation</label>
          <select value={cond.fuel} onChange={(e) => set("fuel", e.target.value as FuelClass)}>
            {(Object.keys(FUEL_LABEL) as FuelClass[]).map((f) => <option key={f} value={f}>{FUEL_LABEL[f]}</option>)}</select></div>
      </div>
      <div className="between wrap" style={{ gap: 12 }}>
        <div className="small dim">Fire reported <b style={{ color: "var(--text)" }}>{cond.ignition_km} km {compass(cond.ignition_bearing_deg)}</b> of the site.{" "}
          <button className="link small" style={{ background: "none", border: 0, padding: 0, cursor: "pointer" }} onClick={() => setPlacing(!placing)}>{placing ? "Cancel" : "Place it on the map"}</button></div>
        <div className="row" style={{ gap: 8 }}>
          <button className="btn ghost" onClick={() => setCond(() => randomConditions())}>Random conditions</button>
          <button className="btn primary sim-report" onClick={onStart}>Report a fire</button>
        </div>
      </div>
    </div>
  );
}

function AIPanel({ advice, busy, err, level }: { advice: SimAdvice | null; busy: boolean; err: string; level: Level }) {
  return (
    <div className="card grid" style={{ gap: 12 }}>
      <div className="between">
        <div className="eyebrow">AI response plan</div>
        {advice && <span className="small mute">{advice.generated_by === "template" ? "rule-based" : advice.model}</span>}
      </div>
      {busy && <div className="small dim row" style={{ gap: 8 }}><span className="spinner" /> Building the plan for level {level.toLowerCase()}…</div>}
      {err && <div className="small" style={{ color: "var(--critical-hot)" }}>{err}</div>}
      {advice && (
        <>
          <ol className="sim-plan">
            {advice.suggestions.map((s) => (
              <li key={s.suggestion_id}>
                <div className="row" style={{ gap: 8, alignItems: "baseline" }}>
                  <b>{s.title}</b>
                </div>
                <div className="small dim">{s.detail}</div>
                <div className="small mute">{AUDIENCE[s.audience]} · priority {s.priority}</div>
              </li>
            ))}
          </ol>
          <div className="row wrap" style={{ gap: 6 }}>
            {Object.entries(advice.access_routes).map(([k, v]) => (
              <span key={k} className={`chip ${v === "potentially_exposed" ? "assumed" : "observed"}`}>{k}: {v === "potentially_exposed" ? "faces the fire" : "clear"}</span>
            ))}
            <LevelBadge level={level} />
          </div>
          <div className="small mute">{advice.disclaimer}</div>
        </>
      )}
    </div>
  );
}
