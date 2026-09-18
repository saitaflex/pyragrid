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
import { MeshCounts, SensorEventList, SensorLegend } from "../components/Sensors";

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

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div className="between wrap">
        <div>
          <div className="eyebrow">Ground sensors · optional</div>
          <h1 className="display" style={{ fontSize: "clamp(28px,3.6vw,42px)" }}>Hexagonal sensor mesh</h1>
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
          <SiteMap key={focus ?? "all"} sites={sit?.sites ?? []} detections={dets ?? []} sensors={nodes}
            center={focused ? [focused.lon, focused.lat] : undefined} zoom={focused ? 12.2 : undefined}
            onSelect={(id) => setFocus(data?.meshes.some((m) => m.site_id === id) ? id : focus)} height={520} />
          <div className="small mute">Click a hexagon for its reading. Click a site to zoom into its mesh. Orange dots are satellite detections.</div>
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
          <thead><tr><th>Site</th><th>Mesh</th><th>Status now</th><th>Ground fire</th><th></th></tr></thead>
          <tbody>
            {data?.meshes.map((m) => (
              <tr key={m.site_id} style={{ cursor: "pointer", background: m.site_id === focus ? "var(--panel-2)" : undefined }} onClick={() => setFocus(m.site_id)}>
                <td>{m.site_name}<div className="small mute mono">{m.site_id}</div></td>
                <td className="small dim">{m.nodes} nodes · every {m.spacing_m} m · {(m.coverage_m / 1000).toFixed(1)} km radius</td>
                <td><MeshCounts mesh={m} /></td>
                <td>{m.ground_fire ? <span className="chip" style={{ borderColor: "var(--critical-hot)", color: "var(--critical-hot)" }}>confirmed on the ground</span> : <span className="dim small">no</span>}</td>
                <td onClick={(e) => e.stopPropagation()}>{staff && <Link className="link small" to={`/sites/${m.site_id}`}>Site →</Link>}</td>
              </tr>
            ))}
            {data && data.meshes.length === 0 && <tr><td colSpan={5} className="dim small" style={{ padding: 24, textAlign: "center" }}>No sensor mesh installed yet. Admins can install one from a site page.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="card grid" style={{ gap: 12 }}>
        <div className="eyebrow">How the mesh works</div>
        <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          {[
            ["1 · Layout", "Nodes are placed on a hexagonal grid: 3 rings, 37 nodes, covering the site plus a buffer (at least 1 km). Every node has 6 equidistant neighbours, so one lost node leaves no blind corridor."],
            ["2 · Sensing", "Each node reports temperature, battery and a tilt switch. Warm at 45°C, Fire at 65°C. Silence means it died (burned or out of battery); a tilt alarm means it was moved or knocked over."],
            ["3 · Transport", "Low-power radio (e.g. LoRaWAN) to a gateway on site, then to the Engine's ingest API. In this demo the readings are simulated from the same satellite detections the engine scores."],
            ["4 · Use", "Sensors confirm or rule out satellite hotspots, see fire at night or under cloud, and show which side of the site is burning. Fire service, civil protection and NGOs can see the mesh through their shared view."],
          ].map(([t, d]) => <div key={t}><div style={{ fontWeight: 700, marginBottom: 6 }}>{t}</div><div className="small dim">{d}</div></div>)}
        </div>
      </div>
    </div></div>
  );
}
