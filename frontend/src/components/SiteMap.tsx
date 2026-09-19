import { useEffect, useRef } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import type { Detection, FireEstimate, Level, SensorNode } from "../api/types";
import { LEVEL_COLOR, SENSOR_COLOR, SENSOR_LABEL, compass } from "../api/levels";
import { addSensorIcons, circleRing } from "./sensorIcons";

/** How far one ground sensor can feel a fire's heat, drawn as its footprint. */
const SENSE_M = 250;

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
function sensorFC(nodes: SensorNode[]) {
  return {
    type: "FeatureCollection",
    features: nodes.map((n) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [n.lon, n.lat] },
      properties: {
        icon: `s-${n.kind}-${n.state}`, color: SENSOR_COLOR[n.state], alert: n.state === "ok" ? 0 : 1,
        html: `<b>${esc(n.label)}</b> · ${esc(n.place)}${n.name ? ` <span style="opacity:.75">(${esc(n.name)})</span>` : ""}<br/>` +
          `<b style="color:${SENSOR_COLOR[n.state]}">${esc(SENSOR_LABEL[n.state])}</b> · ${n.temp_c === null ? "no reading" : `${n.temp_c}°C`} · battery ${n.battery_pct}%<br/>` +
          `<span style="opacity:.75">${n.dist_m} m ${compass(n.bearing_deg)} of the site centre · ${esc(n.note)}</span>`,
      },
    })),
  } as GeoJSON.FeatureCollection;
}
function senseFC(nodes: SensorNode[]) {
  return {
    type: "FeatureCollection",
    features: nodes.filter((n) => n.state !== "offline").map((n) => ({
      type: "Feature",
      geometry: { type: "Polygon", coordinates: [circleRing(n.lat, n.lon, SENSE_M, 24)] },
      properties: { color: SENSOR_COLOR[n.state], alert: n.state === "ok" ? 0 : 1 },
    })),
  } as GeoJSON.FeatureCollection;
}
function estimateFC(est: FireEstimate[]) {
  return {
    type: "FeatureCollection",
    features: est.flatMap((e) => [
      { type: "Feature", geometry: { type: "Polygon", coordinates: [circleRing(e.lat, e.lon, e.radius_m)] }, properties: { part: "area" } },
      {
        type: "Feature", geometry: { type: "Point", coordinates: [e.lon, e.lat] },
        properties: {
          part: "centre",
          html: `<b style="color:#FF3B30">Estimated fire position</b><br/>Combined from ${e.sensors} sensor${e.sensors > 1 ? "s" : ""} · ${e.confidence} confidence<br/>` +
            `± ${e.radius_m} m · ${e.distance_m} m ${compass(e.bearing_deg)} of the site centre<br/><span style="opacity:.75">Hottest: ${esc(e.hottest)}</span>`,
        },
      },
    ]),
  } as GeoJSON.FeatureCollection;
}
function markFC(marks: MapMark[]) {
  return {
    type: "FeatureCollection",
    features: marks.map((m) => ({ type: "Feature", geometry: { type: "Point", coordinates: [m.lon, m.lat] }, properties: { color: m.color, label: m.label } })),
  } as GeoJSON.FeatureCollection;
}

