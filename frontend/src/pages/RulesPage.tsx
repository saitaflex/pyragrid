import { useState } from "react";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { AdminOnly } from "../components/RouteGuards";
import { useAuth } from "../state/AuthContext";
import { Reveal } from "../components/Reveal";
import { LEVELS } from "../api/levels";
import type { Level, SiteType, SopRule, SopRuleInput } from "../api/types";

const TYPES: SiteType[] = ["solar_farm", "wind_farm", "substation", "forest_block", "telecom_tower", "test_plot"];
const blank: SopRuleInput = { name: "", enabled: true, priority: 50, conditions: { min_level: "HIGH", asset_types: [], min_criticality: 1, wind_toward_site: null }, actions: [] };

export function RulesPage() {
  const { user } = useAuth();
  const { data: rules, reload } = useAsync(() => api.getRules(), []);
  const [editing, setEditing] = useState<SopRule | "new" | null>(null);
  const [form, setForm] = useState<SopRuleInput>(blank);
  const [actionsText, setActionsText] = useState("");

  const start = (r: SopRule | "new") => {
    setEditing(r);
    const base = r === "new" ? blank : r;
    setForm({ name: base.name, enabled: base.enabled, priority: base.priority, conditions: { ...base.conditions, asset_types: [...base.conditions.asset_types] }, actions: base.actions });
    setActionsText(base.actions.join("\n"));
  };
  const save = async () => {
    const body: SopRuleInput = { ...form, actions: actionsText.split("\n").map((s) => s.trim()).filter(Boolean) };
    if (editing === "new") await api.createRule(body);
    else if (editing) await api.updateRule(editing.rule_id, body);
    setEditing(null); reload();
  };
  const del = async (id: string) => { if (confirm(`Delete ${id}?`)) { await api.deleteRule(id); reload(); } };

  const isAdmin = user?.role === "admin";

  return (
    <div className="page"><div className="container grid" style={{ gap: 18 }}>
      <div className="between wrap">
        <div><div className="eyebrow">SOP rules</div><h1 className="display" style={{ fontSize: "clamp(28px,3.6vw,42px)" }}>Protocol engine</h1></div>
        <AdminOnly><button className="btn primary" onClick={() => start("new")}>+ New rule</button></AdminOnly>
      </div>

      {editing && (
        <Reveal>
          <div className="card pad-lg grid" style={{ gap: 14 }}>
            <div className="eyebrow">{editing === "new" ? "New rule" : `Edit ${editing.rule_id}`}</div>
            <div className="grid" style={{ gridTemplateColumns: "2fr 1fr 1fr", gap: 12 }}>
              <div><label>Name</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
              <div><label>Priority</label><input type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} /></div>
              <div><label>Enabled</label>
                <select value={String(form.enabled)} onChange={(e) => setForm({ ...form, enabled: e.target.value === "true" })}><option value="true">Yes</option><option value="false">No</option></select>
              </div>
            </div>
            <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              <div><label>Min level</label>
                <select value={form.conditions.min_level} onChange={(e) => setForm({ ...form, conditions: { ...form.conditions, min_level: e.target.value as Level } })}>{LEVELS.map((l) => <option key={l}>{l}</option>)}</select>
              </div>
              <div><label>Min criticality</label><input type="number" min={1} max={5} value={form.conditions.min_criticality} onChange={(e) => setForm({ ...form, conditions: { ...form.conditions, min_criticality: Number(e.target.value) } })} /></div>
              <div><label>Wind toward site</label>
                <select value={String(form.conditions.wind_toward_site)} onChange={(e) => setForm({ ...form, conditions: { ...form.conditions, wind_toward_site: e.target.value === "null" ? null : e.target.value === "true" } })}>
                  <option value="null">Any</option><option value="true">Yes</option><option value="false">No</option>
                </select>
              </div>
            </div>
            <div>
              <label>Asset types (empty = all)</label>
              <div className="row wrap" style={{ gap: 6 }}>
                {TYPES.map((t) => {
                  const on = form.conditions.asset_types.includes(t);
                  return <button key={t} type="button" className={`chip ${on ? "observed" : ""}`} style={{ cursor: "pointer" }}
                    onClick={() => setForm({ ...form, conditions: { ...form.conditions, asset_types: on ? form.conditions.asset_types.filter((x) => x !== t) : [...form.conditions.asset_types, t] } })}>{t}</button>;
                })}
              </div>
            </div>
            <div><label>Actions (one per line)</label><textarea rows={4} value={actionsText} onChange={(e) => setActionsText(e.target.value)} /></div>
            <div className="row" style={{ gap: 8 }}><button className="btn primary" onClick={save}>Save</button><button className="btn ghost" onClick={() => setEditing(null)}>Cancel</button></div>
          </div>
        </Reveal>
      )}

      <div className="grid" style={{ gap: 12 }}>
        {rules?.map((r) => (
          <div key={r.rule_id} className="card" style={{ opacity: r.enabled ? 1 : 0.55 }}>
            <div className="between wrap">
              <div>
                <div className="row" style={{ gap: 8 }}><span className="mono small mute">{r.rule_id}</span><span style={{ fontWeight: 600 }}>{r.name}</span>{!r.enabled && <span className="chip unknown">disabled</span>}</div>
                <div className="small mute" style={{ marginTop: 4 }}>≥ {r.conditions.min_level} · crit ≥ {r.conditions.min_criticality} · {r.conditions.asset_types.length ? r.conditions.asset_types.join(", ") : "all types"} · wind {r.conditions.wind_toward_site === null ? "any" : r.conditions.wind_toward_site ? "toward" : "away"} · priority {r.priority}</div>
              </div>
              {isAdmin && <div className="row" style={{ gap: 8 }}><button className="btn sm ghost" onClick={() => start(r)}>Edit</button><button className="btn sm ghost" onClick={() => del(r.rule_id)}>Delete</button></div>}
            </div>
            <div className="row wrap" style={{ gap: 6, marginTop: 10 }}>{r.actions.map((a, i) => <span key={i} className="chip" style={{ textTransform: "none" }}>{a}</span>)}</div>
          </div>
        ))}
      </div>
    </div></div>
  );
}
