// burn.ts — the fire that ends the dragon intro. Driven by q = 0..1 (scroll):
//   0.00–0.45  a wall of fire comes down from the top and covers the paper
//   0.45–0.62  the flames die down to char and glowing embers
//   0.62–0.95  the char burns through (glowing edges) and reveals the fire photo
//   0.95–1.00  the canvas fades out over the real photo section underneath
// Colours come from the logo's flames: deep red, flame red, ember orange, yellow tips.

const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const ease = (t: number) => t * t * (3 - 2 * t);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// small value noise, enough for flame tongues and the burn-through mask
function hash(x: number, y: number) { const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return s - Math.floor(s); }
function noise2(x: number, y: number) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash(xi, yi), b = hash(xi + 1, yi), c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
  return lerp(lerp(a, b, u), lerp(c, d, u), v);
}
function fbm(x: number, y: number) { let s = 0, a = 0.5, f = 1; for (let i = 0; i < 4; i++) { s += a * noise2(x * f, y * f); f *= 2; a *= 0.5; } return s; }

const LAYERS = [
  { color: "#5E1206", amp: 0.20, off: -0.10, speed: 0.55, freq: 2.2 },
  { color: "#9E2A10", amp: 0.16, off: -0.05, speed: 0.8, freq: 3.1 },
  { color: "#C53A19", amp: 0.13, off: 0.0, speed: 1.1, freq: 4.0 },
  { color: "#F07A2A", amp: 0.09, off: 0.035, speed: 1.5, freq: 5.3 },
  { color: "#FFB14A", amp: 0.05, off: 0.06, speed: 2.1, freq: 7.0 },
];
const CHAR = [20, 12, 9];

export class Burn {
  private ctx: CanvasRenderingContext2D;
  private w = 0; private h = 0; private dpr = 1;
  private q = 0; private raf = 0; private t0 = performance.now(); private running = false;
  private photo = new Image();
  private mask: HTMLCanvasElement; private mctx: CanvasRenderingContext2D; private field: Float32Array;
  private MW = 220; private MH = 140;
  private sparks: { x: number; y: number; vx: number; vy: number; life: number; max: number; r: number }[] = [];
  private canvas: HTMLCanvasElement;
  private still: boolean;

