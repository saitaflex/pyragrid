import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "../api/client";
import { useTime } from "../state/TimeContext";
import { useAsync } from "../hooks/useAsync";
import { TimeSlider } from "../components/TimeSlider";
import { SiteMap } from "../components/SiteMap";
import { StatTile } from "../components/StatTile";
import { LevelBadge } from "../components/LevelBadge";
import { Reveal } from "../components/Reveal";
import { eur, SITE_TYPE_LABEL } from "../api/levels";

export function PortfolioPage() {
  const { step } = useTime();
  const nav = useNavigate();
  const { data: pf } = useAsync(() => api.getPortfolio(step), [step]);
  const { data: dets } = useAsync(() => api.getDetections(step), [step]);
  const { data: incidents } = useAsync(() => api.getIncidents(step), [step]);
  const { data: unack } = useAsync(() => api.getAlerts(step, "unacknowledged"), [step]);

  return (
    <div className="page">
      <div className="container grid" style={{ gap: 18 }}>
        <div className="between wrap">
          <div>
            <div className="eyebrow">Portfolio</div>
            <h1 className="display" style={{ fontSize: "clamp(30px,4vw,46px)" }}>Operations overview</h1>
          </div>
          {unack && unack.length > 0 && (
            <button className="btn" onClick={() => nav("/alerts")} style={{ borderColor: "var(--high)" }}>
              <span className="badge lv-HIGH HIGH"><span className="dot" />{unack.length}</span> unacknowledged
            </button>
          )}
        </div>

        <TimeSlider />

        <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
          <StatTile label="Critical" value={pf?.counts.CRITICAL ?? 0} accent="var(--critical-hot)" hint="sites" />
          <StatTile label="High" value={pf?.counts.HIGH ?? 0} accent="var(--high)" hint="sites" />
          <StatTile label="Exposed value" value={Math.round((pf?.total_exposed_value_eur ?? 0) / 1_000_000)} suffix="M€" accent="var(--ember)" hint="HIGH + CRITICAL" />
          <StatTile label="Sites" value={pf?.sites.length ?? 0} hint="in portfolio" />
        </div>

        <div className="grid" style={{ gridTemplateColumns: "1.55fr 1fr", gap: 18, alignItems: "start" }} >
          <Reveal>
            <SiteMap sites={pf?.sites ?? []} detections={dets ?? []} onSelect={(id) => nav(`/sites/${id}`)} height={520} />
          </Reveal>
          <Reveal delay={0.1}>
            <div className="card" style={{ padding: 0, maxHeight: 520, overflow: "auto" }}>
              <div className="between" style={{ padding: "16px 18px", position: "sticky", top: 0, background: "var(--bg-1)", borderBottom: "1px solid var(--border)", zIndex: 1 }}>
                <span className="eyebrow">Ranked exposure</span>
                <span className="small mute">API order</span>
              </div>
              {pf?.sites.map((s, i) => (
                <motion.button key={s.site_id} onClick={() => nav(`/sites/${s.site_id}`)}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.02 }}
                  className={`row lv-${s.level}`} style={{ width: "100%", textAlign: "left", justifyContent: "space-between", padding: "13px 18px", borderBottom: "1px solid var(--border)", background: "transparent", borderLeft: "3px solid var(--lv)" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{s.name}</div>
                    <div className="small mute">{SITE_TYPE_LABEL[s.type]} · {eur(s.value_eur)}{s.nearest_fire_km !== null ? ` · fire ${s.nearest_fire_km.toFixed(1)}km` : ""}</div>
                  </div>
                  <LevelBadge level={s.level} score={s.score} />
                </motion.button>
              ))}
            </div>
          </Reveal>
        </div>

        {incidents && incidents.length > 0 && (
          <Reveal>
            <div className="card">
              <div className="eyebrow" style={{ marginBottom: 12 }}>Open incidents</div>
              <div className="row wrap" style={{ gap: 10 }}>
                {incidents.map((inc) => (
                  <button key={inc.incident_id} className={`card hover lv-${inc.level}`} onClick={() => nav(`/incidents/${inc.incident_id}`)}
                    style={{ borderLeft: "3px solid var(--lv)", padding: "12px 16px", background: "var(--bg-1)", minWidth: 240 }}>
                    <div className="between" style={{ gap: 12 }}><span style={{ fontWeight: 600 }}>{inc.site_name}</span><LevelBadge level={inc.level} score={inc.score} /></div>
                    <div className="small mute" style={{ marginTop: 4 }}>{inc.headline}</div>
                  </button>
                ))}
              </div>
            </div>
          </Reveal>
        )}
      </div>
    </div>
  );
}
