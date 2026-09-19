// sensorIcons.ts — map icons for ground sensors: shape = what it is mounted on,
// colour = its state. Drawn once on a canvas and registered with the map.
import type maplibregl from "maplibre-gl";
import { SENSOR_COLOR } from "../api/levels";
import type { SensorKind, SensorState } from "../api/types";

const KINDS: SensorKind[] = ["structure", "vegetation", "fence", "grid"];
const STATES: SensorState[] = ["ok", "warm", "fire", "offline", "dropped"];
const PX = 2; // pixel ratio
const SIZE = 22;

/** Path of each shape in a 22×22 box. */
export function shapePath(ctx: CanvasRenderingContext2D | Path2D, kind: SensorKind) {
  if (kind === "structure") {          // house: roof + walls
    ctx.moveTo(11, 2); ctx.lineTo(20, 10); ctx.lineTo(17, 10); ctx.lineTo(17, 19);
    ctx.lineTo(5, 19); ctx.lineTo(5, 10); ctx.lineTo(2, 10); ctx.closePath();
  } else if (kind === "vegetation") {  // tree: crown + trunk
    ctx.moveTo(11, 1.5); ctx.lineTo(19, 15); ctx.lineTo(13, 15); ctx.lineTo(13, 20);
    ctx.lineTo(9, 20); ctx.lineTo(9, 15); ctx.lineTo(3, 15); ctx.closePath();
  } else if (kind === "fence") {       // square post
    ctx.rect(5, 5, 12, 12);
  } else {                             // open ground: dot
    ctx.moveTo(18, 11); ctx.arc(11, 11, 7, 0, Math.PI * 2);
  }
}

export function addSensorIcons(m: maplibregl.Map) {
  for (const kind of KINDS) {
    for (const state of STATES) {
      const id = `s-${kind}-${state}`;
      if (m.hasImage(id)) continue;
      const c = document.createElement("canvas");
      c.width = c.height = SIZE * PX;
      const ctx = c.getContext("2d")!;
      ctx.scale(PX, PX);
      ctx.beginPath();
      shapePath(ctx, kind);
      ctx.fillStyle = SENSOR_COLOR[state];
      ctx.strokeStyle = state === "fire" ? "#fff" : "rgba(10,10,12,0.9)";
      ctx.lineWidth = 1.6;
      ctx.lineJoin = "round";
      ctx.fill();
      ctx.stroke();
      const img = ctx.getImageData(0, 0, c.width, c.height);
      m.addImage(id, { width: c.width, height: c.height, data: new Uint8Array(img.data.buffer) }, { pixelRatio: PX });
    }
  }
}

/** Circle of `radiusM` metres around a point, as a GeoJSON ring. */
export function circleRing(lat: number, lon: number, radiusM: number, steps = 48): [number, number][] {
  const out: [number, number][] = [];
  const dLat = radiusM / 111_320;
  const dLon = radiusM / (111_320 * Math.cos((lat * Math.PI) / 180));
  for (let i = 0; i <= steps; i++) {
    const a = (i / steps) * Math.PI * 2;
    out.push([lon + dLon * Math.sin(a), lat + dLat * Math.cos(a)]);
  }
  return out;
}
