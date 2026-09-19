import { useSyncExternalStore } from "react";
import { AnimatePresence, motion } from "framer-motion";

/** Notifications that slide in on the right. Any page can push one with `notify(...)`. */
export type ToastTone = "critical" | "warn" | "info" | "ok";
export interface Toast { id: number; tone: ToastTone; title: string; body?: string; at: string }

let toasts: Toast[] = [];
let nextId = 1;
const subs = new Set<() => void>();
const emit = () => subs.forEach((f) => f());

// Every notification is also kept in a history the bell shows (this browser tab only).
const HISTORY_KEY = "pg_notifications";
export interface Past extends Toast { read: boolean }
let history: Past[] = (() => { try { return JSON.parse(sessionStorage.getItem(HISTORY_KEY) || "[]"); } catch { return []; } })();
const saveHistory = () => { try { sessionStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 60))); } catch { /* ignore */ } };
export const notificationHistory = {
  get: () => history,
  subscribe(fn: () => void) { subs.add(fn); return () => { subs.delete(fn); }; },
  markAllRead() { history = history.map((h) => ({ ...h, read: true })); saveHistory(); emit(); },
  clear() { history = []; saveHistory(); emit(); },
};

export function notify(tone: ToastTone, title: string, body?: string, ms = tone === "critical" ? 9000 : 6500) {
  const t: Toast = { id: nextId++, tone, title, body, at: new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) };
  toasts = [t, ...toasts].slice(0, 3);            // at most three at once
  history = [{ ...t, id: Date.now() + t.id, read: false }, ...history].slice(0, 60);
  saveHistory();
  emit();
  window.setTimeout(() => dismiss(t.id), ms);
}
export function dismiss(id: number) { toasts = toasts.filter((t) => t.id !== id); emit(); }
export function clearToasts() { toasts = []; emit(); }

export const TONE_COLOR: Record<ToastTone, string> = { critical: "var(--critical-hot)", warn: "var(--high)", info: "var(--elevated)", ok: "var(--normal)" };
const COLOR = TONE_COLOR;
const ICON: Record<ToastTone, string> = { critical: "▲", warn: "●", info: "●", ok: "✓" };

export function ToastStack() {
  const list = useSyncExternalStore((f) => { subs.add(f); return () => subs.delete(f); }, () => toasts);
  return (
    <div className="toasts" role="region" aria-label="Notifications" aria-live="assertive">
      <AnimatePresence initial={false}>
        {list.map((t) => (
          <motion.div key={t.id} layout className={`toast ${t.tone}`}
            initial={{ opacity: 0, x: 60 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 60 }}
            transition={{ type: "spring", stiffness: 420, damping: 34 }}
            style={{ borderLeftColor: COLOR[t.tone] }}>
            <span className="toast-icon" style={{ color: COLOR[t.tone] }} aria-hidden>{ICON[t.tone]}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="toast-title">{t.title}</div>
              {t.body && <div className="toast-body">{t.body}</div>}
              <div className="toast-at">{t.at}</div>
            </div>
            <button className="toast-x" onClick={() => dismiss(t.id)} aria-label="Dismiss notification">×</button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
