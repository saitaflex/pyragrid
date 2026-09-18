import { useEffect, useRef, useState } from "react";

export function StatTile({ label, value, suffix, accent, hint }: {
  label: string; value: number; suffix?: string; accent?: string; hint?: string;
}) {
  const [n, setN] = useState(0);
  const raf = useRef<number>(0);
  useEffect(() => {
    const start = performance.now();
    const from = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / 700);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(from + (value - from) * eased);
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [value]);
  return (
    <div className="card hover" style={{ position: "relative", overflow: "hidden" }}>
      {accent && <div style={{ position: "absolute", inset: 0, background: `radial-gradient(20rem 12rem at 100% 0%, ${accent}22, transparent 60%)` }} />}
      <div className="eyebrow" style={{ position: "relative" }}>{label}</div>
      <div className="kpi" style={{ position: "relative", color: accent ?? "var(--text)" }}>
        {Math.round(n).toLocaleString()}{suffix ?? ""}
      </div>
      {hint && <div className="small mute" style={{ position: "relative" }}>{hint}</div>}
    </div>
  );
}
