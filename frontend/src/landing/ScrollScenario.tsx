import { useEffect, useMemo, useRef, useState } from "react";
import type { Level } from "../api/types";
import { LEVEL_COLOR } from "../api/levels";

/* One incident, told by scrolling. The page scroll drives the fire: a small hotspot while
   the situation is light, a large burning front when it becomes critical. Drawn like a fire
   perimeter map (burned area, active edge, smoke with the wind), not like a cartoon. */

const CW = 1000, CH = 625;          // canvas units; 1 unit = 10 m
const M = 10;
const SITE = { x: 735, y: 285, r: 55 };
const IGNITION = { x: 150, y: 560 };
const FENCE_HIT = { x: SITE.x - 125, y: SITE.y + 105 };   // where the head of the fire ends up
const WIND = { x: 0.72, y: -0.69 };                      // blowing toward the north-east

const STAGES: { at: number; level: Level; time: string; title: string; body: string; did: string[] }[] = [
  {
    at: 0, level: "NORMAL", time: "13:00", title: "A dry afternoon",
    body: "32 °C, 22 % humidity, wind 20 km/h from the south-west. Nothing burning within 25 km of the solar farm.",
    did: ["The site is monitored at every satellite pass"],
  },
  {
    at: 0.2, level: "ELEVATED", time: "14:10", title: "A satellite sees heat 6 km away",
    body: "One VIIRS pixel, 375 m wide, south-west of the site and upwind. On its own it could be a farm burn, so nobody is sent anywhere yet.",
    did: ["Level raised to Elevated", "The control room watches the next pass"],
  },
  {
    at: 0.45, level: "HIGH", time: "16:40", title: "The fire grows toward the site",
    body: "The next passes show a front moving with the wind. Sensors at the forest edge climb past 45 °C. The fire is real and it is coming this way.",
    did: ["Regional control centre notified", "Headcount confirmed with the site manager", "Secondary access route checked"],
  },
  {
    at: 0.7, level: "CRITICAL", time: "18:05", title: "Sensors confirm it at the farmhouse",
    body: "Three sensors report fire. Combined, they put the front about 900 m from the fence, give or take 150 m, more precise than any satellite pixel.",
    did: ["People leave by the secondary route", "The fire service gets the handoff pack with the fire position", "Controlled shutdown prepared"],
  },
];

// Sensors placed like the Engine does: fence, houses, forest edge, open ground
const SENSORS: { x: number; y: number; kind: "fence" | "house" | "forest" | "open" }[] = [
  ...Array.from({ length: 6 }, (_, i) => {
    const a = (i * 60 * Math.PI) / 180;
    return { x: SITE.x + (SITE.r + 10) * Math.sin(a), y: SITE.y - (SITE.r + 10) * Math.cos(a), kind: "fence" as const };
  }),
  { x: 560, y: 420, kind: "house" }, { x: 610, y: 470, kind: "house" }, { x: 845, y: 395, kind: "house" },
  { x: 430, y: 470, kind: "forest" }, { x: 470, y: 360, kind: "forest" }, { x: 395, y: 555, kind: "forest" },
  { x: 540, y: 250, kind: "forest" }, { x: 900, y: 170, kind: "forest" },
  { x: 680, y: 450, kind: "open" }, { x: 640, y: 150, kind: "open" }, { x: 880, y: 290, kind: "open" },
];

