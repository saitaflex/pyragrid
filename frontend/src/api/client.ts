// client.ts — one typed function per §2.5 endpoint. Mock mode is fully self-contained;
// live mode calls VITE_API_BASE_URL and falls back to mocks on failure.
import * as E from "./engine";
import type {
  AckResponse, AdvisorResponse, Alert, AuditEntry, DecisionRecord, Detection, HandoffPack,
  Health, ImportReport, Incident, IngestionRun, LoginResponse, OutboxEmail, Portfolio, Site,
  SiteStatus, SopRule, SopRuleInput, SourceStatus, TimelinePoint, User, ReplaySummary,
  SensorsResponse, Situation, StaffUser, DrillView, DrillScenario, SimAdvice,
} from "./types";
import type { Conditions, FireState } from "../sim/firesim";

// Unset in a production build → same origin (the root Vercel project serves the Engine at /api).
export const BASE = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://localhost:8000" : "");
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "false"; // default to mocks

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
const now = () => new Date().toISOString().replace(/\.\d+Z$/, "Z");

const MOCK_USERS: Record<string, { user: User; password: string }> = {
  "admin@demo.eu": { password: "demo1234", user: { email: "admin@demo.eu", name: "Demo Admin", customer_id: "demo", role: "admin" } },
  "operator@demo.eu": { password: "demo1234", user: { email: "operator@demo.eu", name: "Demo Operator", customer_id: "demo", role: "operator" } },
  "other@othercorp.eu": { password: "demo1234", user: { email: "other@othercorp.eu", name: "Other Admin", customer_id: "othercorp", role: "admin" } },
};

// ---- mutable mock state ----
let rules: SopRule[] = E.DEFAULT_RULES.map((r) => ({ ...r, conditions: { ...r.conditions } }));
const acks = new Map<string, { by: string; at: string }>();
const decisions = new Map<string, { decision: "approved" | "rejected"; note: string; by: string; at: string; incidentId: string; title: string; engine: "template" }>();
const advisorStore = new Map<string, AdvisorResponse>();
const audit: AuditEntry[] = [{ id: 1, at: now(), actor: "admin@demo.eu", action: "login", details: "" }];
let auditId = 2;
let currentUser: User | null = null;
const addAudit = (actor: string, action: string, details: string) => { audit.unshift({ id: auditId++, at: now(), actor, action, details }); };

