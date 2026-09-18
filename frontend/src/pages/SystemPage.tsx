import { api } from "../api/client";
import { useTime } from "../state/TimeContext";
import { useAsync } from "../hooks/useAsync";
import { AdminOnly } from "../components/RouteGuards";
import { Reveal } from "../components/Reveal";
import { fmtTime } from "../api/levels";

export function SystemPage() {
  const { step } = useTime();
  const { data: sources } = useAsync(() => api.getSources(), []);
  const { data: runs } = useAsync(() => api.getIngestionRuns(), []);
  const { data: outbox } = useAsync(() => api.getOutbox(step), [step]);
  const { data: audit } = useAsync(() => api.getAudit(), [step]);
  const { data: decisions } = useAsync(() => api.getDecisions(), [step]);

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div><div className="eyebrow">System</div><h1 className="display" style={{ fontSize: "clamp(28px,3.6vw,42px)" }}>Sources & audit</h1></div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 18, alignItems: "start" }}>
        <Reveal>
          <div className="card"><div className="eyebrow" style={{ marginBottom: 12 }}>Data sources</div>
            {sources?.map((s) => (
              <div key={s.name} className="between" style={{ padding: "11px 0", borderBottom: "1px solid var(--border)" }}>
                <div className="row" style={{ gap: 10 }}>
                  <span style={{ width: 9, height: 9, borderRadius: "50%", background: "currentColor" }} className={`state-${s.state}`} />
                  <div><div style={{ fontWeight: 600 }}>{s.name}</div><div className="small mute">{s.detail}</div></div>
                </div>
                <span className={`chip state-${s.state}`} style={{ borderColor: "currentColor" }}>{s.state}</span>
              </div>
            ))}
          </div>
        </Reveal>
        <Reveal delay={0.05}>
          <div className="card"><div className="eyebrow" style={{ marginBottom: 12 }}>Email outbox · at this time</div>
            {outbox?.length ? outbox.map((m) => (
              <div key={m.alert_id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                <div className="row between"><span className="small" style={{ fontWeight: 600 }}>{m.subject}</span><span className="chip assumed">{m.status}</span></div>
                <div className="small mute" style={{ marginTop: 4 }}>{m.to}</div>
              </div>
            )) : <div className="dim small">No outbox emails yet.</div>}
          </div>
        </Reveal>
      </div>

      <Reveal>
        <div className="card"><div className="eyebrow" style={{ marginBottom: 12 }}>Ingestion runs</div>
          <table><thead><tr><th>Run</th><th>Source</th><th>Received</th><th>Inserted</th><th>Rejected</th></tr></thead>
            <tbody>{runs?.map((r) => <tr key={r.run_id}><td className="mono small">{r.run_id}</td><td className="small">{r.source}</td><td className="mono small">{r.records_received}</td><td className="mono small">{r.records_inserted}</td><td className="mono small">{r.records_rejected}</td></tr>)}</tbody>
          </table>
        </div>
      </Reveal>

      <AdminOnly fallback={<div className="card dim small">Audit log and AI decisions are visible to admins only.</div>}>
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 18, alignItems: "start" }}>
          <Reveal>
            <div className="card" style={{ maxHeight: 360, overflow: "auto" }}><div className="eyebrow" style={{ marginBottom: 12 }}>Audit log</div>
              {audit?.map((e) => (
                <div key={e.id} className="row between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)", gap: 10 }}>
                  <span className="small"><span className="chip" style={{ marginRight: 8 }}>{e.action}</span>{e.details}</span>
                  <span className="mono small mute" style={{ whiteSpace: "nowrap" }}>{e.actor}</span>
                </div>
              ))}
            </div>
          </Reveal>
          <Reveal delay={0.05}>
            <div className="card" style={{ maxHeight: 360, overflow: "auto" }}>
              <div className="eyebrow">AI decisions</div>
              <div className="small mute" style={{ margin: "4px 0 12px" }}>Human decisions on AI suggestions: our learning dataset</div>
              {decisions?.length ? decisions.map((d) => (
                <div key={d.suggestion_id} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                  <div className="row between"><span className="small" style={{ fontWeight: 600 }}>{d.title}</span><span className={`chip ${d.decision === "approved" ? "observed" : "unknown"}`}>{d.decision}</span></div>
                  <div className="small mute">{d.decided_by} · {fmtTime(d.decided_at)}</div>
                </div>
              )) : <div className="dim small">No decisions yet. Approve or reject an AI suggestion on an incident.</div>}
            </div>
          </Reveal>
        </div>
      </AdminOnly>
    </div></div>
  );
}