const clamp = (v: number, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const ease = (t: number) => t * t * (3 - 2 * t);
function levelAt(p: number): number { let i = 0; STAGES.forEach((s, k) => { if (p >= s.at) i = k; }); return i; }
function noise(u: number) { return 0.75 + 0.25 * Math.sin(u * 17.3) + 0.15 * Math.sin(u * 41.7 + 1.3); }

/** Burned area as overlapping blobs along the spread path; `s` is fire progress 0..1.
 *  A wind-driven fire is narrow where it started and widest toward its head (a teardrop). */
function blobs(s: number) {
  const out: { x: number; y: number; r: number; age: number }[] = [];
  if (s <= 0) return out;
  const N = 140;
  for (let k = 0; k <= N; k++) {
    const u = (k / N) * s;                               // position along the path, 0..s
    const along = u / s;                                 // 0 at ignition, 1 at the head
    const x = IGNITION.x + (FENCE_HIT.x - IGNITION.x) * u + Math.sin(u * 9) * 18;
    const y = IGNITION.y + (FENCE_HIT.y - IGNITION.y) * u + Math.cos(u * 7) * 14;
    const width = (6 + 62 * s) * (0.3 + 0.7 * Math.sqrt(along)) * noise(u);
    out.push({ x, y, r: width * (along > 0.96 ? 0.85 : 1), age: s - u });
    // flank fingers make the edge irregular, as real perimeters are
    const side = Math.sin(u * 23) > 0 ? 1 : -1;
    out.push({ x: x - side * WIND.y * width * 0.55, y: y + side * WIND.x * width * 0.55, r: width * 0.55 * noise(u + 0.37), age: s - u });
  }
  return out;
}

function sensorState(x: number, y: number, bs: ReturnType<typeof blobs>, s: number) {
  if (s <= 0) return { state: "ok" as const, t: 29 };
  let edge = Infinity;
  for (const b of bs) edge = Math.min(edge, Math.hypot(x - b.x, y - b.y) - b.r);
  if (edge < -8) return { state: "offline" as const, t: null };        // inside the burn: gone
  const km = Math.max(0, edge) * M / 1000;
  const t = 29 + 560 * Math.exp(-km / 0.28) * (0.4 + 0.6 * s);
  return { state: t >= 65 ? "fire" as const : t >= 45 ? "warm" as const : "ok" as const, t };
}

const SENSOR_FILL = { ok: "#3FA34D", warm: "#F9A825", fire: "#FF3B30", offline: "#5E5A66" };

export function ScrollScenario() {
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const progress = useRef(0);
  const [p, setP] = useState(0);
  const stage = levelAt(p);

  // scroll -> progress (0 at the first stage, 1 at the end of the last)
  useEffect(() => {
    const onScroll = () => {
      const el = wrap.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const total = r.height - window.innerHeight;
      const v = clamp(-r.top / Math.max(1, total));
      progress.current = v;
      setP((old) => (Math.abs(old - v) > 0.002 ? v : old));
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => { window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onScroll); };
  }, []);

  // drawing loop: the scene follows the scroll, flames flicker only while visible
  useEffect(() => {
    const c = canvas.current!;
    const ctx = c.getContext("2d")!;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    let raf = 0, visible = false, t0 = performance.now();
    const size = () => { c.width = c.clientWidth * dpr; c.height = c.clientHeight * dpr; };
    size();
    const terrain = drawTerrain();
    const burnLayer = document.createElement("canvas");
    const frontLayer = document.createElement("canvas");

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (!visible) return;
      const time = still ? 0 : (now - t0) / 1000;
      const s = ease(clamp((progress.current - 0.15) / 0.8));
      const sx = c.width / CW, sy = c.height / CH;
      ctx.setTransform(sx, 0, 0, sy, 0, 0);
      ctx.drawImage(terrain, 0, 0, CW, CH);
      const bs = blobs(s);
      const intensity = s;                                  // light fire -> small and dim

      // smoke, downwind of the front; thicker as the fire grows
      if (s > 0.02) {
        const head = bs[bs.length - 2];                    // the head (last is a flank finger)
        for (let i = 0; i < 9; i++) {
          const d = 40 + i * (40 + 90 * intensity) + ((time * 14) % 40);
          const x = head.x + WIND.x * d, y = head.y + WIND.y * d;
          const rr = 20 + i * (10 + 30 * intensity);
          const g = ctx.createRadialGradient(x, y, 0, x, y, rr);
          const a = (0.28 * intensity + 0.05) * (1 - i / 10);
          g.addColorStop(0, `rgba(120,118,112,${a})`);
          g.addColorStop(1, "rgba(120,118,112,0)");
          ctx.fillStyle = g;
          ctx.beginPath(); ctx.arc(x, y, rr, 0, Math.PI * 2); ctx.fill();
        }
      }

      if (s > 0) {
        // burned area: one soft-edged shape, charred black with a warm tint where it is fresh
        const L = layer(burnLayer, c);
        L.clearRect(0, 0, CW, CH);
        L.fillStyle = "rgb(24,18,14)";
        for (const b of bs) { L.beginPath(); L.arc(b.x, b.y, b.r, 0, Math.PI * 2); L.fill(); }
        L.globalCompositeOperation = "source-atop";
        for (const b of bs) {
          if (b.age > 0.3) continue;
          L.fillStyle = `rgba(120,45,15,${0.35 * (1 - b.age / 0.3)})`;
          L.beginPath(); L.arc(b.x, b.y, b.r * 0.9, 0, Math.PI * 2); L.fill();
        }
        L.globalCompositeOperation = "source-over";
        ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.filter = "blur(1.5px)"; ctx.globalAlpha = 0.95;
        ctx.drawImage(burnLayer, 0, 0);
        ctx.restore();

        // active front: a single band on the outer edge of the young fire. Light fire =
        // thin and dim; critical = thick, bright, glowing.
        const F = layer(frontLayer, c);
        F.clearRect(0, 0, CW, CH);
        const band = 2 + 9 * intensity;
        const flick = still ? 1 : 0.85 + 0.15 * Math.sin(time * 7);
        F.fillStyle = `rgb(255,${Math.round(70 + 50 * intensity)},24)`;
        for (const b of bs) {
          if (b.age > 0.18) continue;
          F.beginPath(); F.arc(b.x, b.y, b.r + band * 0.35 * flick, 0, Math.PI * 2); F.fill();
        }
        F.globalCompositeOperation = "destination-out";            // hollow it out
        for (const b of bs) { F.beginPath(); F.arc(b.x, b.y, Math.max(0, b.r - band), 0, Math.PI * 2); F.fill(); }
        // the flaming front is the downwind head; the flanks and the tail are dying down
        const head = bs[bs.length - 2], tail = bs[0];
        const fade = F.createLinearGradient(tail.x, tail.y, head.x + WIND.x * head.r, head.y + WIND.y * head.r);
        fade.addColorStop(0, "rgba(0,0,0,0)"); fade.addColorStop(0.55, "rgba(0,0,0,0.25)"); fade.addColorStop(1, "rgba(0,0,0,1)");
        F.globalCompositeOperation = "destination-in";
        F.fillStyle = fade; F.fillRect(0, 0, CW, CH);
        F.globalCompositeOperation = "source-over";
        ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.globalCompositeOperation = "lighter";
        ctx.filter = `blur(${4 + 10 * intensity}px)`; ctx.globalAlpha = 0.5 + 0.4 * intensity;
        ctx.drawImage(frontLayer, 0, 0);                             // glow
        ctx.filter = "blur(0.8px)"; ctx.globalAlpha = 0.55 + 0.45 * intensity;
        ctx.drawImage(frontLayer, 0, 0);                             // core
        ctx.restore();
      }

      // satellite pixels (375 m squares) over the active front, from the first detection on
      if (progress.current >= STAGES[1].at) {
        const px = 37.5, seen = new Set<string>();
        ctx.strokeStyle = "rgba(255,138,61,0.85)"; ctx.lineWidth = 1.2; ctx.setLineDash([4, 3]);
        for (const b of bs) {
          if (b.age > 0.12) continue;
          const gx = Math.floor(b.x / px) * px, gy = Math.floor(b.y / px) * px, key = `${gx},${gy}`;
          if (seen.has(key)) continue;
          seen.add(key); ctx.strokeRect(gx, gy, px, px);
        }
        ctx.setLineDash([]);
      }

      // sensors
      const reads = SENSORS.map((q) => ({ ...q, ...sensorState(q.x, q.y, bs, s) }));
      for (const r of reads) {
        ctx.fillStyle = SENSOR_FILL[r.state];
        ctx.strokeStyle = "rgba(10,14,16,0.9)"; ctx.lineWidth = 2;
        ctx.beginPath();
        if (r.kind === "fence") ctx.rect(r.x - 6, r.y - 6, 12, 12);
        else if (r.kind === "house") { ctx.moveTo(r.x, r.y - 9); ctx.lineTo(r.x + 8, r.y - 2); ctx.lineTo(r.x + 8, r.y + 7); ctx.lineTo(r.x - 8, r.y + 7); ctx.lineTo(r.x - 8, r.y - 2); ctx.closePath(); }
        else if (r.kind === "forest") { ctx.moveTo(r.x, r.y - 9); ctx.lineTo(r.x + 8, r.y + 6); ctx.lineTo(r.x - 8, r.y + 6); ctx.closePath(); }
        else ctx.arc(r.x, r.y, 6, 0, Math.PI * 2);
        ctx.fill(); ctx.stroke();
      }

      // combined fire position once sensors carry the heat
      if (progress.current >= STAGES[3].at) {
        const hot = reads.filter((r) => (r.state === "warm" || r.state === "fire") && r.t !== null);
        if (hot.length) {
          const w = hot.map((r) => Math.max(1, (r.t as number) - 29) ** 2), tw = w.reduce((a, b) => a + b, 0);
          const ex = hot.reduce((a, r, i) => a + r.x * w[i], 0) / tw, ey = hot.reduce((a, r, i) => a + r.y * w[i], 0) / tw;
          ctx.strokeStyle = "#FF3B30"; ctx.lineWidth = 2; ctx.setLineDash([7, 5]);
          ctx.fillStyle = "rgba(255,59,48,0.10)";
          ctx.beginPath(); ctx.arc(ex, ey, 15, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); ctx.setLineDash([]);
          ctx.fillStyle = "#FF3B30"; ctx.beginPath(); ctx.arc(ex, ey, 4.5, 0, Math.PI * 2); ctx.fill();
        }
      }
    };
    raf = requestAnimationFrame(frame);
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; });
    io.observe(c);
    window.addEventListener("resize", size);
    return () => { cancelAnimationFrame(raf); io.disconnect(); window.removeEventListener("resize", size); };
  }, []);

  // numbers that follow the fire
  const s = ease(clamp((p - 0.15) / 0.8));
  const bs = blobs(s);
  let edge = Infinity;
  for (const b of bs) edge = Math.min(edge, Math.hypot(SITE.x - b.x, SITE.y - b.y) - b.r - SITE.r);
  const kmToFence = s > 0 ? Math.max(0, edge) * M / 1000 : null;
  const hectares = useMemo(() => { const q = Math.round(s * 200) / 200; return q > 0 ? Math.round(areaHa(blobs(q))) : 0; }, [s]);
  const cur = STAGES[stage];

  const jump = (i: number) => {
    const el = wrap.current!;
    const total = el.getBoundingClientRect().height - window.innerHeight;
    const top = el.getBoundingClientRect().top + window.scrollY + (STAGES[i].at + 0.04) * total;
    window.scrollTo({ top, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  };

  return (
    <div className="ss" ref={wrap}>
      <div className="ss-sticky">
        <div className="ss-visual">
          <canvas ref={canvas} className="ss-canvas" role="img"
            aria-label={`Map of the solar farm. ${cur.level.toLowerCase()} situation: ${cur.title}.`} />
          <div className="ss-hud" aria-live="polite">
            <span className="ss-level" style={{ background: LEVEL_COLOR[cur.level] }}>{cur.level.toLowerCase()}</span>
            <span>{cur.time}</span>
            <span>{hectares ? `${hectares} ha burned` : "no fire"}</span>
            <span>{kmToFence === null ? "wind 20 km/h from SW" : kmToFence < 0.05 ? "front at the fence" : `front ${kmToFence.toFixed(1)} km from the fence`}</span>
          </div>
          <div className="ss-key" aria-hidden>
            <span><i className="k-burn" />burned</span><span><i className="k-front" />active front</span>
            <span><i className="k-sat" />satellite pixel</span><span><i className="k-est" />sensor fire position</span>
          </div>
        </div>
        <nav className="ss-steps" aria-label="Incident stages">
          {STAGES.map((st, i) => (
            <button key={st.level} className={i === stage ? "on" : i < stage ? "done" : ""} onClick={() => jump(i)}
              aria-current={i === stage ? "step" : undefined}>
              <i style={{ background: i <= stage ? LEVEL_COLOR[st.level] : undefined }} />{st.time}
            </button>
          ))}
        </nav>
      </div>
      <div className="ss-text">
        {STAGES.map((st, i) => (
          <article key={st.level} className={`ss-card ${i === stage ? "on" : ""}`}>
            <div className="ss-card-meta"><span style={{ color: LEVEL_COLOR[st.level] }}>{st.level.toLowerCase()}</span> {st.time}</div>
            <h3>{st.title}</h3>
            <p>{st.body}</p>
            <ul>{st.did.map((d) => <li key={d}>{d}</li>)}</ul>
          </article>
        ))}
      </div>
    </div>
  );
}

/** An offscreen layer the size of the visible canvas, drawn in map units. */
function layer(o: HTMLCanvasElement, c: HTMLCanvasElement) {
  if (o.width !== c.width || o.height !== c.height) { o.width = c.width; o.height = c.height; }
  const g = o.getContext("2d")!;
  g.setTransform(c.width / CW, 0, 0, c.height / CH, 0, 0);
  return g;
}

function areaHa(bs: ReturnType<typeof blobs>) {
  // coarse raster count of the burned blobs, 10 units (100 m) per cell
  let cells = 0;
  const minX = Math.min(...bs.map((b) => b.x - b.r)), maxX = Math.max(...bs.map((b) => b.x + b.r));
  const minY = Math.min(...bs.map((b) => b.y - b.r)), maxY = Math.max(...bs.map((b) => b.y + b.r));
  for (let x = minX; x < maxX; x += 10) for (let y = minY; y < maxY; y += 10)
    if (bs.some((b) => (x - b.x) ** 2 + (y - b.y) ** 2 < b.r * b.r)) cells++;
  return cells * 1;                              // one 100 m x 100 m cell = 1 ha
}

/** The static map under the fire: forest, farmland, a road, the river, the site. */
function drawTerrain() {
  const o = document.createElement("canvas");
  o.width = CW * 2; o.height = CH * 2;
  const g = o.getContext("2d")!;
  g.scale(2, 2);
  g.fillStyle = "#1A232A"; g.fillRect(0, 0, CW, CH);
  const patch = (pts: number[][], color: string) => {
    g.fillStyle = color; g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
    for (const [x, y] of pts.slice(1)) g.lineTo(x, y);
    g.closePath(); g.fill();
  };
  patch([[0, 330], [210, 280], [360, 330], [520, 300], [560, 420], [470, 625], [0, 625]], "#1F3A2B");   // pine forest
  patch([[520, 0], [700, 0], [640, 170], [520, 230], [430, 150]], "#1F3A2B");
  patch([[830, 90], [1000, 40], [1000, 250], [900, 230]], "#1F3A2B");
  patch([[560, 420], [760, 380], [980, 470], [1000, 625], [470, 625]], "#2A2F22");                      // farmland
  patch([[0, 0], [430, 0], [430, 150], [210, 280], [0, 330]], "#232B24");                                 // scrub
  g.strokeStyle = "#2C4A5E"; g.lineWidth = 6; g.beginPath();                                             // river
  g.moveTo(0, 190); g.bezierCurveTo(250, 170, 380, 250, 520, 230); g.bezierCurveTo(700, 200, 820, 260, 1000, 320); g.stroke();
  g.strokeStyle = "#4A4640"; g.lineWidth = 2.5; g.setLineDash([]); g.beginPath();                        // road
  g.moveTo(1000, 560); g.bezierCurveTo(850, 500, 800, 380, SITE.x + 30, SITE.y + 50); g.stroke();
  // solar farm: rows of panels inside the fence
  g.save(); g.beginPath(); g.arc(SITE.x, SITE.y, SITE.r, 0, Math.PI * 2); g.clip();
  g.fillStyle = "#12202E"; g.fillRect(SITE.x - SITE.r, SITE.y - SITE.r, SITE.r * 2, SITE.r * 2);
  g.fillStyle = "#2B4766";
  for (let y = SITE.y - SITE.r + 4; y < SITE.y + SITE.r; y += 9) g.fillRect(SITE.x - SITE.r, y, SITE.r * 2, 5);
  g.restore();
  g.strokeStyle = "#8C95A1"; g.lineWidth = 1.2; g.beginPath(); g.arc(SITE.x, SITE.y, SITE.r, 0, Math.PI * 2); g.stroke();
  g.fillStyle = "#ECE7E0"; g.font = "600 14px Inter, sans-serif"; g.textAlign = "center";
  g.fillText("Solar farm", SITE.x, SITE.y - SITE.r - 24);
  // scale bar
  g.fillStyle = "#8C95A1"; g.fillRect(870, 598, 100, 3);                                                // scale bar
  g.font = "12px Inter, sans-serif"; g.textAlign = "right"; g.fillText("1 km", 970, 590);
  // north arrow
  g.beginPath(); g.moveTo(960, 30); g.lineTo(968, 50); g.lineTo(960, 45); g.lineTo(952, 50); g.closePath(); g.fill();
  g.textAlign = "center"; g.fillText("N", 960, 66);
  // wind: from the south-west, toward the north-east
  g.strokeStyle = "#8C95A1"; g.lineWidth = 2; g.beginPath();
  g.moveTo(860, 58); g.lineTo(892, 26); g.moveTo(892, 26); g.lineTo(879, 28); g.moveTo(892, 26); g.lineTo(890, 39); g.stroke();
  g.textAlign = "right"; g.fillText("wind 20 km/h", 885, 76);
  return o;
}