export function SiteMap({ sites, detections, sensors = [], estimates = [], marks = [], center = [-7.25, 42.28] as [number, number], zoom = 8.6, onSelect, height = 460 }: {
  sites: MapSite[]; detections: Detection[]; sensors?: SensorNode[]; estimates?: FireEstimate[]; marks?: MapMark[];
  center?: [number, number]; zoom?: number; onSelect?: (id: string) => void; height?: number;
}) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const ready = useRef(false);
  const latest = useRef({ sites, detections, sensors, estimates, marks });
  latest.current = { sites, detections, sensors, estimates, marks };

  useEffect(() => {
    if (!box.current || map.current) return;
    const m = new maplibregl.Map({ container: box.current, style, center, zoom, attributionControl: { compact: true } });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      const cur = latest.current;
      addSensorIcons(m);
      // each sensor's footprint; overlapping footprints show the combined coverage
      m.addSource("sense", { type: "geojson", data: senseFC(cur.sensors) });
      m.addLayer({ id: "sense-fill", type: "fill", source: "sense", paint: { "fill-color": ["get", "color"], "fill-opacity": ["case", ["==", ["get", "alert"], 1], 0.22, 0.07] } });
      m.addSource("est", { type: "geojson", data: estimateFC(cur.estimates) });
      m.addLayer({ id: "est-fill", type: "fill", source: "est", filter: ["==", ["get", "part"], "area"], paint: { "fill-color": "#FF3B30", "fill-opacity": 0.14 } });
      m.addLayer({ id: "est-line", type: "line", source: "est", filter: ["==", ["get", "part"], "area"], paint: { "line-color": "#FF3B30", "line-width": 2, "line-dasharray": [2, 1.5] } });
      m.addSource("dets", { type: "geojson", data: detFC(cur.detections) });
      m.addLayer({ id: "dets-glow", type: "circle", source: "dets", paint: { "circle-radius": 9, "circle-color": "#ff6a1f", "circle-blur": 1, "circle-opacity": 0.55 } });
      m.addLayer({ id: "dets-core", type: "circle", source: "dets", paint: { "circle-radius": 2.4, "circle-color": "#ffd28a", "circle-opacity": 0.9 } });
      m.addSource("marks", { type: "geojson", data: markFC(cur.marks) });
      m.addLayer({ id: "marks-glow", type: "circle", source: "marks", paint: { "circle-radius": 14, "circle-color": ["get", "color"], "circle-blur": 0.9, "circle-opacity": 0.6 } });
      m.addLayer({ id: "marks-core", type: "circle", source: "marks", paint: { "circle-radius": 4, "circle-color": ["get", "color"], "circle-stroke-width": 1.5, "circle-stroke-color": "#fff" } });
      m.addSource("sensors", { type: "geojson", data: sensorFC(cur.sensors) });
      m.addLayer({
        id: "sensors", type: "symbol", source: "sensors",
        layout: {
          "icon-image": ["get", "icon"], "icon-allow-overlap": true, "icon-ignore-placement": true,
          "icon-size": ["interpolate", ["linear"], ["zoom"], 8, 0.45, 12, 0.8, 15, 1.1],
          "symbol-sort-key": ["get", "alert"],
        },
      });
      m.addLayer({ id: "est-centre", type: "circle", source: "est", filter: ["==", ["get", "part"], "centre"], paint: { "circle-radius": 7, "circle-color": "#FF3B30", "circle-stroke-width": 2.5, "circle-stroke-color": "#fff" } });
      m.addSource("sites", { type: "geojson", data: sitesFC(cur.sites) });
      m.addLayer({ id: "sites-halo", type: "circle", source: "sites", paint: { "circle-radius": ["+", ["get", "r"], 6], "circle-color": ["get", "color"], "circle-opacity": 0.16 } });
      m.addLayer({ id: "sites-core", type: "circle", source: "sites", paint: { "circle-radius": ["get", "r"], "circle-color": ["get", "color"], "circle-stroke-width": 1.5, "circle-stroke-color": "rgba(255,255,255,0.85)" } });
      m.on("click", "sites-core", (e) => { const id = e.features?.[0]?.properties?.site_id; if (id && onSelect) onSelect(String(id)); });
      for (const layer of ["sensors", "est-centre"]) {
        m.on("click", layer, (e) => {
          const f = e.features?.[0];
          if (f) new maplibregl.Popup({ closeButton: false, className: "sensor-pop" }).setLngLat(e.lngLat).setHTML(String(f.properties?.html)).addTo(m);
        });
      }
      m.on("click", "marks-core", (e) => {
        const f = e.features?.[0];
        if (f) new maplibregl.Popup({ closeButton: false, className: "sensor-pop" }).setLngLat(e.lngLat).setHTML(esc(String(f.properties?.label))).addTo(m);
      });
      for (const layer of ["sites-core", "sensors", "est-centre", "marks-core"]) {
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
    (m.getSource("sensors") as maplibregl.GeoJSONSource | undefined)?.setData(sensorFC(sensors));
    (m.getSource("sense") as maplibregl.GeoJSONSource | undefined)?.setData(senseFC(sensors));
    (m.getSource("est") as maplibregl.GeoJSONSource | undefined)?.setData(estimateFC(estimates));
    (m.getSource("marks") as maplibregl.GeoJSONSource | undefined)?.setData(markFC(marks));
  }, [sites, detections, sensors, estimates, marks]);

  return <div ref={box} style={{ height, width: "100%", borderRadius: "var(--radius)", overflow: "hidden", border: "1px solid var(--border)" }} />;
}
