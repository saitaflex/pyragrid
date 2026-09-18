import { useEffect, useRef } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import type { Detection, Level, SensorNode } from "../api/types";
import { LEVEL_COLOR, SENSOR_COLOR, SENSOR_LABEL } from "../api/levels";

const style: StyleSpecification = {
  version: 8,
  sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors" } },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#0b0b0e" } },
    { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.42, "raster-saturation": -0.7, "raster-brightness-max": 0.85 } },
  ],
};

/** Anything with a position and a level can be drawn as a site marker. */
export interface MapSite { site_id: string; lat: number; lon: number; level: Level; value_eur?: number | null }
/** Free markers, e.g. the signals of a training drill. */
export interface MapMark { lat: number; lon: number; label: string; color: string }

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));

function sitesFC(sites: MapSite[]) {
  return {
    type: "FeatureCollection",
    features: sites.map((s) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [s.lon, s.lat] },
      properties: { site_id: s.site_id, color: LEVEL_COLOR[s.level], level: s.level, r: s.value_eur ? 6 + Math.sqrt(s.value_eur / 1_000_000) * 2.4 : 8 },
    })),
  } as GeoJSON.FeatureCollection;
}
function detFC(dets: Detection[]) {
  return {
    type: "FeatureCollection",
    features: dets.map((d) => ({ type: "Feature", geometry: { type: "Point", coordinates: [d.lon, d.lat] }, properties: { frp: d.intensity_frp } })),
  } as GeoJSON.FeatureCollection;
}
function hexFC(nodes: SensorNode[]) {
  return {
    type: "FeatureCollection",
    features: nodes.map((n) => ({
      type: "Feature",
      geometry: { type: "Polygon", coordinates: [n.hex] },
      properties: {
        color: SENSOR_COLOR[n.state], alert: n.state === "ok" ? 0 : 1,
        html: `<b>${esc(n.label)}</b> · ${esc(SENSOR_LABEL[n.state])}<br/>` +
          `${n.temp_c === null ? "no reading" : `${n.temp_c}°C`} · battery ${n.battery_pct}%<br/>` +
          `<span style="opacity:.75">${esc(n.note)}</span>`,
      },
    })),
  } as GeoJSON.FeatureCollection;
}
function markFC(marks: MapMark[]) {
  return {
    type: "FeatureCollection",
    features: marks.map((m) => ({ type: "Feature", geometry: { type: "Point", coordinates: [m.lon, m.lat] }, properties: { color: m.color, label: m.label } })),
  } as GeoJSON.FeatureCollection;
}

export function SiteMap({ sites, detections, sensors = [], marks = [], center = [-7.25, 42.28] as [number, number], zoom = 8.6, onSelect, height = 460 }: {
  sites: MapSite[]; detections: Detection[]; sensors?: SensorNode[]; marks?: MapMark[];
  center?: [number, number]; zoom?: number; onSelect?: (id: string) => void; height?: number;
}) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const ready = useRef(false);
  const latest = useRef({ sites, detections, sensors, marks });
  latest.current = { sites, detections, sensors, marks };

  useEffect(() => {
    if (!box.current || map.current) return;
    const m = new maplibregl.Map({ container: box.current, style, center, zoom, attributionControl: { compact: true } });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      const cur = latest.current;
      m.addSource("hex", { type: "geojson", data: hexFC(cur.sensors) });
      m.addLayer({ id: "hex-fill", type: "fill", source: "hex", paint: { "fill-color": ["get", "color"], "fill-opacity": ["case", ["==", ["get", "alert"], 1], 0.55, 0.18] } });
      m.addLayer({ id: "hex-line", type: "line", source: "hex", paint: { "line-color": ["get", "color"], "line-width": 1, "line-opacity": 0.8 } });
      m.addSource("dets", { type: "geojson", data: detFC(cur.detections) });
      m.addLayer({ id: "dets-glow", type: "circle", source: "dets", paint: { "circle-radius": 9, "circle-color": "#ff6a1f", "circle-blur": 1, "circle-opacity": 0.55 } });
      m.addLayer({ id: "dets-core", type: "circle", source: "dets", paint: { "circle-radius": 2.4, "circle-color": "#ffd28a", "circle-opacity": 0.9 } });
      m.addSource("marks", { type: "geojson", data: markFC(cur.marks) });
      m.addLayer({ id: "marks-glow", type: "circle", source: "marks", paint: { "circle-radius": 14, "circle-color": ["get", "color"], "circle-blur": 0.9, "circle-opacity": 0.6 } });
      m.addLayer({ id: "marks-core", type: "circle", source: "marks", paint: { "circle-radius": 4, "circle-color": ["get", "color"], "circle-stroke-width": 1.5, "circle-stroke-color": "#fff" } });
      m.addSource("sites", { type: "geojson", data: sitesFC(cur.sites) });
      m.addLayer({ id: "sites-halo", type: "circle", source: "sites", paint: { "circle-radius": ["+", ["get", "r"], 6], "circle-color": ["get", "color"], "circle-opacity": 0.16 } });
      m.addLayer({ id: "sites-core", type: "circle", source: "sites", paint: { "circle-radius": ["get", "r"], "circle-color": ["get", "color"], "circle-stroke-width": 1.5, "circle-stroke-color": "rgba(255,255,255,0.85)" } });
      m.on("click", "sites-core", (e) => { const id = e.features?.[0]?.properties?.site_id; if (id && onSelect) onSelect(String(id)); });
      m.on("click", "hex-fill", (e) => {
        const f = e.features?.[0];
        if (f) new maplibregl.Popup({ closeButton: false, className: "sensor-pop" }).setLngLat(e.lngLat).setHTML(String(f.properties?.html)).addTo(m);
      });
      m.on("click", "marks-core", (e) => {
        const f = e.features?.[0];
        if (f) new maplibregl.Popup({ closeButton: false, className: "sensor-pop" }).setLngLat(e.lngLat).setHTML(esc(String(f.properties?.label))).addTo(m);
      });
      for (const layer of ["sites-core", "hex-fill", "marks-core"]) {
        m.on("mouseenter", layer, () => { m.getCanvas().style.cursor = "pointer"; });
        m.on("mouseleave", layer, () => { m.getCanvas().style.cursor = ""; });
      }
      ready.current = true;
    });
    return () => { m.remove(); map.current = null; ready.current = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m || !ready.current) return;
    (m.getSource("sites") as maplibregl.GeoJSONSource | undefined)?.setData(sitesFC(sites));
    (m.getSource("dets") as maplibregl.GeoJSONSource | undefined)?.setData(detFC(detections));
    (m.getSource("hex") as maplibregl.GeoJSONSource | undefined)?.setData(hexFC(sensors));
    (m.getSource("marks") as maplibregl.GeoJSONSource | undefined)?.setData(markFC(marks));
  }, [sites, detections, sensors, marks]);

  return <div ref={box} style={{ height, width: "100%", borderRadius: "var(--radius)", overflow: "hidden", border: "1px solid var(--border)" }} />;
}
