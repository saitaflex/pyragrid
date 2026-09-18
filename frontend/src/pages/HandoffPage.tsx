import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useTime } from "../state/TimeContext";
import { useAsync } from "../hooks/useAsync";
import { LevelBadge } from "../components/LevelBadge";
import { fmtTime } from "../api/levels";
import type { HandoffPack } from "../api/types";

function asText(p: HandoffPack): string {
  return [
    `HANDOFF PACK — ${p.site_name} (${p.site_id})`,
    `Level ${p.level} (score ${p.score}) — ${p.headline}`,
    `Location ${p.lat}, ${p.lon} — personnel ${p.personnel_on_site} — criticality ${p.criticality}/5`,
    ``, `Access routes:`, ...p.access_routes.map((r) => `  - ${r.name}: ${r.status} (bearing ${r.bearing_deg}°)`),
    ``, `Hazards:`, ...p.hazards.map((h) => `  - ${h.name} [${h.kind}]: ${h.note}`),
    ``, `Water points:`, ...p.water_points.map((w) => `  - ${w.name}: ${w.capacity_m3} m³ at ${w.lat}, ${w.lon}`),
    ``, `Contact: ${p.contact.role} ${p.contact.phone}`,
    ``, p.disclaimer,
  ].join("\n");
}

export function HandoffPage() {
  const { siteId = "" } = useParams();
  const { step } = useTime();
  const { data: p } = useAsync(() => api.getHandoff(siteId, step), [siteId, step]);

  return (
    <div className="page"><div className="container" style={{ maxWidth: 820 }}>
      <div className="between wrap no-print" style={{ marginBottom: 16 }}>
        <Link to={`/sites/${siteId}`} className="link small">← Site</Link>
        <div className="row" style={{ gap: 8 }}>
          <button className="btn sm ghost" onClick={() => p && navigator.clipboard.writeText(asText(p))}>Copy as text</button>
          <button className="btn sm primary" onClick={() => window.print()}>Print</button>
        </div>
      </div>

      {p && (
        <div className="card pad-lg print-sheet" style={{ background: "#fff", color: "#111" }}>
          <div className="between" style={{ borderBottom: "2px solid #111", paddingBottom: 12 }}>
            <div><div style={{ fontFamily: "var(--display)", fontSize: 24, fontWeight: 800 }}>{p.site_name}</div><div style={{ color: "#555", fontSize: 13 }}>{p.site_id} · {p.type.replace("_", " ")} · generated {fmtTime(p.generated_at)}</div></div>
            <div style={{ textAlign: "right" }}><LevelBadge level={p.level} score={p.score} /><div style={{ fontSize: 13, marginTop: 4, color: "#333" }}>{p.headline}</div></div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, margin: "16px 0" }}>
            {[["Location", `${p.lat}, ${p.lon}`], ["Personnel", String(p.personnel_on_site)], ["Criticality", `${p.criticality}/5`], ["Contact", p.contact.phone]].map(([k, v]) => (
              <div key={k}><div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#888" }}>{k}</div><div style={{ fontWeight: 600 }}>{v}</div></div>
            ))}
          </div>

          <Section title="Access routes">
            {p.access_routes.map((r) => <Line key={r.name} a={r.name} b={`${r.status} · bearing ${r.bearing_deg}°`} />)}
          </Section>
          <Section title="Hazards">
            {p.hazards.map((h) => <div key={h.name} style={{ padding: "6px 0", borderBottom: "1px solid #eee" }}><b>{h.name}</b> <span style={{ color: "#888", fontSize: 12 }}>[{h.kind}]</span><div style={{ fontSize: 13, color: "#444" }}>{h.note}</div></div>)}
          </Section>
          <Section title="Water points (simulated)">
            {p.water_points.map((w) => <Line key={w.name} a={w.name} b={`${w.capacity_m3} m³ · ${w.lat}, ${w.lon}`} />)}
          </Section>
          <Section title="Contact"><Line a={p.contact.role} b={p.contact.phone} /></Section>

          <div style={{ marginTop: 16, fontSize: 12, fontStyle: "italic", color: "#666", borderTop: "1px solid #ddd", paddingTop: 12 }}>{p.disclaimer}</div>
        </div>
      )}
    </div></div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <div style={{ marginTop: 14 }}><div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.1em", color: "#c0392b", fontWeight: 700, marginBottom: 6 }}>{title}</div>{children}</div>;
}
function Line({ a, b }: { a: string; b: string }) {
  return <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #eee", fontSize: 14 }}><span>{a}</span><span style={{ color: "#444" }}>{b}</span></div>;
}
