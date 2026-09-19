import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../state/AuthContext";
import { BRAND } from "../brand";
import { BrandMark } from "../components/BrandMark";

const DEMO = [
  ["admin@demo.eu", "company admin"],
  ["operator@demo.eu", "operator"],
  ["ana@demo.eu", "operator (shift lead)"],
  ["fire@demo.eu", "fire service"],
  ["gov@demo.eu", "civil protection"],
  ["ngo@demo.eu", "NGO"],
  ["other@othercorp.eu", "other company"],
];

export function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("admin@demo.eu");
  const [password, setPassword] = useState("demo1234");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try { await login(email, password); nav("/"); } // partners are redirected to /situation
    catch (e2) { setErr((e2 as Error).message === "invalid credentials" ? "Invalid credentials" : "Login failed"); }
    finally { setBusy(false); }
  };

  return (
    <div style={{ minHeight: "100vh", display: "grid", gridTemplateColumns: "1.1fr 0.9fr" }} className="login-wrap">
      <div style={{ position: "relative", overflow: "hidden", borderRight: "1px solid var(--border)", padding: "56px 5vw", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        <motion.div initial={{ opacity: 0, scale: 1.1 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1.4 }}
          style={{ position: "absolute", inset: 0, zIndex: -1, background: "radial-gradient(40rem 40rem at 30% 20%, rgba(255,90,31,0.22), transparent 55%), radial-gradient(30rem 30rem at 80% 90%, rgba(198,40,40,0.2), transparent 55%)" }} />
        <div className="row" style={{ gap: 12 }}>
          <BrandMark size={44} />
          <span className="display" style={{ fontSize: 24 }}>{BRAND.name}</span>
        </div>
        <div>
          <motion.div className="eyebrow" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            {BRAND.tagline}
          </motion.div>
          <motion.h1 className="display" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            style={{ fontSize: "clamp(38px, 6vw, 74px)", margin: "14px 0" }}>
            Hundreds of detections.<br />One action list.
          </motion.h1>
          <motion.p className="dim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} style={{ maxWidth: 460, fontSize: 16 }}>
            Near-real-time exposure for critical energy assets — transparent scoring, protocol
            actions, a grounded AI advisor and a firefighter handoff pack.
          </motion.p>
        </div>
        <div className="small mute">MVP decision-support model, not a validated prediction model. Demo data is simulated.</div>
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 6vw" }}>
        <motion.form onSubmit={submit} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }} style={{ width: "100%", maxWidth: 380 }}>
          <h2 style={{ fontSize: 26, marginBottom: 6 }}>Sign in</h2>
          <p className="dim small" style={{ marginBottom: 22 }}>Use a demo account below.</p>
          <div style={{ marginBottom: 14 }}>
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
          </div>
          <div style={{ marginBottom: 18 }}>
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </div>
          {err && <div style={{ color: "var(--critical-hot)", fontSize: 13, marginBottom: 12 }}>{err}</div>}
          <button className="btn primary" style={{ width: "100%", justifyContent: "center" }} disabled={busy}>
            {busy ? <span className="spinner" /> : "Enter the console"}
          </button>
          <div className="divider" />
          <div className="small mute" style={{ marginBottom: 8 }}>Demo accounts · password <span className="mono">demo1234</span></div>
          <div className="grid" style={{ gap: 6 }}>
            {DEMO.map(([e, role]) => (
              <button type="button" key={e} className="btn sm ghost" style={{ justifyContent: "space-between" }} onClick={() => { setEmail(e); setPassword("demo1234"); }}>
                <span className="mono">{e}</span><span className="mute">{role}</span>
              </button>
            ))}
          </div>
        </motion.form>
      </div>
    </div>
  );
}
