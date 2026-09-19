import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { STAFF_ROLES } from "../api/types";
import { useTime } from "../state/TimeContext";
import { useAuth } from "../state/AuthContext";
import { useAsync } from "../hooks/useAsync";
import { TimeSlider } from "../components/TimeSlider";
import { SiteMap } from "../components/SiteMap";
import { StatTile } from "../components/StatTile";
import { EstimateLine, MeshCounts, PlacementLine, SensorEventList, SensorLegend } from "../components/Sensors";

export function SensorsPage() {
  const { step } = useTime();
  const { user } = useAuth();
  const staff = !!user && STAFF_ROLES.includes(user.role);
  const [focus, setFocus] = useState<string | null>(null);
  const { data, error, loading } = useAsync(() => api.getSensors(step), [step]);
  const { data: sit } = useAsync(() => api.getSituation(step), [step]);
  const { data: dets } = useAsync(() => api.getDetections(step), [step]);

  const totals = useMemo(() => {
    const t = { nodes: 0, fire: 0, warm: 0, offline: 0, dropped: 0 };
    for (const m of data?.meshes ?? []) {
      t.nodes += m.nodes; t.fire += m.counts.fire; t.warm += m.counts.warm; t.offline += m.counts.offline; t.dropped += m.counts.dropped;
    }
    return t;
  }, [data]);

  const focused = data?.meshes.find((m) => m.site_id === focus);
  const nodes = focus ? (data?.nodes ?? []).filter((n) => n.site_id === focus) : data?.nodes ?? [];
  const events = focus ? (data?.events ?? []).filter((e) => e.site_id === focus) : data?.events ?? [];
  const estimates = (data?.meshes ?? []).filter((m) => m.fire_estimate && (!focus || m.site_id === focus)).map((m) => m.fire_estimate!);

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div className="between wrap">
        <div>
          <div className="eyebrow">Ground sensors · optional</div>
          <h1 className="display" style={{ fontSize: "clamp(28px,3.6vw,42px)" }}>Sensors on the ground</h1>
        </div>
        <SensorLegend />
      </div>
      <TimeSlider />
      {error && <div className="card dim">{error}</div>}
      {loading && !data && <div className="card small dim row" style={{ gap: 10 }}><span className="spinner" /> Loading sensor readings… (the first load after a quiet period takes a few seconds)</div>}

      <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
        <StatTile label="Sensors reporting fire" value={totals.fire} accent="var(--critical-hot)" hint={`of ${totals.nodes} nodes`} />
        <StatTile label="Warm" value={totals.warm} accent="var(--elevated)" hint="heat nearby" />
        <StatTile label="Offline (died)" value={totals.offline} accent="var(--text-mute)" hint="burned or no battery" />
        <StatTile label="Dropped (moved)" value={totals.dropped} accent="#4FC3F7" hint="tilt alarm" />
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1.5fr 1fr", gap: 18, alignItems: "start" }}>
        <div className="grid" style={{ gap: 10 }}>
          <SiteMap key={focus ?? "all"} sites={sit?.sites ?? []} detections={dets ?? []} sensors={nodes} estimates={estimates}
            center={focused ? [focused.lon, focused.lat] : undefined} zoom={focused ? 13 : undefined}
            onSelect={(id) => setFocus(data?.meshes.some((m) => m.site_id === id) ? id : focus)} height={520} />
          <div className="small mute">Click a sensor for its reading and where it is mounted. Click a site to zoom in. Orange dots are satellite detections; the red dashed circle is where the sensors put the fire.</div>
        </div>
        <div className="card" style={{ maxHeight: 560, overflow: "auto" }}>
          <div className="between" style={{ marginBottom: 8 }}>
            <div className="eyebrow">Sensor events {focused && `· ${focused.site_name}`}</div>
            {focus && <button className="btn sm ghost" onClick={() => setFocus(null)}>All sites</button>}
          </div>
          <SensorEventList events={events} showSite={!focus} />
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table>
          <thead><tr><th>Site</th><th>Where the sensors are</th><th>Status now</th><th>Ground fire</th><th></th></tr></thead>
          <tbody>
            {data?.meshes.map((m) => (
              <tr key={m.site_id} style={{ cursor: "pointer", background: m.site_id === focus ? "var(--panel-2)" : undefined }} onClick={() => setFocus(m.site_id)}>
                <td>{m.site_name}<div className="small mute mono">{m.site_id}</div></td>
                <td className="small"><div className="dim" style={{ marginBottom: 4 }}>{m.nodes} sensors within {(m.coverage_m / 1000).toFixed(1)} km{m.layout_source === "openstreetmap" ? " · placed on OpenStreetMap features" : " · even grid (no map features)"}</div><PlacementLine mesh={m} /></td>
                <td><MeshCounts mesh={m} /></td>
                <td style={{ maxWidth: 320 }}>{m.fire_estimate ? <EstimateLine est={m.fire_estimate} /> : <span className="dim small">no heat sensed</span>}</td>
                <td onClick={(e) => e.stopPropagation()}>{staff && <Link className="link small" to={`/sites/${m.site_id}`}>Site →</Link>}</td>
              </tr>
            ))}
            {data && data.meshes.length === 0 && <tr><td colSpan={5} className="dim small" style={{ padding: 24, textAlign: "center" }}>No sensors installed yet. Admins can install them from a site page.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="card grid" style={{ gap: 12 }}>
        <div className="eyebrow">How the mesh works</div>
        <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          {[
            ["1 · Placement", "Each sensor sits on a real place from OpenStreetMap: on the site fence, at nearby houses, cabins and farm buildings, and along forest, scrub and grassland edges where fire arrives. Open-ground points fill any gaps, covering the site plus at least 1 km around it."],
            ["2 · Sensing", "Each node reports temperature, battery and a tilt switch. Warm at 45°C, Fire at 65°C. Silence means it died (burned or out of battery); a tilt alarm means it was moved or knocked over."],
            ["3 · Transport", "Low-power radio (e.g. LoRaWAN) to a gateway on site, then to the Engine's ingest API. In this demo the readings are simulated from the same satellite detections the engine scores."],
            ["4 · Combined position", "Readings of all warm and fire sensors are combined (heat-weighted) into one estimated fire position with an uncertainty circle: more hot sensors, higher confidence. It confirms or rules out satellite hotspots, works at night and under cloud, and is shared with fire service, civil protection and NGOs."],
          ].map(([t, d]) => <div key={t}><div style={{ fontWeight: 700, marginBottom: 6 }}>{t}</div><div className="small dim">{d}</div></div>)}
        </div>
      </div>
    </div></div>
  );
}
