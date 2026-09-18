import { useState } from "react";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { AdminOnly } from "../components/RouteGuards";
import { Reveal } from "../components/Reveal";
import { SITES } from "../api/engine";
import { eur, SITE_TYPE_LABEL } from "../api/levels";
import type { ImportReport } from "../api/types";

const HEADER = "site_id,name,type,lat,lon,radius_m,value_eur,fuel_class,personnel_on_site,primary_access_bearing_deg,criticality";

function sampleCsv() {
  const rows = SITES.map((s) => [s.site_id, s.name, s.type, s.lat, s.lon, s.radius_m, s.value_eur, s.fuel_class, s.personnel_on_site, s.primary_access_bearing_deg, s.criticality].join(","));
  return [HEADER, ...rows].join("\n");
}

export function AssetsPage() {
  const { data: sites } = useAsync(() => api.getSites(), []);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [err, setErr] = useState("");

  const download = () => {
    const blob = new Blob([sampleCsv()], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "sample_assets.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  const onFile = async (f: File) => {
    if (!confirm("This replaces your portfolio. Continue?")) return;
    setErr(""); setReport(null);
    try { setReport(await api.importAssets(await f.text())); }
    catch (e) { setErr((e as Error).message); }
  };

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div className="between wrap">
        <div><div className="eyebrow">Assets</div><h1 className="display" style={{ fontSize: "clamp(28px,3.6vw,42px)" }}>Portfolio</h1></div>
        <button className="btn" onClick={download}>Download sample CSV</button>
      </div>

      <AdminOnly>
        <Reveal>
          <div className="card">
            <div className="between wrap">
              <div><div style={{ fontWeight: 600 }}>Import assets</div><div className="small mute">CSV / GeoJSON · replaces the portfolio · demo import is simulated</div></div>
              <label className="btn primary" style={{ cursor: "pointer" }}>
                Choose file
                <input type="file" accept=".csv,.geojson,.json" style={{ display: "none" }} onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
              </label>
            </div>
            {err && <div style={{ color: "var(--critical-hot)", marginTop: 12 }} className="small">Import failed: {err}</div>}
            {report && (
              <div style={{ marginTop: 14 }}>
                <div className="row" style={{ gap: 10 }}><span className="chip observed">{report.accepted} accepted</span>{report.rejected.length > 0 && <span className="chip assumed">{report.rejected.length} rejected</span>}</div>
                {report.rejected.map((r) => <div key={r.row} className="small mute" style={{ marginTop: 6 }}>row {r.row} {r.site_id ? `(${r.site_id})` : ""}: {r.reason}</div>)}
              </div>
            )}
          </div>
        </Reveal>
      </AdminOnly>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table>
          <thead><tr><th>Site</th><th>Type</th><th>Value</th><th>Fuel</th><th>Personnel</th><th>Criticality</th></tr></thead>
          <tbody>
            {sites?.map((s) => (
              <tr key={s.site_id}>
                <td><div style={{ fontWeight: 600 }}>{s.name}</div><div className="mono small mute">{s.site_id}</div></td>
                <td className="small">{SITE_TYPE_LABEL[s.type]}</td>
                <td className="mono small">{eur(s.value_eur)}</td>
                <td><span className="chip">{s.fuel_class}</span></td>
                <td className="mono small">{s.personnel_on_site}</td>
                <td className="mono small">{s.criticality}/5</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div></div>
  );
}
