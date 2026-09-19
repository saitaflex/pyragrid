import { useEffect, useRef, useState } from "react";
import { BRAND } from "../brand";
import "./dragon.css";
import { Burn } from "./burn";

/* The PyraGrid dragon wakes as you scroll: its eyes open in the dark, the night draws back
   to paper, the three heads lift off and breathe fire one after the other. Each head stands
   for one part of the platform (watch, locate, act). Ported from the PyraGrid intro page. */

const W = 473;                                          // logo width in its own pixels
const D = "/brand/dragon/";
const HEADS = { l: [19.662, 19.501, 17.759], c: [39.112, 13.152, 18.605], r: [60.888, 20.635, 18.605] } as const;
const FLAMES = { l: [4.44, 19.274, 15.856], c: [56.448, 2.494, 10.571], r: [78.858, 20.862, 16.49] } as const;
const EYE_TOPS = [53.061, 58.957, 64.853, 70.748];
const ATTACH = { l: [25, 21], c: [9, 35], r: [-20, 25] } as const;     // head back on its neck
const RECOIL = { l: [1, 0], c: [-0.6, 0.8], r: [-1, 0] } as const;     // away from the flame
const ORIGIN = { l: "100% 55%", c: "0% 96%", r: "0% 50%" } as const;

const CAPTIONS: { title: string; body: string }[] = [
  { title: "", body: "Scroll to wake it" },
  { title: "The first head watches.", body: "NASA satellites on every pass, and ground sensors on the fences, farmhouses and forest edges around each site." },
  { title: "The second head locates.", body: "Distance, wind and fuel become one risk level per site, and hot sensors are combined into one fire position." },
  { title: "The third head acts.", body: "Your protocol and an AI response plan reach the control room, the fire service and the people nearby the moment a site turns critical." },
];

const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const smooth = (x: number, a: number, b: number) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
const backOut = (t: number) => { const s = 1.9; t -= 1; return t * t * ((s + 1) * t + s) + 1; };

