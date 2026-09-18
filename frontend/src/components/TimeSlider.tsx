import { useTime } from "../state/TimeContext";
import { fmtTime } from "../api/levels";

export function TimeSlider() {
  const { step, setStep, iso, steps, playing, togglePlay } = useTime();
  return (
    <div className="card" style={{ padding: "14px 18px", display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
      <div className="row" style={{ gap: 8 }}>
        <button className="btn sm ghost" onClick={() => setStep(step - 1)} aria-label="back 3 hours">◀ 3h</button>
        <button className="btn sm primary" onClick={togglePlay} style={{ minWidth: 92 }}>
          {playing ? "❚❚ Pause" : "▶ Play"}
        </button>
        <button className="btn sm ghost" onClick={() => setStep(step + 1)} aria-label="forward 3 hours">3h ▶</button>
      </div>
      <input
        type="range" min={0} max={steps - 1} value={step}
        onChange={(e) => setStep(Number(e.target.value))}
        style={{ flex: 1, minWidth: 200, accentColor: "var(--ember)", padding: 0, background: "transparent", border: "none" }}
      />
      <div className="mono" style={{ minWidth: 200, textAlign: "right", fontSize: 13 }}>{fmtTime(iso)}</div>
    </div>
  );
}
