import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api/client";
import type { AdvisorResponse, AdvisorEngine, Audience } from "../api/types";
import { fmtTime } from "../api/levels";
import { EvidenceChip } from "./EvidenceChip";

const ENGINE_LABEL: Record<AdvisorEngine, string> = { groq: "Groq", ollama: "Ollama", template: "Template (no AI)" };
const AUDIENCE_LABEL: Record<Audience, string> = { operator: "Operator", site_team: "Site team", fire_service_liaison: "Fire service liaison" };

export function AdvisorPanel({ incidentId, siteId, atStep }: { incidentId: string; siteId: string; atStep: number }) {
  const [resp, setResp] = useState<AdvisorResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { api.getLatestAdvice(incidentId).then(setResp); }, [incidentId]);

  const generate = async () => {
    setLoading(true);
    try { setResp(await api.generateAdvice(incidentId, siteId, atStep)); } finally { setLoading(false); }
  };
  const decide = async (sid: string, title: string, decision: "approved" | "rejected") => {
    await api.decide(sid, decision, "", incidentId, title);
    setResp(await api.getLatestAdvice(incidentId));
  };

  return (
    <div className="card pad-lg" style={{ borderColor: "color-mix(in srgb, var(--ember) 30%, var(--border))" }}>
      <div className="between wrap" style={{ marginBottom: 6 }}>
        <div>
          <div className="eyebrow">AI Advisor · suggestions need human approval</div>
          <div className="dim small" style={{ marginTop: 4 }}>Grounded suggestions for the company. Never firefighting tactics.</div>
        </div>
        <button className="btn primary" onClick={generate} disabled={loading}>
          {loading ? <><span className="spinner" /> Generating…</> : resp ? "Regenerate advice" : "Generate advice"}
        </button>
      </div>

      {resp && (
        <div className="row wrap" style={{ gap: 10, margin: "12px 0" }}>
          <span className="chip" style={{ color: "var(--ember-2)", borderColor: "var(--border-2)" }}>{ENGINE_LABEL[resp.generated_by]}</span>
          {resp.model && <span className="chip">{resp.model}</span>}
          <span className="chip">{fmtTime(resp.created_at)}</span>
          {resp.rejected_by_guardrails > 0 && <span className="chip assumed">{resp.rejected_by_guardrails} blocked by safety rules</span>}
          {resp.fallback_reason && <span className="chip unknown">{resp.fallback_reason}</span>}
        </div>
      )}

      {!resp && !loading && <div className="dim small" style={{ padding: "20px 0" }}>No advice yet. Generate grounded suggestions for this incident.</div>}

      <div className="grid" style={{ gap: 12 }}>
        <AnimatePresence>
          {resp?.suggestions.map((s, i) => (
            <motion.div key={s.suggestion_id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
              className="card" style={{ background: "var(--bg-1)" }}>
              <div className="between wrap" style={{ gap: 10 }}>
                <div className="row" style={{ gap: 8 }}>
                  <span className="chip" style={{ color: "var(--ember-2)" }}>P{s.priority}</span>
                  <span className="chip">{AUDIENCE_LABEL[s.audience]}</span>
                </div>
                {s.decision ? (
                  <span className={`chip ${s.decision === "approved" ? "observed" : "unknown"}`}>
                    {s.decision === "approved" ? "✓ Approved" : "✕ Rejected"} · {s.decided_by}
                  </span>
                ) : (
                  <div className="row" style={{ gap: 8 }}>
                    <button className="btn sm" onClick={() => decide(s.suggestion_id, s.title, "approved")}>Approve</button>
                    <button className="btn sm ghost" onClick={() => decide(s.suggestion_id, s.title, "rejected")}>Reject</button>
                  </div>
                )}
              </div>
              <div style={{ fontWeight: 600, margin: "10px 0 4px" }}>{s.title}</div>
              <div className="dim small">{s.detail}</div>
              <div className="row wrap" style={{ gap: 6, marginTop: 10 }}>{s.evidence.map((e) => <EvidenceChip key={e} ek={e} />)}</div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {resp && <div className="small mute" style={{ marginTop: 14, fontStyle: "italic" }}>{resp.disclaimer}</div>}
    </div>
  );
}
