import { useState } from "react";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";

/** Fire spread estimate for one site.
 *
 *  Deliberately reads as an estimate, not a prediction: the arrival time is prefixed with a
 *  tilde, the confidence sentence sits directly beside it rather than in a tooltip, and the
 *  assumptions are one click away on the same card. A number this operationally loaded should
 *  never appear without the caveat attached to it.
 */
export function ForecastPanel({ siteId, step }: { siteId: string; step: number }) {
  const { data: f, error } = useAsync(() => api.getForecast(siteId, step), [siteId, step]);
  const [showWhy, setShowWhy] = useState(false);

  // 404 is the normal answer when no fire is in range — say so plainly, don't look broken
  if (error) {
    return (
      <div className="card">
        <div className="eyebrow">Spread forecast</div>
        <div className="dim small" style={{ marginTop: 8 }}>
          No fire within range of this site, so there is nothing to project.
        </div>
      </div>
    );
  }
  if (!f) return <div className="card"><div className="eyebrow">Spread forecast</div></div>;

  const arrival = f.hours_to_arrival;
  const urgent = arrival !== null && arrival <= 6;

  return (
    <div className="card" style={{ borderColor: urgent ? "color-mix(in srgb, var(--ember) 40%, var(--border))" : undefined }}>
      <div className="between wrap">
        <div>
          <div className="eyebrow">Spread forecast · estimate, not a prediction</div>
          <div className="dim small" style={{ marginTop: 4 }}>{f.fuel_model}</div>
        </div>
        <button className="btn sm ghost" onClick={() => setShowWhy((v) => !v)}>
          {showWhy ? "Hide assumptions" : `Assumptions (${f.assumptions.length})`}
        </button>
      </div>

      <div className="row wrap" style={{ gap: 28, marginTop: 16, alignItems: "flex-end" }}>
        <div>
          <div className="kpi" style={{ color: urgent ? "var(--ember-2)" : "var(--text)" }}>
            {arrival === null ? "—" : `~${arrival.toFixed(1)} h`}
          </div>
          <div className="mute small">until the front reaches the site</div>
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 20 }}>{f.ros_toward_site_m_h} m/h</div>
          <div className="mute small">toward this site ({f.ros_head_m_h} m/h downwind)</div>
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 20 }}>{f.distance_km} km</div>
          <div className="mute small">nearest detection, bearing {f.bearing_from_fire}°</div>
        </div>
      </div>

      <div className="small" style={{ marginTop: 14, color: urgent ? "var(--ember-2)" : "var(--text-dim)" }}>
        {f.arrival_confidence}
      </div>

      {f.front_positions.some((p) => p.reaches_site) && (
        <div className="row wrap" style={{ gap: 8, marginTop: 12 }}>
          {f.front_positions.map((p) => (
            <span key={p.hours_ahead} className={`chip ${p.reaches_site ? "assumed" : ""}`}>
              +{p.hours_ahead}h {p.travel_km} km{p.reaches_site ? " · at the site" : ""}
            </span>
          ))}
        </div>
      )}

      {showWhy && (
        <div style={{ marginTop: 16 }}>
          <div className="divider" />
          <div className="small dim" style={{ marginBottom: 8 }}>{f.method}</div>
          <ul className="small dim" style={{ paddingLeft: 18, display: "grid", gap: 6 }}>
            {f.assumptions.map((a) => <li key={a}>{a}</li>)}
          </ul>
          <div className="small mute" style={{ marginTop: 12 }}>{f.disclaimer}</div>
        </div>
      )}
    </div>
  );
}
