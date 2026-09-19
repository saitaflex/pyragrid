import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { STAFF_ROLES, type DataSource } from "../api/types";
import { useAuth } from "../state/AuthContext";
import { BRAND } from "../brand";
import { BrandMark } from "./BrandMark";
import { NotificationBell } from "./NotificationBell";

const SOURCE_LABEL: Record<DataSource, string> = {
  firms_sp: "NASA FIRMS", firms_nrt: "NASA FIRMS (NRT)", synthetic_fallback: "Synthetic demo data",
};

const NAV_STAFF = [
  { to: "/", label: "Portfolio", end: true },
  { to: "/alerts", label: "Alerts" },
  { to: "/sensors", label: "Sensors" },
  { to: "/drills", label: "Drills" },
  { to: "/situation", label: "Shared view" },
  { to: "/history", label: "History" },
  { to: "/assets", label: "Assets" },
  { to: "/rules", label: "Rules" },
  { to: "/system", label: "System" },
];
const NAV_PARTNER = [
  { to: "/situation", label: "Situation", end: true },
  { to: "/sensors", label: "Sensors" },
];

export function TopBar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [src, setSrc] = useState<DataSource>("synthetic_fallback");
  const NAV = user && !STAFF_ROLES.includes(user.role) ? NAV_PARTNER : NAV_STAFF;
  useEffect(() => { api.health().then((h) => setSrc(h.data_source)); }, []);

  return (
    <header style={{ position: "sticky", top: 0, zIndex: 30, backdropFilter: "blur(14px)", background: "rgba(8,8,10,0.72)", borderBottom: "1px solid var(--border)" }}>
      <div className="container" style={{ display: "flex", alignItems: "center", gap: 20, height: 62 }}>
        <NavLink to={NAV[0].to} className="row" style={{ gap: 10 }}>
          <BrandMark size={34} />
          <span className="display" style={{ fontSize: 20 }}>{BRAND.name}</span>
        </NavLink>
        <nav className="row" style={{ gap: 4, marginLeft: 8, flex: 1 }}>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className="nav-link"
              style={({ isActive }) => ({
                padding: "8px 10px", borderRadius: 999, fontSize: 13, fontWeight: 600, whiteSpace: "nowrap",
                color: isActive ? "var(--text)" : "var(--text-mute)",
                background: isActive ? "var(--panel-2)" : "transparent",
              })}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="row" style={{ gap: 14 }}>
          {user && STAFF_ROLES.includes(user.role) && (
            <NavLink to="/simulate" className="btn sm report-fire" title="Simulate a fire reported right now">Report a fire</NavLink>
          )}
          <div className="tag-src" style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", lineHeight: 1.2 }}>
            <span style={{ color: "var(--ember-2)" }}>{SOURCE_LABEL[src]}</span>
            <span className="mute">rules-1.0</span>
          </div>
          {user && <NotificationBell staff={STAFF_ROLES.includes(user.role)} />}
          {user && (
            <div className="row" style={{ gap: 10 }}>
              <div style={{ textAlign: "right", lineHeight: 1.2 }}>
                <div className="small">{user.email}</div>
                <div className="small mute" style={{ textTransform: "uppercase", letterSpacing: "0.08em" }}>{user.role}</div>
              </div>
              <button className="btn sm ghost" onClick={() => { logout(); nav("/login"); }}>Logout</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
