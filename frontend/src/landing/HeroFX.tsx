import { useEffect, useRef } from "react";

/* Life for the fire photo: a breathing glow on the burning ridge, smoke drifting with the
   wind, embers of different sizes rising and scattering, and a slight parallax. Positions
   follow the fire in the photo whatever the crop (background: cover, 50% 40%). */

export function HeroFX({ fireX = 0.55, fireY = 0.33, aspect = 2048 / 1152, imageRef }: {
  fireX?: number; fireY?: number; aspect?: number; imageRef?: React.RefObject<HTMLDivElement | null>;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current;
    if (!c || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ctx = c.getContext("2d")!;
    const dpr = Math.min(1.5, window.devicePixelRatio || 1);
    let w = 0, h = 0, ox = 0, oy = 0, span = 0, raf = 0, visible = true;
    const resize = () => {
      w = c.clientWidth; h = c.clientHeight;
      c.width = w * dpr; c.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const rw = Math.max(w, h * aspect), rh = rw / aspect;
      ox = (w - rw) * 0.5 + fireX * rw; oy = (h - rh) * 0.4 + fireY * rh;
      span = rw * 0.16;                                   // width of the burning ridge
    };
    resize();

    type P = { x: number; y: number; vx: number; vy: number; life: number; max: number; r: number; soft: boolean };
    const embers: P[] = [];
    const smoke = Array.from({ length: 7 }, (_, i) => ({ k: i / 7, seed: Math.random() * 10 }));
    let t0 = performance.now(), last = t0;

    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      if (!visible) { last = now; return; }
      const t = (now - t0) / 1000, dt = Math.min(3, (now - last) / 16.7); last = now;
      ctx.clearRect(0, 0, w, h);

      // smoke: soft plumes rising from the ridge and leaning with the wind (to the left)
      for (const s of smoke) {
        const k = (s.k + t * 0.018) % 1;
        const x = ox - k * w * 0.45 + Math.sin(t * 0.3 + s.seed) * 30, y = oy - 20 - k * h * 0.42;
        const r = 60 + k * 260;
        const g = ctx.createRadialGradient(x, y, 0, x, y, r);
        const a = 0.14 * Math.sin(Math.PI * k);
        g.addColorStop(0, `rgba(40,38,40,${a})`); g.addColorStop(1, "rgba(40,38,40,0)");
        ctx.fillStyle = g; ctx.fillRect(x - r, y - r, 2 * r, 2 * r);
      }

      // the fire breathes: a warm glow that swells and dips like real flames
      ctx.save(); ctx.globalCompositeOperation = "lighter";
      const flick = 0.75 + 0.15 * Math.sin(t * 7.3) + 0.1 * Math.sin(t * 13.1 + 1.7);
      for (const [dx, rr, a] of [[0, 1.0, 0.34], [-0.35, 0.6, 0.2], [0.4, 0.55, 0.18]] as const) {
        const x = ox + dx * span, r = span * rr * (0.9 + 0.1 * flick);
        const g = ctx.createRadialGradient(x, oy, 0, x, oy, r);
        g.addColorStop(0, `rgba(255,120,40,${a * flick})`); g.addColorStop(0.5, `rgba(255,80,20,${a * 0.4 * flick})`); g.addColorStop(1, "rgba(255,70,20,0)");
        ctx.fillStyle = g; ctx.fillRect(x - r, oy - r, 2 * r, 2 * r);
      }

      // embers: many small sharp ones, a few big soft ones, carried up and left
      if (embers.length < 120 && Math.random() < 0.7) {
        const soft = Math.random() < 0.12;
        embers.push({ x: ox + (Math.random() - 0.5) * span * 1.4, y: oy + Math.random() * 10, vx: -0.2 - Math.random() * 0.6, vy: -0.3 - Math.random() * 0.9,
          life: 0, max: 140 + Math.random() * 220, r: soft ? 2.5 + Math.random() * 3.5 : 0.6 + Math.random() * 1.4, soft });
      }
      for (let i = embers.length - 1; i >= 0; i--) {
        const p = embers[i];
        p.life += dt; p.x += (p.vx + Math.sin((p.life + p.y) / 27) * 0.35) * dt; p.y += p.vy * dt; p.vy *= 0.999;
        const a = Math.max(0, 1 - p.life / p.max) * (p.life < 12 ? p.life / 12 : 1);
        if (a <= 0) { embers.splice(i, 1); continue; }
        ctx.beginPath();
        ctx.fillStyle = p.soft ? `rgba(255,140,60,${a * 0.35})` : `rgba(255,${150 + Math.round(a * 80)},60,${a * 0.9})`;
        ctx.shadowColor = "rgba(255,110,30,.9)"; ctx.shadowBlur = p.soft ? 12 : 5;
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
      }
      ctx.restore();
    };
    raf = requestAnimationFrame(tick);

    // parallax: the photo drifts a few pixels against the pointer
    const img = imageRef?.current;
    const move = (e: PointerEvent) => {
      if (!img) return;
      const dx = (e.clientX / window.innerWidth - 0.5) * -14, dy = (e.clientY / window.innerHeight - 0.5) * -8;
      img.style.translate = `${dx}px ${dy}px`;
    };
    window.addEventListener("pointermove", move, { passive: true });
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; });
    io.observe(c);
    window.addEventListener("resize", resize);
    return () => { cancelAnimationFrame(raf); io.disconnect(); window.removeEventListener("resize", resize); window.removeEventListener("pointermove", move); };
  }, [fireX, fireY, aspect, imageRef]);

  return <canvas ref={ref} className="lp-embers" aria-hidden />;
}
