import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { STEPS, isoToStep, stepIso } from "../api/engine";

interface TimeCtx {
  step: number;
  setStep: (n: number) => void;
  iso: string;
  steps: number;
  playing: boolean;
  togglePlay: () => void;
}

const Ctx = createContext<TimeCtx>(null as unknown as TimeCtx);
export const useTime = () => useContext(Ctx);

export function TimeProvider({ children }: { children: ReactNode }) {
  const [params, setParams] = useSearchParams();
  const initial = params.get("at") ? isoToStep(params.get("at")!) : STEPS - 1;
  const [step, setStepState] = useState(Math.max(0, Math.min(STEPS - 1, initial)));
  const [playing, setPlaying] = useState(false);
  const timer = useRef<number | null>(null);

  const setStep = (n: number) => {
    const clamped = Math.max(0, Math.min(STEPS - 1, n));
    setStepState(clamped);
    const next = new URLSearchParams(params);
    next.set("at", stepIso(clamped));
    setParams(next, { replace: true });
  };

  useEffect(() => {
    if (!playing) { if (timer.current) window.clearInterval(timer.current); return; }
    timer.current = window.setInterval(() => {
      setStepState((s) => {
        if (s >= STEPS - 1) { setPlaying(false); return s; }
        const n = s + 1;
        const next = new URLSearchParams(window.location.search);
        next.set("at", stepIso(n));
        setParams(next, { replace: true });
        return n;
      });
    }, 900);
    return () => { if (timer.current) window.clearInterval(timer.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing]);

  const togglePlay = () => setPlaying((p) => !p);

  return (
    <Ctx.Provider value={{ step, setStep, iso: stepIso(step), steps: STEPS, playing, togglePlay }}>
      {children}
    </Ctx.Provider>
  );
}
