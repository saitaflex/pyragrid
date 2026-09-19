import { useEffect, useMemo, useRef, useState } from "react";
import { LEVEL_COLOR, SENSOR_COLOR, SENSOR_LABEL } from "../api/levels";
import { SensorShape } from "../components/Sensors";
import {
  ACTIONS, DESTROY_C, FIRE_START, H, SITE, W, distanceKm, estimate, level, readings,
} from "./sim";

const SAT_PX = 375 / 12;
// a light situation shows a small, dim fire; a critical one a large, bright front
const FIRE_R = { NORMAL: 20, ELEVATED: 30, HIGH: 48, CRITICAL: 72 } as const;
const FIRE_A = { NORMAL: 0.55, ELEVATED: 0.7, HIGH: 0.85, CRITICAL: 1 } as const;   // a VIIRS pixel is ~375 m: a coarse square on this map

/** Drag the fire (or press play) and watch sensors, the combined position and the
 *  protocol react. Keyboard: focus the fire and use the arrow keys. */
export function FirePlay() {
  const [fire, setFire] = useState(FIRE_START);
  const [burned, setBurned] = useState<Set<string>>(new Set());
  const [playing, setPlaying] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const dragging = useRef(false);

  const rs = useMemo(() => readings(fire.x, fire.y, burned), [fire, burned]);
  const est = useMemo(() => estimate(rs), [rs]);
  const lvl = level(fire.x, fire.y);
  const km = distanceKm(fire.x, fire.y);

  // sensors that read ≥150 °C melt and stay silent
  useEffect(() => {
    const melt = rs.filter((r) => r.temp !== null && r.temp >= DESTROY_C).map((r) => r.id);
    if (melt.length) setBurned((b) => new Set([...b, ...melt]));
  }, [rs]);

  // play: the fire walks toward the site along the wind
  useEffect(() => {
    if (!playing) return;
    const t = window.setInterval(() => {
      setFire((f) => {
        const dx = SITE.x - 40 - f.x, dy = SITE.y + 40 - f.y;
        const d = Math.hypot(dx, dy);
        if (d < 6) { setPlaying(false); return f; }
        return { x: f.x + (dx / d) * 4, y: f.y + (dy / d) * 4 };
      });
    }, 60);
    return () => window.clearInterval(t);
  }, [playing]);

  const toSvg = (e: React.PointerEvent) => {
    const r = svg.current!.getBoundingClientRect();
    return {
      x: Math.min(W - 10, Math.max(10, ((e.clientX - r.left) / r.width) * W)),
      y: Math.min(H - 10, Math.max(10, ((e.clientY - r.top) / r.height) * H)),
    };
  };
  const reset = () => { setPlaying(false); setBurned(new Set()); setFire(FIRE_START); };
  const onKey = (e: React.KeyboardEvent) => {
    const step = e.shiftKey ? 30 : 10;
    const d = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[e.key];
    if (!d) return;
    e.preventDefault();
    setPlaying(false);
    setFire((f) => ({ x: Math.min(W - 10, Math.max(10, f.x + d[0])), y: Math.min(H - 10, Math.max(10, f.y + d[1])) }));
  };

  const hot = rs.filter((r) => r.state === "fire").length;
  const warm = rs.filter((r) => r.state === "warm").length;
  const dead = rs.filter((r) => r.state === "offline").length;
  const hovered = rs.find((r) => r.id === hover);
  // critical sites keep the high-level actions too
  const actions = lvl === "CRITICAL" ? [...ACTIONS.HIGH, ...ACTIONS.CRITICAL] : ACTIONS[lvl];
  // the satellite pixel snaps to a coarse grid: that is all a satellite can say
  const sat = { x: Math.floor(fire.x / SAT_PX) * SAT_PX, y: Math.floor(fire.y / SAT_PX) * SAT_PX };

  return (
    <div className="fp">
      <div className="fp-stage">
        <svg ref={svg} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Toy map of a solar site with ground sensors and a movable fire"
          onPointerMove={(e) => { if (dragging.current) setFire(toSvg(e)); }}
          onPointerUp={() => { dragging.current = false; }} onPointerLeave={() => { dragging.current = false; }}>
          <defs>
            <radialGradient id="fp-glow"><stop offset="0" stopColor="#FFB14A" stopOpacity=".9" /><stop offset=".4" stopColor="#FF5A1F" stopOpacity=".45" /><stop offset="1" stopColor="#FF5A1F" stopOpacity="0" /></radialGradient>
            <pattern id="fp-panels" width="10" height="7" patternUnits="userSpaceOnUse"><rect width="9" height="6" fill="#20324A" /></pattern>
          </defs>
          {/* terrain: forest to the west, scrub to the south, the valley with the site */}
          <path d="M0,0 H330 C300,120 250,230 290,330 C320,410 300,480 300,480 H0 Z" fill="#1D3A2C" opacity=".55" />
          <path d="M300,480 C330,420 380,380 470,400 C560,420 600,480 600,480 Z" fill="#3B3A24" opacity=".45" />
          <path d="M600,0 H800 V160 C730,170 680,120 600,0 Z" fill="#1D3A2C" opacity=".45" />
          {/* wind */}
          <g className="fp-wind" aria-hidden>
            {[0, 1, 2].map((i) => <path key={i} d={`M${60 + i * 60},${150 + i * 26} l40,-40 m0,0 l-14,2 m14,-2 l-2,14`} stroke="#8C95A1" strokeWidth="1.6" fill="none" opacity=".55" />)}
            <text x="56" y="210" fill="#8C95A1" fontSize="12">wind from SW</text>
          </g>
          {/* the site */}
          <circle cx={SITE.x} cy={SITE.y} r={SITE.r} fill="url(#fp-panels)" stroke={LEVEL_COLOR[lvl]} strokeWidth="2" opacity=".95" />
          <text x={SITE.x} y={SITE.y - SITE.r - 20} textAnchor="middle" fill="#ECE7E0" fontSize="13" fontWeight="600">Solar farm</text>
          {/* satellite pixel */}
          <rect x={sat.x} y={sat.y} width={SAT_PX} height={SAT_PX} fill="none" stroke="#FF8A3D" strokeWidth="1.5" strokeDasharray="3 3" />
          {/* the fire */}
          <circle cx={fire.x} cy={fire.y} r={FIRE_R[lvl]} fill="url(#fp-glow)" className="fp-flicker" style={{ opacity: FIRE_A[lvl] }} />
          {/* sensors */}
          {rs.map((r) => (
            <g key={r.id} transform={`translate(${r.x - 12},${r.y - 12})`} onPointerEnter={() => setHover(r.id)} onPointerLeave={() => setHover(null)}>
              <circle cx="12" cy="12" r="22" fill={SENSOR_COLOR[r.state]} opacity={r.state === "ok" ? 0.08 : 0.2} />
              <svg width="24" height="24" viewBox="0 0 22 22"><SensorPath kind={r.kind} color={SENSOR_COLOR[r.state]} /></svg>
            </g>
          ))}
          {/* combined position */}
          {est && (
            <g>
              <circle cx={est.x} cy={est.y} r={est.r} fill="#FF3B30" fillOpacity=".12" stroke="#FF3B30" strokeWidth="2" strokeDasharray="6 4" />
              <circle cx={est.x} cy={est.y} r="5" fill="#FF3B30" stroke="#fff" strokeWidth="2" />
            </g>
          )}
          {/* drag handle */}
          <g className="fp-handle" tabIndex={0} role="slider" aria-label="Fire position. Use arrow keys to move it."
            aria-valuetext={`${km.toFixed(1)} km from the site`}
            onPointerDown={(e) => { dragging.current = true; setPlaying(false); (e.target as Element).setPointerCapture?.(e.pointerId); }}
            onKeyDown={onKey}>
            <circle cx={fire.x} cy={fire.y} r="16" fill="#FF5A1F" stroke="#fff" strokeWidth="2.5" />
            <path d={`M${fire.x},${fire.y - 8} c5,5 7,8 4,12 c-2,3 -6,3 -8,0 c-2,-3 0,-6 4,-12 z`} fill="#fff" />
          </g>
          {!playing && fire.x === FIRE_START.x && fire.y === FIRE_START.y && (
            <text x={fire.x + 24} y={fire.y + 5} fill="#ECE7E0" fontSize="13" className="fp-hint">Drag the fire</text>
          )}
          {hovered && (
            <g transform={`translate(${Math.min(hovered.x + 14, W - 190)},${Math.max(hovered.y - 44, 8)})`} pointerEvents="none">
              <rect width="180" height="38" rx="8" fill="#0F1519" stroke="#2A3640" />
              <text x="10" y="16" fill="#ECE7E0" fontSize="12" fontWeight="600">{hovered.place}</text>
              <text x="10" y="30" fill={SENSOR_COLOR[hovered.state]} fontSize="12">{SENSOR_LABEL[hovered.state]}{hovered.temp !== null ? `, ${hovered.temp}°C` : ""}</text>
            </g>
          )}
        </svg>
        <div className="fp-controls">
          <button className="lp-btn" onClick={() => setPlaying((p) => !p)}>{playing ? "Pause" : "Let it spread"}</button>
          <button className="lp-btn quiet" onClick={reset}>Reset</button>
        </div>
      </div>

      <div className="fp-read" aria-live="polite">
        <div className="fp-level" style={{ color: LEVEL_COLOR[lvl], borderColor: LEVEL_COLOR[lvl] }}>
          <span className="fp-level-name">{lvl.toLowerCase()}</span>
          <span className="fp-level-km">{km < 0.05 ? "at the fence" : `${km.toFixed(1)} km from the fence`}</span>
        </div>
        <dl className="fp-facts">
          <div><dt>Satellite</dt><dd>one hotspot, a 375 m square</dd></div>
          <div><dt>Ground sensors</dt><dd>{hot || warm || dead ? `${hot} fire, ${warm} warm, ${dead} silent` : "all normal"}</dd></div>
          <div><dt>Fire position</dt><dd>{est ? `combined from ${est.n} sensor${est.n > 1 ? "s" : ""}, ±${Math.round(est.r * 12)} m` : "not sensed on the ground yet"}</dd></div>
        </dl>
        <div className="fp-actions">
          <div className="fp-actions-title">What the protocol asks for</div>
          {actions.length ? <ul>{actions.map((a) => <li key={a}>{a}</li>)}</ul>
            : <p>Nothing yet. Move the fire closer.</p>}
        </div>
        <div className="fp-legend">
          {(["structure", "vegetation", "fence", "grid"] as const).map((k) => (
            <span key={k}><SensorShape kind={k} color="#8C95A1" size={13} />{{ structure: "house", vegetation: "forest edge", fence: "fence", grid: "open ground" }[k]}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

function SensorPath({ kind, color }: { kind: "structure" | "vegetation" | "fence" | "grid"; color: string }) {
  const d = {
    structure: "M11 2 L20 10 L17 10 L17 19 L5 19 L5 10 L2 10 Z",
    vegetation: "M11 1.5 L19 15 L13 15 L13 20 L9 20 L9 15 L3 15 Z",
    fence: "M5 5 H17 V17 H5 Z",
    grid: "M18 11 A7 7 0 1 1 4 11 A7 7 0 1 1 18 11 Z",
  }[kind];
  return <path d={d} fill={color} stroke="rgba(10,14,16,.9)" strokeWidth="1.6" strokeLinejoin="round" />;
}
