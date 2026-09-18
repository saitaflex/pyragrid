# Ember — Console (frontend)

Interactive React + TypeScript console for the Wildfire Asset Intelligence project
(Track 2 / Section 6). Cinematic dark "ember" theme, animated with Framer Motion,
interactive MapLibre map and Recharts timeline.

- **Stack:** Vite + React + TS, react-router-dom 6, maplibre-gl 4, recharts 2, framer-motion, plain CSS.
- **Contract:** `src/api/types.ts` mirrors Section 2.4 verbatim.
- **Mock mode:** runs fully without a backend. `src/api/engine.ts` is a client-side
  replay over the 144-step grid, so scrubbing time animates the whole dashboard.

## Run
```bash
npm install
npm run dev            # http://localhost:5173
npm run build          # type-check + production build
```

## Environment
| Var | Purpose | Default |
|---|---|---|
| `VITE_USE_MOCKS` | `true` = built-in demo data; `false` = call the Engine | `true` |
| `VITE_API_BASE_URL` | Engine base URL (live mode) | `http://localhost:8000` |

## Screens
Login · Portfolio (map + ranked list + time scrubber) · Site (factors, timeline, SOP) ·
Incident (+ AI Advisor, approve/reject) · Alerts · History (backtest) · Assets · Rules ·
System (sources, outbox, audit, AI decisions) · Field card · printable Handoff pack.

## Deploy (Vercel)
Root Directory = `frontend`, framework Vite. Set `VITE_API_BASE_URL` to the Engine URL
and `VITE_USE_MOCKS=false`. `vercel.json` rewrites all routes to `/` so refresh works.

> Demo data is simulated. MVP decision-support model, not a validated prediction model.
> Fire data is near-real-time detections, not perimeters.