  constructor(canvas: HTMLCanvasElement, photoSrc: string) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d")!;
    this.photo.src = photoSrc;
    this.still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.mask = document.createElement("canvas");
    this.mask.width = this.MW; this.mask.height = this.MH;
    this.mctx = this.mask.getContext("2d")!;
    // the burn-through order: noise plus a bias so it starts at the top and near the flames
    this.field = new Float32Array(this.MW * this.MH);
    for (let j = 0; j < this.MH; j++) for (let i = 0; i < this.MW; i++)
      this.field[j * this.MW + i] = clamp(fbm(i / 17, j / 17) * 0.85 + (j / this.MH) * 0.18 - 0.02);
    this.resize();
  }

  resize() {
    this.dpr = Math.min(1.5, window.devicePixelRatio || 1);
    this.w = this.canvas.clientWidth; this.h = this.canvas.clientHeight;
    this.canvas.width = Math.round(this.w * this.dpr); this.canvas.height = Math.round(this.h * this.dpr);
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    this.draw();
  }

  set(q: number) {
    this.q = q;
    this.canvas.style.opacity = String(q >= 0.95 ? 1 - (q - 0.95) / 0.05 : 1);
    this.canvas.style.visibility = q <= 0 || q >= 1 ? "hidden" : "visible";
    const active = q > 0 && q < 1;
    if (active && !this.running && !this.still) { this.running = true; this.loop(); }
    if (!active) { this.running = false; cancelAnimationFrame(this.raf); }
    if (!this.running) this.draw();
  }

  destroy() { this.running = false; cancelAnimationFrame(this.raf); }

  private loop = () => { if (!this.running) return; this.draw(); this.raf = requestAnimationFrame(this.loop); };

  // the photo drawn exactly like the hero section (cover, 50% 40%, its dark shade)
  private drawPhoto() {
    const { ctx, w, h } = this, im = this.photo;
    ctx.fillStyle = "#0F1519"; ctx.fillRect(0, 0, w, h);
    if (im.complete && im.naturalWidth) {
      const s = Math.max(w / im.naturalWidth, h / im.naturalHeight) * 1.06;
      const dw = im.naturalWidth * s, dh = im.naturalHeight * s;
      ctx.drawImage(im, (w - dw) * 0.5, (h - dh) * 0.4, dw, dh);
    }
    let g = ctx.createLinearGradient(0, 0, w, 0);
    g.addColorStop(0, "rgba(15,21,25,.92)"); g.addColorStop(0.45, "rgba(15,21,25,.55)"); g.addColorStop(0.75, "rgba(15,21,25,0)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    g = ctx.createLinearGradient(0, h, 0, h * 0.65);
    g.addColorStop(0, "#0F1519"); g.addColorStop(1, "rgba(15,21,25,0)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
  }

  private flameWall(edge: number, time: number, strength: number) {
    const { ctx, w, h } = this;
    const step = Math.max(2.5, w / 420);
    // brightest (furthest-reaching) layer first, darker ones over it: dark behind, bright tips
    for (const L of [...LAYERS].reverse()) {
      ctx.beginPath(); ctx.moveTo(0, 0);
      for (let x = 0; x <= w + step; x += step) {
        const nx = x / w;
        // spiky tongues that lick downward, flickering in time
        const envelope = 0.35 + 0.65 * fbm(nx * L.freq * 0.6 + time * 0.15, time * L.speed * 0.25);
        const tongues = Math.pow(noise2(nx * L.freq * 9 + time * L.speed * 0.9, time * L.speed * 1.6), 2.6);
        const flick = Math.pow(noise2(nx * L.freq * 23 - time * L.speed * 2.2, time * 3.1 + L.freq), 4) * 0.5;
        const y = edge + (L.off + (tongues + flick) * envelope * L.amp * 2.6) * h * strength;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(w, 0); ctx.closePath();
      ctx.fillStyle = L.color; ctx.fill();
    }
    // behind the front everything has already burned: char coming down after the flames
    const charEnd = edge - 0.32 * h;
    if (charEnd > 0) {
      const g = ctx.createLinearGradient(0, charEnd - 0.18 * h, 0, charEnd + 0.12 * h);
      g.addColorStop(0, `rgb(${CHAR})`); g.addColorStop(1, `rgba(${CHAR},0)`);
      ctx.fillStyle = `rgb(${CHAR})`; ctx.fillRect(0, 0, w, Math.max(0, charEnd - 0.18 * h));
      ctx.fillStyle = g; ctx.fillRect(0, charEnd - 0.18 * h, w, 0.3 * h);
    }
    // heat glow along the front
    ctx.save(); ctx.globalCompositeOperation = "lighter";
    const gl = ctx.createLinearGradient(0, edge - 0.25 * h, 0, edge + 0.12 * h);
    gl.addColorStop(0, "rgba(255,120,30,0)"); gl.addColorStop(0.7, `rgba(255,140,40,${0.35 * strength})`); gl.addColorStop(1, "rgba(255,120,30,0)");
    ctx.fillStyle = gl; ctx.fillRect(0, edge - 0.25 * h, w, 0.37 * h);
    ctx.restore();
  }

  private charWithEmbers(time: number, glow: number) {
    const { ctx, w, h } = this;
    ctx.fillStyle = `rgb(${CHAR})`; ctx.fillRect(0, 0, w, h);
    ctx.save(); ctx.globalCompositeOperation = "lighter";
    for (let k = 0; k < 14; k++) {
      const x = (hash(k, 1) * 1.2 - 0.1) * w, y = (hash(k, 2) * 1.1 - 0.05) * h;
      const r = (0.08 + hash(k, 3) * 0.16) * Math.max(w, h);
      const f = 0.5 + 0.5 * Math.sin(time * (1.5 + hash(k, 4) * 2) + k);
      const g = ctx.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, `rgba(255,90,20,${0.28 * glow * (0.6 + 0.4 * f)})`); g.addColorStop(1, "rgba(255,90,20,0)");
      ctx.fillStyle = g; ctx.fillRect(x - r, y - r, 2 * r, 2 * r);
    }
    ctx.restore();
  }

  // the char burns away: transparent where the noise is under the threshold, a glowing rim at it
  private burnThrough(thr: number) {
    const { MW, MH } = this, img = this.mctx.createImageData(MW, MH), d = img.data;
    for (let k = 0; k < MW * MH; k++) {
      const n = this.field[k], o = k * 4;
      if (n < thr) { d[o + 3] = 0; continue; }
      const rim = n - thr;
      if (rim < 0.045) { const t = rim / 0.045; d[o] = 255; d[o + 1] = Math.round(200 - 110 * t); d[o + 2] = Math.round(90 - 70 * t); d[o + 3] = 255; }
      else if (rim < 0.09) { const t = (rim - 0.045) / 0.045; d[o] = Math.round(lerp(200, CHAR[0], t)); d[o + 1] = Math.round(lerp(60, CHAR[1], t)); d[o + 2] = Math.round(lerp(15, CHAR[2], t)); d[o + 3] = 255; }
      else { d[o] = CHAR[0]; d[o + 1] = CHAR[1]; d[o + 2] = CHAR[2]; d[o + 3] = 255; }
    }
    this.mctx.putImageData(img, 0, 0);
    this.ctx.imageSmoothingEnabled = true;
    this.ctx.save();
    this.ctx.filter = "blur(3px)";                    // soft, charred edges instead of pixels
    this.ctx.drawImage(this.mask, 0, 0, this.w, this.h);
    this.ctx.restore();
  }

  private embers(time: number, amount: number, dt: number, fromY: number | null = null) {
    const { ctx, w, h } = this;
    if (!this.still && Math.random() < amount * 1.4) {
      for (let i = 0; i < 3; i++) {
        const y = fromY === null ? h * (0.55 + Math.random() * 0.5) : fromY + (Math.random() - 0.3) * 0.12 * h;
        this.sparks.push({ x: Math.random() * w, y, vx: -0.4 + Math.random() * 0.8, vy: fromY === null ? -(0.6 + Math.random() * 1.6) : (Math.random() - 0.6) * 2.2, life: 0, max: 50 + Math.random() * 80, r: 0.7 + Math.random() * 2 });
      }
    }
    ctx.save(); ctx.globalCompositeOperation = "lighter";
    for (let i = this.sparks.length - 1; i >= 0; i--) {
      const s = this.sparks[i];
      s.life += dt; s.x += s.vx * dt + Math.sin((s.life + time) / 9) * 0.4; s.y += s.vy * dt;
      const a = 1 - s.life / s.max;
      if (a <= 0 || s.y < -10) { this.sparks.splice(i, 1); continue; }
      ctx.fillStyle = `rgba(255,${150 + Math.round(80 * a)},60,${a})`;
      ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  }

  private last = performance.now();
  draw() {
    const { ctx, w, h, q } = this;
    const now = performance.now(), dt = Math.min(3, (now - this.last) / 16.7); this.last = now;
    const time = this.still ? 0 : (now - this.t0) / 1000;
    ctx.clearRect(0, 0, w, h);
    if (q <= 0 || q >= 1) return;
    if (q < 0.45) {
      const e = ease(clamp(q / 0.45));
      const edge = lerp(-0.3 * h, 1.25 * h, e);
      this.flameWall(edge, time, 0.7 + 0.3 * e);
      this.embers(time, 0.4 + 0.6 * e, dt, edge);
    } else if (q < 0.62) {
      const k = clamp((q - 0.45) / 0.17);
      this.charWithEmbers(time, 1 - 0.5 * k);
      // the last flames sink out of the bottom of the screen
      this.flameWall(lerp(1.25 * h, 1.9 * h, ease(k)), time, 1 - k);
      this.embers(time, 1 - k * 0.5, dt);
    } else {
      const k = ease(clamp((q - 0.62) / 0.33));
      this.drawPhoto();
      this.burnThrough(lerp(0.12, 1.12, k));
      this.embers(time, 0.5 * (1 - k), dt);
    }
  }
}