export function DragonIntro({ onDemo, busy }: { onDemo: () => void; busy: boolean }) {
  const scene = useRef<HTMLElement>(null);
  const art = useRef<HTMLDivElement>(null);
  const paper = useRef<HTMLDivElement>(null);
  const heads = useRef<Record<string, HTMLImageElement | null>>({});
  const flames = useRef<Record<string, HTMLDivElement | null>>({});
  const pupils = useRef<(HTMLImageElement | null)[]>([]);
  const snaps = useRef<HTMLImageElement>(null);
  const glow = useRef<HTMLDivElement>(null);
  const burnCanvas = useRef<HTMLCanvasElement>(null);
  const burn = useRef<Burn | null>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const [cap, setCap] = useState(0);
  const [lit, setLit] = useState([false, false, false]);
  const [eyes, setEyes] = useState<"closed" | "open" | "blink">("closed");
  const [revealed, setRevealed] = useState(false);
  const revealedRef = useRef(false);
  const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // the night draws back from the chest eyes to paper
  const reveal = (instant: boolean) => {
    if (revealedRef.current) return;
    revealedRef.current = true;
    setEyes("open");
    const done = () => { setRevealed(true); if (paper.current) paper.current.style.clipPath = "none"; };
    const box = art.current?.getBoundingClientRect(), stage = scene.current?.querySelector(".dr-stage")?.getBoundingClientRect();
    if (instant || !box || !stage || !paper.current) return done();
    const cx = box.left - stage.left + box.width * (231 / W), cy = box.top - stage.top + box.height * (282 / 441);
    const end = Math.hypot(Math.max(cx, stage.width - cx), Math.max(cy, stage.height - cy)) + 40;
    const t0 = performance.now(), dur = 1300;
    const step = (now: number) => {
      const t = clamp((now - t0) / dur), e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      if (paper.current) paper.current.style.clipPath = `circle(${e * end}px at ${cx}px ${cy}px)`;
      if (t < 1) requestAnimationFrame(step); else done();
    };
    requestAnimationFrame(step);
  };

  // intro: eyes open one by one in the dark, blink, then the reveal
  useEffect(() => {
    if (reduce) { reveal(true); return; }
    const timers = [
      window.setTimeout(() => setEyes("open"), 700),
      window.setTimeout(() => setEyes("blink"), 1700),
      window.setTimeout(() => setEyes("open"), 1800),
      window.setTimeout(() => reveal(false), 2250),
    ];
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // scroll drives the heads, the flames and the captions
  useEffect(() => {
    let ticking = false;
    const render = () => {
      ticking = false;
      const el = scene.current, a = art.current;
      if (!el || !a) return;
      const u = a.getBoundingClientRect().width / W;
      const r = el.getBoundingClientRect(), max = r.height - window.innerHeight;
      const total = reduce ? 1 : max > 0 ? clamp(-r.top / max) : 1;
      const p = reduce ? 1 : clamp(total / 0.66);                 // the dragon
      const q = reduce ? 0 : clamp((total - 0.7) / 0.3);          // the fire that ends the intro
      burn.current?.set(q);
      el.classList.toggle("gone", q >= 0.47);                 // covered by fire: hide it all
      el.classList.toggle("burnt", q >= 0.95);
      if (p > 0.02 && !revealedRef.current) reveal(true);
      const lift = smooth(p, 0.04, 0.17);
      const fire = { l: smooth(p, 0.24, 0.33), c: smooth(p, 0.44, 0.53), r: smooth(p, 0.64, 0.73) };
      (["l", "c", "r"] as const).forEach((k) => {
        const [ax, ay] = ATTACH[k], pop = Math.sin(Math.PI * lift) * 5, rec = Math.sin(Math.PI * fire[k]) * 3;
        const x = ax * (1 - lift) + RECOIL[k][0] * rec, y = ay * (1 - lift) - pop + RECOIL[k][1] * rec;
        const h = heads.current[k];
        if (h) h.style.transform = `translate(${x * u}px, ${y * u}px)`;
        const f = flames.current[k];
        if (f) { f.style.transform = `scale(${fire[k] === 0 ? 0 : backOut(fire[k])})`; f.style.opacity = String(clamp(fire[k] * 3)); }
      });
      if (snaps.current) snaps.current.style.opacity = String(smooth(p, 0.12, 0.19));
      if (glow.current) glow.current.style.opacity = String((fire.l + fire.c + fire.r) / 3);
      setCap(p < 0.22 ? 0 : p < 0.43 ? 1 : p < 0.63 ? 2 : p < 0.84 ? 3 : 4);
      setLit([fire.l > 0.6, fire.c > 0.6, fire.r > 0.6]);
    };
    const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(render); } };
    if (burnCanvas.current && !reduce) burn.current = new Burn(burnCanvas.current, "/media/hero.webp");
    const onResize = () => { burn.current?.resize(); onScroll(); };
    render();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);
    const onKey = (e: KeyboardEvent) => { if (!revealedRef.current && e.key !== "Tab") reveal(true); };
    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onResize); window.removeEventListener("keydown", onKey); burn.current?.destroy(); burn.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // the pupils follow the pointer; the eyes blink now and then
  useEffect(() => {
    if (reduce) return;
    const move = (ev: PointerEvent) => {
      const a = art.current;
      if (!a) return;
      const r = a.getBoundingClientRect(), u = r.width / W;
      const dx = ev.clientX - (r.left + r.width * (231 / W)), dy = ev.clientY - (r.top + r.height * (282 / 441));
      const d = Math.hypot(dx, dy) || 1, m = Math.min(1, d / 300) * 2.2 * u;
      pupils.current.forEach((pp) => { if (pp) pp.style.transform = `translate(${(dx / d) * m}px, ${(dy / d) * m * 0.5}px)`; });
    };
    window.addEventListener("pointermove", move, { passive: true });
    let t = 0;
    const next = () => { t = window.setTimeout(() => { if (revealedRef.current) { setEyes("blink"); window.setTimeout(() => setEyes("open"), 110); } next(); }, 4500 + Math.random() * 4500); };
    next();
    return () => { window.removeEventListener("pointermove", move); clearTimeout(t); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const skip = () => { reveal(true); const next = scene.current?.nextElementSibling; next?.scrollIntoView({ behavior: reduce ? "auto" : "smooth" }); };

  return (
    <section ref={scene} className={`dr ${revealed ? "revealed" : ""} ${reduce ? "still" : ""}`} aria-label={`${BRAND.name} introduction`}>
      <div className="dr-stage" ref={stageRef}>
        <div className="dr-night" aria-hidden />
        <div ref={paper} className="dr-paper" aria-hidden />
        <div ref={glow} className="dr-glow" aria-hidden />
        <header className="dr-head">
          <span className="dr-mark">{BRAND.name}</span>
          <span className="dr-head-links">
            <a href="/login" className="dr-link">Sign in</a>
            <button type="button" className="dr-skip" onClick={skip}>Skip intro</button>
          </span>
        </header>

        <div className="dr-art">
          <div ref={art} className={`dr-dragon ${!revealed ? "glowing" : ""}`} role="img"
            aria-label={`${BRAND.name} logo: a three-headed dragon with four eyes on its chest, each head breathing fire`}>
            {(["l", "c", "r"] as const).map((k) => (
              <div key={k} ref={(el) => { flames.current[k] = el; }} className={`dr-layer dr-flame ${lit["lcr".indexOf(k)] ? "lit" : ""}`}
                style={{ left: `${FLAMES[k][0]}%`, top: `${FLAMES[k][1]}%`, width: `${FLAMES[k][2]}%`, transformOrigin: ORIGIN[k] }}>
                <img src={`${D}flame_${k}.png`} alt="" style={{ transformOrigin: ORIGIN[k], animationDelay: k === "c" ? "-.4s" : k === "r" ? "-.7s" : "0s" }} />
              </div>
            ))}
            <img className="dr-layer" src={`${D}body.png`} alt="" style={{ left: "4.863%", top: "37.415%", width: "89.218%" }} />
            <img ref={snaps} className="dr-layer dr-snaps" src={`${D}snaps.png`} alt="" style={{ left: "31.501%", top: "34.467%", width: "34.249%" }} />
            {(["l", "c", "r"] as const).map((k) => (
              <img key={k} ref={(el) => { heads.current[k] = el; }} className="dr-layer" src={`${D}head_${k}.png`} alt=""
                style={{ left: `${HEADS[k][0]}%`, top: `${HEADS[k][1]}%`, width: `${HEADS[k][2]}%` }} />
            ))}
            {EYE_TOPS.map((top, i) => (
              <span key={i} className={`dr-eye ${eyes !== "closed" ? "open" : ""} ${eyes === "blink" ? "blink" : ""}`}
                style={{ left: "45.243%", top: `${top}%`, width: "7.4%", transitionDelay: eyes === "open" && !revealed ? `${i * 170}ms` : undefined }}>
                <img src={`${D}eye${i + 1}.png`} alt="" />
                <img ref={(el) => { pupils.current[i] = el; }} className="dr-pupil" src={`${D}pupil${i + 1}.png`} alt="" />
              </span>
            ))}
          </div>
        </div>

        <div className="dr-captions" aria-live="polite">
          {CAPTIONS.map((c, i) => (
            <div key={i} className={`dr-cap ${cap === i ? "on" : ""} ${i === 0 ? "hint" : ""}`}>
              {c.title && <h2>{c.title}</h2>}
              <p>{c.body}</p>
              {i === 0 && <span className="dr-cue" aria-hidden />}
            </div>
          ))}
          <div className={`dr-cap final ${cap === 4 ? "on" : ""}`}>
            <h2>{BRAND.name}</h2>
            <p>Wildfire intelligence for companies with sites in fire country.</p>
            <div className="dr-actions">
              <button type="button" className="dr-btn" disabled={busy} onClick={onDemo}>{busy ? "Opening…" : "Open the live demo"}</button>
              <a className="dr-btn quiet" href="#story">See how it works</a>
            </div>
          </div>
        </div>
        <div className="dr-progress" aria-hidden>{lit.map((on, i) => <i key={i} className={on ? "on" : ""} />)}</div>
        <canvas ref={burnCanvas} className="dr-burn" aria-hidden />
      </div>
    </section>
  );
}
