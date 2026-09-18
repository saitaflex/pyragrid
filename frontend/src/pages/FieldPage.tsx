import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useTime } from "../state/TimeContext";
import { useAsync } from "../hooks/useAsync";
import { LevelBadge } from "../components/LevelBadge";
import { LEVEL_COLOR, compass } from "../api/levels";

export function FieldPage() {
  const { siteId = "" } = useParams();
  const { step } = useTime();
  const { data: st } = useAsync(() => api.getSiteStatus(siteId, step), [siteId, step]);
  const secondary = st?.access_routes.find((r) => r.name === "Secondary access");

  return (
    <div className="page"><div className="container" style={{ maxWidth: 420 }}>
      <Link to={`/sites/${siteId}`} className="link small">← Site</Link>
      <div className="card" style={{ marginTop: 12, background: st ? `linear-gradient(160deg, color-mix(in srgb, ${LEVEL_COLOR[st.level]} 22%, transparent), var(--panel))` : undefined, borderColor: st ? LEVEL_COLOR[st.level] : undefined }}>
        <div className="between"><div className="eyebrow">Field card</div>{st && <LevelBadge level={st.level} score={st.score} />}</div>
        <div className="display" style={{ fontSize: 30, margin: "14px 0 4px" }}>{st?.name}</div>
        <div style={{ fontSize: 22, fontWeight: 700, marginTop: 16 }}>
          {st?.nearest_fire_km !== null && st ? `${st.nearest_fire_km!.toFixed(1)} km ${compass(st.fire_bearing_deg!)}` : "No fire within 25 km"}
        </div>
        <div className="dim" style={{ marginTop: 6 }}>{st?.wind ? `Wind ${compass(st.wind.from_deg)} → ${compass(st.wind.to_deg)}` : "Wind unknown"}</div>
        <div className="divider" />
        <div className="between"><span className="small mute">Secondary route</span><span className={`chip ${secondary?.status === "available" ? "observed" : "assumed"}`}>{secondary?.status === "available" ? "available" : "exposed"}</span></div>
        <div className="between" style={{ marginTop: 8 }}><span className="small mute">Contact</span><span className="small" style={{ fontWeight: 600 }}>Operations Centre</span></div>
      </div>
    </div></div>
  );
}
