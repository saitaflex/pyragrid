import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../state/AuthContext";
import { BRAND } from "../brand";
import { BrandMark } from "../components/BrandMark";
import { Embers } from "./Embers";
import { FirePlay } from "./FirePlay";
import { ScrollScenario } from "./ScrollScenario";
import "./landing.css";

const ROLES = [
  { email: "admin@demo.eu", who: "Company control room", enter: "Enter as the control room", sees: "Every site, alerts, protocol rules, drills and the AI advisor.", to: "/" },
  { email: "fire@demo.eu", who: "Fire service", enter: "Enter as the fire service", sees: "Fire position, sensors, people on site, access routes and the handoff pack. No company finances.", to: "/situation" },
  { email: "gov@demo.eu", who: "Civil protection", enter: "Enter as civil protection", sees: "Risk around every site and how many people are there.", to: "/situation" },
  { email: "ngo@demo.eu", who: "NGO or community", enter: "Enter as an NGO", sees: "The public picture: fires, sensors and risk levels.", to: "/situation" },
];

export function LandingPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState("");

  const enter = async (email: string, to: string) => {
    setBusy(email); setErr("");
    try { await login(email, "demo1234"); nav(to); }
    catch { setErr("The demo account could not sign in. Try the sign-in page."); }
    finally { setBusy(null); }
  };

  return (
    <div className="lp">
      <header className="lp-hero">
        <div className="lp-hero-img" role="img" aria-label="A solar farm in the Galician hills at dusk with a wildfire burning on the far ridge" />
        <Embers />
        <div className="lp-hero-shade" />
        <nav className="lp-nav">
          <span className="lp-brand"><BrandMark size={22} />{BRAND.name}</span>
          <Link to="/login" className="lp-link">Sign in</Link>
        </nav>
        <div className="lp-hero-copy">
          <h1>Know where the fire is before it reaches your site.</h1>
          <p>Satellite detections, ground sensors and your own emergency protocol on one screen, for the control room, the fire service and the people who live nearby.</p>
          <div className="lp-cta">
            <button className="lp-btn" disabled={!!busy} onClick={() => enter("admin@demo.eu", "/")}>
              {busy === "admin@demo.eu" ? "Opening…" : "Open the live demo"}
            </button>
            <a className="lp-btn quiet" href="#story">See how it works</a>
          </div>
          {err && <p className="lp-err">{err}</p>}
        </div>
        <p className="lp-credit">Illustration generated with AI. Demo data is simulated.</p>
      </header>

      <section className="lp-section" id="story">
        <div className="lp-head">
          <h2>One fire, hour by hour</h2>
          <p>Scroll to follow a simulated incident near a solar farm. The fire stays small while the situation is light and grows as it becomes serious. At each step you see what the platform knows and what the team does.</p>
        </div>
        <ScrollScenario />
      </section>

      <section className="lp-section" id="try">
        <div className="lp-head">
          <h2>Now move the fire yourself</h2>
          <p>A satellite only sees a 375&nbsp;m square. Sensors on real places around the site feel the heat and are combined into one position. When a sensor burns, it goes silent, and that is information too.</p>
        </div>
        <FirePlay />
      </section>

      <section className="lp-section lp-split">
        <figure className="lp-photo">
          <img src="/media/sensor.webp" alt="A small solar-powered temperature sensor on a wooden post at the edge of a pine forest" width="1200" height="900" />
          <figcaption>Illustration generated with AI.</figcaption>
        </figure>
        <div>
          <h2>Sensors go where fire meets people</h2>
          <p>Each site gets a few dozen small solar-powered sensors, placed from OpenStreetMap: on the fence, at farmhouses and cabins, and along the forest and scrub edge where a fire arrives. They are optional, and the platform works from satellites alone.</p>
          <ul className="lp-states">
            <li><i style={{ background: "#3FA34D" }} />Normal</li>
            <li><i style={{ background: "#F9A825" }} />Warm, 45&nbsp;°C or more</li>
            <li><i style={{ background: "#FF3B30" }} />Fire, 65&nbsp;°C or more</li>
            <li><i style={{ background: "#6F6B78" }} />Silent: burned or out of battery</li>
            <li><i style={{ background: "#4FC3F7" }} />Moved or knocked over</li>
          </ul>
        </div>
      </section>

      <section className="lp-section">
        <div className="lp-head">
          <h2>One picture, shared with the right people</h2>
          <p>Everyone sees the same fire. Each organisation only sees what it needs. Pick a role to enter the demo as them.</p>
        </div>
        <div className="lp-roles">
          {ROLES.map((r) => (
            <button key={r.email} className="lp-role" disabled={!!busy} onClick={() => enter(r.email, r.to)}>
              <strong>{r.who}</strong>
              <span>{r.sees}</span>
              <em>{busy === r.email ? "Opening…" : r.enter}</em>
            </button>
          ))}
        </div>
      </section>

      <section className="lp-section lp-split reverse">
        <div>
          <h2>Practise before the real one</h2>
          <p>An admin starts a drill on a real site. Signals arrive one by one, every employee gets a drill alert on their screen, and each person chooses what they would do. The scoreboard shows who reacted fast and who picked the right actions.</p>
          <button className="lp-btn" disabled={!!busy} onClick={() => enter("admin@demo.eu", "/drills")}>
            {busy === "admin@demo.eu" ? "Opening…" : "Start a drill"}
          </button>
        </div>
        <figure className="lp-photo">
          <img src="/media/control.webp" alt="Operators in a control room in front of a wall-sized wildfire map" width="1600" height="900" />
          <figcaption>Illustration generated with AI.</figcaption>
        </figure>
      </section>

      <footer className="lp-foot">
        <p>Fire data: NASA FIRMS VIIRS detections, or a clearly labelled synthetic fallback. Weather: Open-Meteo. Map data © OpenStreetMap contributors. Sites, people, sensors and protocols in this demo are simulated. The risk score supports decisions; it is not a validated prediction model, and the fire service decides all firefighting actions.</p>
        <Link to="/login" className="lp-link">Sign in with a demo account</Link>
      </footer>
    </div>
  );
}
