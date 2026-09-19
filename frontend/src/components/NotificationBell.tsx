import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api/client";
import type { Alert, Level } from "../api/types";
import { LEVEL_COLOR, fmtTime } from "../api/levels";
import { useTime } from "../state/TimeContext";
import { notificationHistory, TONE_COLOR, type Past } from "./Toasts";

/* The bell in the top bar: past notifications and the latest site alerts in one panel,
   with a filter to keep only the serious ones (the big fires). */

type Filter = "all" | "high" | "critical";
const RANK: Record<Level, number> = { NORMAL: 0, ELEVATED: 1, HIGH: 2, CRITICAL: 3 };
const FILTERS: [Filter, string][] = [["all", "All"], ["high", "High and up"], ["critical", "Critical only"]];

export function NotificationBell({ staff }: { staff: boolean }) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState<Filter>(() => { try { return (localStorage.getItem("pg_bell_filter") as Filter) || "all"; } catch { return "all"; } });
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const history = useSyncExternalStore(notificationHistory.subscribe, notificationHistory.get);
  const { step } = useTime();
  const box = useRef<HTMLDivElement>(null);

  // unacknowledged site alerts up to the current time (staff only: partners have no alerts)
  useEffect(() => {
    if (!staff) return;
    let alive = true;
    api.getAlerts(step, "unacknowledged").then((a) => { if (alive) setAlerts(a); }).catch(() => { if (alive) setAlerts([]); });
    return () => { alive = false; };
  }, [staff, step]);

  // close on outside click or Escape
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const setF = (f: Filter) => { setFilter(f); try { localStorage.setItem("pg_bell_filter", f); } catch { /* ignore */ } };
  const keepTone = (h: Past) => filter === "all" || (filter === "critical" ? h.tone === "critical" : h.tone === "critical" || h.tone === "warn");
  const keepLevel = (a: Alert) => filter === "all" || RANK[a.to_level] >= (filter === "critical" ? 3 : 2);
  const notes = history.filter(keepTone);
  const siteAlerts = (alerts ?? []).filter((a) => a.kind === "escalation" && keepLevel(a))
    .sort((a, b) => RANK[b.to_level] - RANK[a.to_level] || b.score - a.score || b.at.localeCompare(a.at)).slice(0, 12);
  const unread = history.filter((h) => !h.read).length;
  const criticalAlerts = (alerts ?? []).filter((a) => a.to_level === "CRITICAL" && a.kind === "escalation").length;
  const badge = unread + criticalAlerts;

  const toggle = () => { setOpen((o) => !o); if (!open) window.setTimeout(() => notificationHistory.markAllRead(), 1200); };

  return (
    <div className="bell" ref={box}>
      <button className={`bell-btn ${badge ? "hot" : ""}`} onClick={toggle} aria-expanded={open} aria-haspopup="dialog"
        aria-label={badge ? `Notifications, ${badge} need attention` : "Notifications"}>
        <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden><path d="M12 3a6 6 0 0 0-6 6v3.2l-1.6 3.2A1 1 0 0 0 5.3 17h13.4a1 1 0 0 0 .9-1.6L18 12.2V9a6 6 0 0 0-6-6Zm-2.5 15.5a2.5 2.5 0 0 0 5 0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
        {badge > 0 && <span className="bell-badge">{badge > 99 ? "99+" : badge}</span>}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div className="bell-panel" role="dialog" aria-label="Notifications and alerts"
            initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.15 }}>
            <div className="bell-top">
              <strong>Notifications</strong>
              {history.length > 0 && <button className="bell-clear" onClick={() => notificationHistory.clear()}>Clear</button>}
            </div>
            <div className="bell-filters" role="group" aria-label="Show">
              {FILTERS.map(([f, label]) => (
                <button key={f} className={`bell-chip ${filter === f ? "on" : ""}`} aria-pressed={filter === f} onClick={() => setF(f)}>{label}</button>
              ))}
            </div>
            <div className="bell-scroll">
              {notes.length === 0 ? <div className="bell-empty">{history.length ? "Nothing at this level." : "No notifications yet. They appear here when something happens: a simulation, a drill, a level change."}</div> : (
                notes.slice(0, 15).map((h) => (
                  <div key={h.id} className={`bell-item ${h.read ? "" : "unread"}`}>
                    <i style={{ background: TONE_COLOR[h.tone] }} />
                    <div><div className="bell-title">{h.title}</div>{h.body && <div className="bell-body">{h.body}</div>}<div className="bell-at">{h.at}</div></div>
                  </div>
                ))
              )}
              {staff && (
                <>
                  <div className="bell-section">Site alerts not yet acknowledged</div>
                  {alerts === null ? <div className="bell-empty">Loading…</div> : siteAlerts.length === 0 ? <div className="bell-empty">None at this level.</div> : siteAlerts.map((a) => (
                    <Link key={a.alert_id} to={`/sites/${a.site_id}`} className="bell-item link-item" onClick={() => setOpen(false)}>
                      <i style={{ background: LEVEL_COLOR[a.to_level] }} />
                      <div>
                        <div className="bell-title">{a.site_name}: <span style={{ color: LEVEL_COLOR[a.to_level] }}>{a.to_level.toLowerCase()}</span> <span className="bell-score">score {a.score}</span></div>
                        <div className="bell-body">{a.headline}</div>
                        <div className="bell-at">{fmtTime(a.at)}</div>
                      </div>
                    </Link>
                  ))}
                </>
              )}
            </div>
            {staff && <Link to="/alerts" className="bell-all" onClick={() => setOpen(false)}>Open all alerts</Link>}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
