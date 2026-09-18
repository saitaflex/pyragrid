import { Link, useParams } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, ReferenceLine, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "../api/client";
import { useTime } from "../state/TimeContext";
import { useAsync } from "../hooks/useAsync";
import { TimeSlider } from "../components/TimeSlider";
import { SiteMap } from "../components/SiteMap";
import { FactorBars } from "../components/FactorBars";
import { LevelBadge } from "../components/LevelBadge";
import { Reveal } from "../components/Reveal";
import { LEVEL_COLOR, SITE_TYPE_LABEL, compass, eur, fmtTime } from "../api/levels";

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return <div><div className="small mute" style={{ marginBottom: 3 }}>{label}</div><div style={{ fontWeight: 600 }}>{value}</div></div>;
}

export function SitePage() {
  const { siteId = "" } = useParams();
  const { step } = useTime();
  const { data: st, error } = useAsync(() => api.getSiteStatus(siteId, step), [siteId, step]);
  const { data: tl } = useAsync(() => api.getTimeline(siteId), [siteId]);
  const { data: dets } = useAsync(() => api.getDetections(step), [step]);

  if (error) return <div className="page"><div className="container"><div className="card">Site not found.</div></div></div>;

  const chart = (tl ?? []).map((p, i) => ({ i, score: p.score }));

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div className="between wrap">
        <div>
          <Link to="/" className="link small">← Portfolio</Link>
          <h1 className="display" style={{ fontSize: "clamp(26px,3.4vw,40px)", marginTop: 6 }}>{st?.name ?? "…"}</h1>
          <div className="dim small">{st && SITE_TYPE_LABEL[st.type]} · {st && eur(st.value_eur)} · criticality {st?.criticality}/5</div>
        </div>
        <div className="row" style={{ gap: 10 }}>
          {st && <LevelBadge level={st.level} score={st.score} />}
          <Link className="btn sm ghost" to={`/field/${siteId}`}>Field view</Link>
          <Link className="btn sm" to={`/sites/${siteId}/handoff`}>Handoff pack</Link>
        </div>
      </div>

      <TimeSlider />

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 18, alignItems: "start" }}>
        <Reveal>
          <div className="card"><div className="eyebrow" style={{ marginBottom: 12 }}>Why this score</div>
            {st && <FactorBars factors={st.factors} statuses={st.factor_status} />}
          </div>
        </Reveal>
        <Reveal delay={0.05}>
          {st && <SiteMap sites={[st]} detections={dets ?? []} center={[st.lon, st.lat]} zoom={11} height={300} />}
          <div className="card" style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Field label="Threat" value={st?.nearest_fire_km !== null && st ? `Fire ${st.nearest_fire_km!.toFixed(1)} km ${compass(st.fire_bearing_deg!)}` : "No fire within 25 km"} />
            <Field label="Fire moving toward site" value={st?.fire_moving_toward_site === null ? "Unknown" : st?.fire_moving_toward_site ? "Yes" : "No"} />
            <Field label="Weather" value={st?.weather ? `${st.weather.temp_c}°C · ${st.weather.rh_pct}% RH` : "Weather unknown"} />
            <Field label="Wind" value={st?.wind ? `${st.wind.speed_kmh} km/h from ${compass(st.wind.from_deg)}` : "Unknown"} />
            <Field label="Personnel on site" value={st?.personnel_on_site} />
            <Field label="Triggering detection" value={<span className="mono small">{st?.triggering_detection_id ?? "—"}</span>} />
          </div>
        </Reveal>
      </div>

      <Reveal>
        <div className="card"><div className="eyebrow" style={{ marginBottom: 10 }}>Score timeline · 0–100</div>
          <ResponsiveContainer width="100%" height={210}>
            <LineChart data={chart} margin={{ top: 6, right: 10, bottom: 0, left: -18 }}>
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 100]} tick={{ fill: "var(--text-mute)", fontSize: 11 }} />
              <ReferenceLine y={25} stroke={LEVEL_COLOR.NORMAL} strokeDasharray="3 3" strokeOpacity={0.4} />
              <ReferenceLine y={50} stroke={LEVEL_COLOR.ELEVATED} strokeDasharray="3 3" strokeOpacity={0.4} />
              <ReferenceLine y={75} stroke={LEVEL_COLOR.HIGH} strokeDasharray="3 3" strokeOpacity={0.4} />
              <ReferenceLine x={step} stroke="var(--ember-2)" strokeWidth={2} />
              <Tooltip contentStyle={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} labelFormatter={() => ""} />
              <Line type="monotone" dataKey="score" stroke="var(--ember)" strokeWidth={2.5} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Reveal>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 18 }}>
        <Reveal>
          <div className="card"><div className="eyebrow" style={{ marginBottom: 12 }}>SOP actions · current rules</div>
            {st?.sop_actions.length ? (
              <ul style={{ listStyle: "none", display: "grid", gap: 8 }}>
                {st.sop_actions.map((a, i) => <li key={i} className="row" style={{ gap: 10, alignItems: "flex-start" }}><span style={{ color: "var(--ember-2)" }}>▸</span><span className="small">{a}</span></li>)}
              </ul>
            ) : <div className="dim small">No SOP actions at this level.</div>}
          </div>
        </Reveal>
        <Reveal delay={0.05}>
          <div className="card"><div className="eyebrow" style={{ marginBottom: 12 }}>Access & exposed components</div>
            <div className="row wrap" style={{ gap: 8, marginBottom: 14 }}>
              {st?.access_routes.map((r) => (
                <span key={r.name} className={`chip ${r.status === "potentially_exposed" ? "assumed" : "observed"}`}>{r.name}: {r.status === "potentially_exposed" ? "exposed" : "available"}</span>
              ))}
            </div>
            {st?.exposed_components.length ? st.exposed_components.map((c) => (
              <div key={c.name} className="between" style={{ padding: "7px 0", borderBottom: "1px solid var(--border)" }}><span className="small">{c.name}</span><span className="mono small">{eur(c.value_eur)}</span></div>
            )) : <div className="dim small">No exposed components at this level.</div>}
          </div>
        </Reveal>
      </div>
      {st && <div className="small mute">Snapshot at {fmtTime(fmtIso(step))}</div>}
    </div></div>
  );
}

import { stepIso } from "../api/engine";
function fmtIso(step: number) { return stepIso(step); }
