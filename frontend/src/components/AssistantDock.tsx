import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api/client";
import { useTime } from "../state/TimeContext";
import type { AssistantAnswer, AssistantTurn } from "../api/types";

/** Ask the operations assistant, from any page.
 *
 *  Deliberately not a general chatbot, and the interface says so: the empty state names what
 *  it can answer, a refusal is shown in the assistant's own words rather than hidden, and
 *  every answer carries its evidence chips so the operator can see what it read. Urgency
 *  colours the answer's edge — an "urgent" reply should not look like small talk.
 */

const STARTERS = [
  "Which site should I worry about first?",
  "How long until the fire reaches this site?",
  "Which access route is exposed?",
  "Why is this site high?",
];

type Msg = { role: "operator" | "assistant"; text: string; meta?: AssistantAnswer };

const EDGE: Record<AssistantAnswer["urgency"], string> = {
  urgent: "var(--critical-hot)",
  action: "var(--elevated)",
  info: "var(--border-2)",
};

export function AssistantDock() {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const { step } = useTime();
  const loc = useLocation();
  const endRef = useRef<HTMLDivElement>(null);

  // The site in view, so "this site" means what the operator is looking at. Parsed from the
  // path rather than useParams, because this dock lives in the layout and never matches the
  // child route that owns the parameter. An incident id starts with its site id.
  const contextSite =
    loc.pathname.match(/^\/(?:sites|field)\/([^/]+)/)?.[1] ??
    loc.pathname.match(/^\/incidents\/([A-Za-z0-9-]+)_/)?.[1] ??
    null;

  useEffect(() => { endRef.current?.scrollIntoView({ block: "end" }); }, [msgs, open]);

  async function send(text: string) {
    const question = text.trim();
    if (!question || busy) return;
    setQ("");
    setMsgs((m) => [...m, { role: "operator", text: question }]);
    setBusy(true);
    try {
      const history: AssistantTurn[] = msgs.slice(-6).map((m) => ({ role: m.role, text: m.text }));
      const a = await api.askAssistant(question, contextSite, step, history);
      setMsgs((m) => [...m, { role: "assistant", text: a.answer, meta: a }]);
    } catch {
      setMsgs((m) => [...m, {
        role: "assistant",
        text: "I could not reach the engine. The site data on screen is still current.",
      }]);
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button className="btn primary assistant-fab no-print" onClick={() => setOpen(true)}
              title="Ask the operations assistant">
        Ask the assistant
      </button>
    );
  }

  return (
    <div className="card assistant-dock no-print">
      <div className="between" style={{ marginBottom: 10 }}>
        <div>
          <div className="eyebrow">Operations assistant</div>
          <div className="mute small" style={{ marginTop: 2 }}>
            Answers only from your own site data
          </div>
        </div>
        <button className="btn sm ghost" onClick={() => setOpen(false)} aria-label="Close">✕</button>
      </div>

      <div className="assistant-log">
        {msgs.length === 0 && (
          <div className="dim small" style={{ display: "grid", gap: 10 }}>
            <div>
              Ask about levels, why a site scored as it did, access routes, people on site,
              protocol actions, sensors, or when the front is estimated to arrive.
            </div>
            <div className="row wrap" style={{ gap: 6 }}>
              {STARTERS.map((s) => (
                <button key={s} className="btn sm ghost" onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}

        {msgs.map((m, i) => (
          <div key={i} className={`assistant-msg ${m.role}`}
               style={m.role === "assistant" && m.meta
                 ? { borderLeft: `3px solid ${EDGE[m.meta.urgency]}` } : undefined}>
            <div style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
            {m.meta && m.meta.evidence.length > 0 && (
              <div className="row wrap" style={{ gap: 5, marginTop: 8 }}>
                {m.meta.evidence.map((e) => <span key={e} className="chip">{e}</span>)}
              </div>
            )}
            {m.meta && (
              <div className="mute small" style={{ marginTop: 6 }}>
                {m.meta.generated_by === "rules"
                  ? "Answered from the data without a model"
                  : `${m.meta.generated_by}${m.meta.model ? ` · ${m.meta.model}` : ""}`}
                {m.meta.refused ? " · declined" : ""}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="row" style={{ gap: 8 }}><span className="spinner" />
          <span className="dim small">Reading the site data…</span></div>}
        <div ref={endRef} />
      </div>

      <form className="row" style={{ gap: 8, marginTop: 10 }}
            onSubmit={(e) => { e.preventDefault(); send(q); }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} maxLength={500}
               placeholder={contextSite ? `Ask about ${contextSite}…` : "Ask about your sites…"}
               aria-label="Ask the operations assistant" />
        <button className={`btn primary${busy ? " working" : ""}`} disabled={busy || !q.trim()}>
          Ask
        </button>
      </form>
      {msgs.some((m) => m.meta) && (
        <div className="mute small" style={{ marginTop: 8 }}>
          {msgs.find((m) => m.meta)!.meta!.disclaimer}
        </div>
      )}
    </div>
  );
}
