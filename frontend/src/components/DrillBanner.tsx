import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api/client";
import type { DrillView } from "../api/types";
import { useAuth } from "../state/AuthContext";
import { STAFF_ROLES } from "../api/types";

/** Every employee sees running drills they still have to answer, on every page. */
export function DrillBanner() {
  const { user } = useAuth();
  const loc = useLocation();
  const [drills, setDrills] = useState<DrillView[]>([]);
  const staff = !!user && STAFF_ROLES.includes(user.role);

  useEffect(() => {
    if (!staff) return;
    let alive = true;
    const poll = () => api.getActiveDrills().then((d) => { if (alive) setDrills(d); }).catch(() => {});
    poll();
    const t = window.setInterval(poll, 5000);
    return () => { alive = false; window.clearInterval(t); };
  }, [staff, loc.pathname]);

  const shown = drills.filter((d) => !loc.pathname.startsWith(`/drills/${d.drill_id}`));
  return (
    <AnimatePresence>
      {shown.map((d) => (
        <motion.div key={d.drill_id} initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} style={{ overflow: "hidden" }}>
          <div className="container" style={{ paddingTop: 12 }}>
            <Link to={`/drills/${d.drill_id}`} className="drill-alert">
              <span className="drill-pulse" aria-hidden />
              <span style={{ fontWeight: 800, letterSpacing: "0.06em" }}>DRILL ALERT</span>
              <span style={{ flex: 1 }}>{d.site_name}: {d.stages[d.stages.length - 1]?.title ?? d.scenario_title}</span>
              <span className="btn sm" style={{ background: "var(--critical-hot)", borderColor: "var(--critical-hot)", color: "#fff" }}>
                {d.my_response?.acked_at ? "Respond now →" : "Acknowledge →"}
              </span>
            </Link>
          </div>
        </motion.div>
      ))}
    </AnimatePresence>
  );
}
