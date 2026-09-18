import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useTime } from "../state/TimeContext";
import { useAsync } from "../hooks/useAsync";
import { FactorBars } from "../components/FactorBars";
import { LevelBadge } from "../components/LevelBadge";
import { AdvisorPanel } from "../components/AdvisorPanel";
import { Reveal } from "../components/Reveal";
import { LEVEL_COLOR } from "../api/levels";

export function IncidentPage() {
  const { incidentId = "" } = useParams();
  const { step } = useTime();
  const { data: inc, error } = useAsync(() => api.getIncident(incidentId, step), [incidentId, step]);
  const { data: st } = useAsync(() => (inc ? api.getSiteStatus(inc.site_id, step) : Promise.resolve(undefined)), [inc?.site_id, step]);
  const [done, setDone] = useState<Set<string>>(new Set());
  const toggle = (a: string) => setDone((s) => { const n = new Set(s); n.has(a) ? n.delete(a) : n.add(a); return n; });

  if (error) return <div className="page"><div className="container"><div className="card">Incident not found.</div></div></div>;

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      {inc && (
        <div className={`card lv-${inc.level}`} style={{ borderLeft: "4px solid var(--lv)", background: `linear-gradient(120deg, color-mix(in srgb, ${LEVEL_COLOR[inc.level]} 14%, transparent), var(--panel))` }}>
          <div className="between wrap">
            <div>
              <Link to="/" className="link small">← Portfolio</Link>
              <h1 className="display" style={{ fontSize: "clamp(24px,3.2vw,38px)", marginTop: 6 }}>{inc.site_name}</h1>
              <div className="dim">{inc.headline}</div>
            </div>
            <div className="row" style={{ gap: 10 }}>
              <LevelBadge level={inc.level} score={inc.score} />
              <Link className="btn sm" to={`/sites/${inc.site_id}/handoff`}>Handoff pack</Link>
            </div>
          </div>
        </div>
      )}

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 18, alignItems: "start" }}>
        <Reveal>
          <div className="card"><div className="eyebrow" style={{ marginBottom: 12 }}>Why · factors</div>
            {st && <FactorBars factors={st.factors} statuses={st.factor_status} />}
          </div>
        </Reveal>
        <Reveal delay={0.05}>
          <div className="card"><div className="eyebrow" style={{ marginBottom: 12 }}>Action · protocol</div>
            <div className="grid" style={{ gap: 8 }}>
              {inc?.actions.map((a) => (
                <label key={a} className="row" style={{ gap: 10, cursor: "pointer", alignItems: "flex-start" }}>
                  <input type="checkbox" checked={done.has(a)} onChange={() => toggle(a)} style={{ width: 16, height: 16, marginTop: 2, accentColor: "var(--ember)" }} />
                  <span className="small" style={{ textDecoration: done.has(a) ? "line-through" : "none", color: done.has(a) ? "var(--text-mute)" : "var(--text)" }}>{a}</span>
                </label>
              ))}
            </div>
            <div className="small mute" style={{ marginTop: 14, fontStyle: "italic" }}>{inc?.disclaimer}</div>
          </div>
        </Reveal>
      </div>

      {inc && <Reveal><AdvisorPanel incidentId={inc.incident_id} siteId={inc.site_id} atStep={step} /></Reveal>}
    </div></div>
  );
}
