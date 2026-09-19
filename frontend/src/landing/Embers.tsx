import { useEffect, useRef } from "react";

/** Embers rising from a fire. (fireX, fireY) is where the fire is, as fractions of the photo
 *  (aspect > 0, cover-fitted) or of the box itself (aspect = 0, `spread` = fraction of its width
 *  they rise from). `rate` = how many embers are alive at once. Pauses off screen; nothing for
 *  reduced motion. */
export function Embers({ fireX = 0.55, fireY = 0.33, aspect = 16 / 9, spread = 0.16, rate = 90, className = "lp-embers" }: {
  fireX?: number; fireY?: number; aspect?: number; spread?: number; rate?: number; className?: string;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current;
    if (!c || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ctx = c.getContext("2d")!;
    let w = 0, h = 0, raf = 0, visible = true, ox = 0, oy = 0;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const resize = () => {
      w = c.clientWidth; h = c.clientHeight;
      c.width = w * dpr; c.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // same maths as CSS background-size: cover; background-position: 50% 40%
      if (aspect > 0) {
        const rw = Math.max(w, h * aspect), rh = rw / aspect;
        ox = (w - rw) * 0.5 + fireX * rw;
        oy = (h - rh) * 0.4 + fireY * rh;
      } else { ox = w * fireX; oy = h * fireY; }
    };
    resize();
    type P = { x: number; y: number; vx: number; vy: number; life: number; max: number; r: number };
    const ps: P[] = [];
    const spawn = (): P => ({
      x: ox + (Math.random() - 0.5) * (aspect > 0 ? Math.min(w * spread, 260) : w * spread), y: oy + Math.random() * 12,
      vx: -0.15 - Math.random() * 0.35, vy: -0.25 - Math.random() * 0.55,
      life: 0, max: 160 + Math.random() * 200, r: 0.6 + Math.random() * 1.6,
    });
    const tick = () => {
      raf = requestAnimationFrame(tick);
      if (!visible) return;
      ctx.clearRect(0, 0, w, h);
      if (ps.length < rate && Math.random() < 0.5 + rate / 200) ps.push(spawn());
      for (let i = ps.length - 1; i >= 0; i--) {
        const p = ps[i];
        p.life++; p.x += p.vx + Math.sin(p.life / 23) * 0.25; p.y += p.vy;
        const a = Math.max(0, 1 - p.life / p.max);
        if (a <= 0) { ps.splice(i, 1); continue; }
        ctx.beginPath();
        ctx.fillStyle = `rgba(255,${120 + Math.floor(a * 90)},40,${a * 0.85})`;
        ctx.shadowColor = "rgba(255,110,30,.8)";
        ctx.shadowBlur = 6;
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
    };
    tick();
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; });
    io.observe(c);
    window.addEventListener("resize", resize);
    return () => { cancelAnimationFrame(raf); io.disconnect(); window.removeEventListener("resize", resize); };
  }, [fireX, fireY, aspect, spread, rate]);

  return <canvas ref={ref} className={className} aria-hidden />;
}