const mock = {
  health(): Promise<Health> {
    return Promise.resolve({
      status: "ok", contract_version: "2.1.0", model_version: "rules-1.0",
      data_source: "synthetic_fallback", replay_start: E.stepIso(0),
      replay_end: new Date(E.START + E.STEPS * E.STEP_MS).toISOString().replace(".000Z", "Z"), step_hours: 3,
    });
  },

  async login(email: string, password: string): Promise<LoginResponse> {
    await delay(350);
    const rec = MOCK_USERS[email.toLowerCase()];
    if (!rec || rec.password !== password) throw new ApiError(401, "invalid credentials");
    currentUser = rec.user;
    addAudit(rec.user.email, "login", "");
    return { access_token: "mock-token", token_type: "bearer", expires_in: 43200, user: rec.user };
  },

  me(): Promise<User> {
    if (!currentUser) throw new ApiError(401, "not authenticated");
    return Promise.resolve(currentUser);
  },

  getSites(): Promise<Site[]> { return Promise.resolve(E.SITES); },

  getPortfolio(atStep: number): Promise<Portfolio> { return Promise.resolve(E.portfolioAt(atStep, rules)); },

  getSiteStatus(id: string, atStep: number): Promise<SiteStatus> {
    if (!E.siteById(id)) throw new ApiError(404, "site not found");
    const { status } = E.statusAt(id, atStep);
    status.sop_actions = E.matchActions(rules, status).actions;
    return Promise.resolve(status);
  },

  getTimeline(id: string): Promise<TimelinePoint[]> { return Promise.resolve(E.timelineFor(id)); },
  getDetections(atStep: number, windowH = 12): Promise<Detection[]> { return Promise.resolve(E.detectionsAt(atStep, windowH)); },
  getSummary(): Promise<ReplaySummary> { return Promise.resolve(E.summary(rules)); },

  getAlerts(atStep: number, status: "all" | "unacknowledged" = "all"): Promise<Alert[]> {
    let list = E.alertsUpTo(atStep, rules).map((a) => {
      const ack = acks.get(a.alert_id);
      return ack ? { ...a, acknowledged: true, acknowledged_by: ack.by, acknowledged_at: ack.at } : a;
    });
    if (status === "unacknowledged") list = list.filter((a) => !a.acknowledged);
    return Promise.resolve(list);
  },

  async acknowledge(alertId: string): Promise<AckResponse> {
    await delay(200);
    if (!acks.has(alertId)) {
      acks.set(alertId, { by: currentUser?.email ?? "operator@demo.eu", at: now() });
      addAudit(currentUser?.email ?? "operator@demo.eu", "alert_acknowledge", alertId);
    }
    const ack = acks.get(alertId)!;
    return { alert_id: alertId, acknowledged: true, acknowledged_by: ack.by, acknowledged_at: ack.at };
  },

  getIncidents(atStep: number): Promise<Incident[]> { return Promise.resolve(E.incidentsOpenAt(atStep, rules)); },
  getIncidentsHistory(): Promise<Incident[]> { return Promise.resolve(E.incidentsHistory(rules)); },
  getIncident(id: string, atStep: number): Promise<Incident> {
    const inc = E.incidentById(id, rules, atStep);
    if (!inc) throw new ApiError(404, "incident not found");
    return Promise.resolve(inc);
  },

  getRules(): Promise<SopRule[]> { return Promise.resolve([...rules].sort((a, b) => a.priority - b.priority || a.rule_id.localeCompare(b.rule_id))); },
  async createRule(body: SopRuleInput): Promise<SopRule> {
    await delay(150);
    const nums = rules.map((r) => parseInt(r.rule_id.slice(2)) || 0);
    const rule: SopRule = { ...body, rule_id: `R-${String((Math.max(0, ...nums) + 1)).padStart(3, "0")}` };
    rules.push(rule); addAudit(currentUser!.email, "sop_rule_create", rule.rule_id);
    return rule;
  },
  async updateRule(id: string, body: SopRuleInput): Promise<SopRule> {
    await delay(150);
    const i = rules.findIndex((r) => r.rule_id === id);
    if (i < 0) throw new ApiError(404, "rule not found");
    rules[i] = { ...body, rule_id: id }; addAudit(currentUser!.email, "sop_rule_update", id);
    return rules[i];
  },
  async deleteRule(id: string): Promise<void> {
    await delay(150);
    if (!rules.some((r) => r.rule_id === id)) throw new ApiError(404, "rule not found");
    rules = rules.filter((r) => r.rule_id !== id); addAudit(currentUser!.email, "sop_rule_delete", id);
  },

  getSources(): Promise<SourceStatus[]> {
    return Promise.resolve([
      { name: "FIRMS", state: "FALLBACK", detail: "Synthetic demo detections (FIRMS not reachable at data build time)" },
      { name: "Weather", state: "ONLINE", detail: "Open-Meteo historical archive" },
      { name: "Vegetation", state: "FALLBACK", detail: "Fuel class from customer asset data; no land-cover dataset yet" },
      { name: "Notification", state: "FALLBACK", detail: "Email outbox only (SMTP not configured)" },
      { name: "Database", state: "ONLINE", detail: "SQLite (local file)" },
      { name: "AI Advisor", state: "FALLBACK", detail: "Template suggestions (no LLM configured)" },
    ]);
  },
  getIngestionRuns(): Promise<IngestionRun[]> {
    return Promise.resolve([{ run_id: "run-synthetic-0001", source: "synthetic_fallback", started_at: E.stepIso(0), completed_at: E.stepIso(0), records_received: 720, records_inserted: 718, records_rejected: 0, error_message: null }]);
  },
  getOutbox(atStep: number): Promise<OutboxEmail[]> {
    const emails = E.alertsUpTo(atStep, rules).filter((a) => a.kind === "escalation").map((a) => ({
      alert_id: a.alert_id, to: "control-room@demo.eu", subject: `[${a.to_level}] ${a.site_name}: ${a.headline}`,
      body: `${a.site_name} escalated ${a.from_level} -> ${a.to_level} at ${a.at} (score ${a.score}). Open the platform for factors and actions.`,
      channel: "email" as const, status: "outbox" as const,
    }));
    return Promise.resolve(emails);
  },
  getAudit(): Promise<AuditEntry[]> { return Promise.resolve(audit.slice(0, 200)); },

  async generateAdvice(incidentId: string, siteId: string, atStep: number): Promise<AdvisorResponse> {
    await delay(850);
    const resp = E.generateAdvice(incidentId, siteId, atStep, rules);
    advisorStore.set(incidentId, resp);
    addAudit(currentUser!.email, "advisor_generate", incidentId);
    return resp;
  },
  getLatestAdvice(incidentId: string): Promise<AdvisorResponse | null> {
    const resp = advisorStore.get(incidentId);
    if (!resp) return Promise.resolve(null);
    return Promise.resolve({ ...resp, suggestions: resp.suggestions.map((s) => {
      const d = decisions.get(s.suggestion_id);
      return d ? { ...s, decision: d.decision, decided_by: d.by, decided_at: d.at } : s;
    }) });
  },
  async decide(suggestionId: string, decision: "approved" | "rejected", note: string, incidentId: string, title: string): Promise<DecisionRecord> {
    await delay(150);
    if (!decisions.has(suggestionId))
      decisions.set(suggestionId, { decision, note, by: currentUser!.email, at: now(), incidentId, title, engine: "template" });
    const d = decisions.get(suggestionId)!;
    addAudit(currentUser!.email, "advisor_decision", suggestionId);
    return { suggestion_id: suggestionId, incident_id: d.incidentId, title: d.title, decision: d.decision, note: d.note, decided_by: d.by, decided_at: d.at, generated_by: d.engine };
  },
  getDecisions(): Promise<DecisionRecord[]> {
    return Promise.resolve([...decisions.entries()].map(([sid, d]) => ({ suggestion_id: sid, incident_id: d.incidentId, title: d.title, decision: d.decision, note: d.note, decided_by: d.by, decided_at: d.at, generated_by: d.engine })).reverse());
  },

  getHandoff(id: string, atStep: number): Promise<HandoffPack> {
    if (!E.siteById(id)) throw new ApiError(404, "site not found");
    return Promise.resolve(E.buildHandoff(id, atStep));
  },

  async importAssets(text: string): Promise<ImportReport> {
    await delay(400);
    const lines = text.trim().split(/\r?\n/).slice(1).filter(Boolean);
    const rejected: ImportReport["rejected"] = [];
    let accepted = 0;
    lines.forEach((line, idx) => {
      const cols = line.split(",");
      if (cols.length < 11) rejected.push({ row: idx + 1, site_id: cols[0] || null, reason: "missing columns" });
      else accepted++;
    });
    if (accepted === 0) throw new ApiError(422, "no valid rows");
    addAudit(currentUser?.email ?? "admin@demo.eu", "assets_import", `accepted ${accepted}`);
    return { accepted, rejected, total_sites: accepted };
  },

  // Sensor meshes, partner sharing and drills are computed by the Engine only.
  getSensors: (_step: number, _siteId?: string): Promise<SensorsResponse> => needsEngine(),
  installSensors: (_siteId: string): Promise<void> => needsEngine(),
  removeSensors: (_siteId: string): Promise<void> => needsEngine(),
  getSituation: (_step: number): Promise<Situation> => needsEngine(),
  getStaff: (): Promise<StaffUser[]> => needsEngine(),
  createDrill: (_body: { site_id: string; scenario: DrillScenario; pace_s: number; participants: string[] }): Promise<DrillView> => needsEngine(),
  getDrills: (): Promise<DrillView[]> => needsEngine(),
  getActiveDrills: (): Promise<DrillView[]> => Promise.resolve([]),
  getDrill: (_id: string): Promise<DrillView> => needsEngine(),
  ackDrill: (_id: string): Promise<DrillView> => needsEngine(),
  respondDrill: (_id: string, _actions: string[], _note: string): Promise<DrillView> => needsEngine(),
  endDrill: (_id: string): Promise<DrillView> => needsEngine(),
  simAdvice: (_siteId: string, _c: Conditions, _st: SimStateBody): Promise<SimAdvice> => needsEngine(),
  simComplete: (_body: { site_id: string; summary: string; actions_done: string[]; actions_total: number; duration_s: number }): Promise<void> => needsEngine(),
};

