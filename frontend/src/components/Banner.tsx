import { motion, AnimatePresence } from "framer-motion";

export function Banner({ show, tone, children }: { show: boolean; tone: "warn" | "info"; children: React.ReactNode }) {
  const color = tone === "warn" ? "var(--critical-hot)" : "var(--elevated)";
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
          style={{ overflow: "hidden" }}
        >
          <div className="container" style={{ paddingTop: 12 }}>
            <div style={{
              border: `1px solid ${color}`, background: `color-mix(in srgb, ${color} 12%, transparent)`,
              color, borderRadius: 12, padding: "10px 16px", fontSize: 13.5, fontWeight: 600,
            }}>
              {children}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