/** What the simulator sends to the AI: the numbers, not the drawn shapes. */
export type SimStateBody = Omit<FireState, "perimeter" | "front" | "ignition" | "reached"> & {
  sensors_fire: number; sensors_warm: number; sensors_offline: number;
};

function needsEngine(): Promise<never> {
  return Promise.reject(new ApiError(503, "This feature needs the live Engine (not available in mock mode)."));
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}

// ---- live mode: same signatures, backed by the Engine (§2.5) ----
type Q = Record<string, string | number | undefined>;
const at = (step: number) => E.stepIso(step);

async function req<T>(method: string, path: string, opts: { query?: Q; body?: unknown; form?: FormData } = {}): Promise<T> {
  const qs = Object.entries(opts.query ?? {}).filter(([, v]) => v !== undefined)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join("&");
  const headers: Record<string, string> = {};
  try { const t = sessionStorage.getItem("wai_token"); if (t) headers.Authorization = `Bearer ${t}`; } catch { /* ignore */ }
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(`${BASE}/api${path}${qs ? `?${qs}` : ""}`, {
    method, headers, body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { const j = await res.json(); detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const live: typeof mock = {
  health: () => req("GET", "/health"),
  async login(email, password) {
    const r = await req<LoginResponse>("POST", "/auth/login", { body: { email, password } });
    currentUser = r.user; // keeps the mock fallback usable if the Engine drops later
    return r;
  },
  me: () => req("GET", "/auth/me"),
  getSites: () => req("GET", "/sites"),
  getPortfolio: (s) => req("GET", "/portfolio", { query: { at: at(s) } }),
  getSiteStatus: (id, s) => req("GET", `/sites/${encodeURIComponent(id)}/status`, { query: { at: at(s) } }),
  getTimeline: (id) => req("GET", `/sites/${encodeURIComponent(id)}/timeline`),
  getDetections: (s, windowH = 12) => req("GET", "/detections", { query: { at: at(s), window_hours: windowH } }),
  getSummary: () => req("GET", "/replay/summary"),
  getAlerts: (s, status = "all") => req("GET", "/alerts", { query: { at: at(s), status } }),
  acknowledge: (id) => req("POST", `/alerts/${encodeURIComponent(id)}/acknowledge`),
  getIncidents: (s) => req("GET", "/incidents", { query: { at: at(s) } }),
  getIncidentsHistory: () => req("GET", "/incidents/history"),
  getIncident: (id, s) => req("GET", `/incidents/${encodeURIComponent(id)}`, { query: { at: at(s) } }),
  getRules: () => req("GET", "/sop/rules"),
  createRule: (body) => req("POST", "/sop/rules", { body }),
  updateRule: (id, body) => req("PUT", `/sop/rules/${encodeURIComponent(id)}`, { body }),
  deleteRule: (id) => req("DELETE", `/sop/rules/${encodeURIComponent(id)}`),
  getSources: () => req("GET", "/status/sources"),
  getIngestionRuns: () => req("GET", "/ingestion/runs"),
  getOutbox: (s) => req("GET", "/notifications/outbox", { query: { at: at(s) } }),
  getAudit: () => req("GET", "/audit"),
  generateAdvice: (incidentId, _siteId, s) => req("POST", `/advisor/incidents/${encodeURIComponent(incidentId)}`, { query: { at: at(s) } }),
  async getLatestAdvice(incidentId) {
    try { return await req<AdvisorResponse>("GET", `/advisor/incidents/${encodeURIComponent(incidentId)}/latest`); }
    catch (e) { if (e instanceof ApiError && e.status === 404) return null; throw e; }
  },
  decide: (suggestionId, decision, note) => req("POST", `/advisor/suggestions/${encodeURIComponent(suggestionId)}/decision`, { body: { decision, note } }),
  getDecisions: () => req("GET", "/advisor/decisions"),
  getHandoff: (id, s) => req("GET", `/sites/${encodeURIComponent(id)}/handoff`, { query: { at: at(s) } }),
  importAssets(text) {
    const form = new FormData();
    form.append("file", new Blob([text], { type: "text/csv" }), "assets.csv");
    return req("POST", "/assets/import", { form });
  },

  getSensors: (s, siteId) => req("GET", "/sensors", { query: { at: at(s), site_id: siteId } }),
  installSensors: (siteId) => req("POST", "/sensors/install", { body: { site_id: siteId } }),
  removeSensors: (siteId) => req("DELETE", `/sensors/install/${encodeURIComponent(siteId)}`),
  getSituation: (s) => req("GET", "/situation", { query: { at: at(s) } }),
  getStaff: () => req("GET", "/staff"),
  createDrill: (body) => req("POST", "/drills", { body }),
  getDrills: () => req("GET", "/drills"),
  getActiveDrills: () => req("GET", "/drills/active"),
  getDrill: (id) => req("GET", `/drills/${encodeURIComponent(id)}`),
  ackDrill: (id) => req("POST", `/drills/${encodeURIComponent(id)}/ack`),
  respondDrill: (id, actions, note) => req("POST", `/drills/${encodeURIComponent(id)}/respond`, { body: { actions, note } }),
  endDrill: (id) => req("POST", `/drills/${encodeURIComponent(id)}/end`),
  simAdvice: (siteId, conditions, state) => req("POST", "/simulate/advice", { body: { site_id: siteId, conditions, state } }),
  simComplete: (body) => req("POST", "/simulate/complete", { body }),
};

// ---- offline state: live calls that cannot reach the Engine fall back to mocks ----
let offline = false;
const offlineSubs = new Set<() => void>();
export const offlineStore = {
  get: () => offline,
  subscribe(fn: () => void) { offlineSubs.add(fn); return () => { offlineSubs.delete(fn); }; },
};
const setOffline = (v: boolean) => { if (offline !== v) { offline = v; offlineSubs.forEach((f) => f()); } };

// Engine unreachable (network error) or broken (5xx) → mock data; 4xx are real answers.
const unreachable = (e: unknown) => !(e instanceof ApiError) || e.status >= 500;

function withFallback(): typeof mock {
  const out = {} as Record<string, unknown>;
  for (const key of Object.keys(mock) as (keyof typeof mock)[]) {
    out[key] = async (...args: unknown[]) => {
      try {
        const r = await (live[key] as (...a: unknown[]) => Promise<unknown>)(...args);
        setOffline(false);
        return r;
      } catch (e) {
        if (unreachable(e)) {
          setOffline(true);
          return (mock[key] as (...a: unknown[]) => Promise<unknown>)(...args);
        }
        if (e instanceof ApiError && e.status === 401 && key !== "login") {
          // stale or mock token against the live Engine → sign in again
          try { sessionStorage.removeItem("wai_token"); sessionStorage.removeItem("wai_user"); } catch { /* ignore */ }
          if (!location.pathname.startsWith("/login")) location.assign("/login");
        }
        throw e;
      }
    };
  }
  return out as typeof mock;
}

export const api: typeof mock = USE_MOCKS ? mock : withFallback();

export type Api = typeof api;
