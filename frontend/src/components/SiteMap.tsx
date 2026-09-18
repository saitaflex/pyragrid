import { useEffect, useRef } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import type { Detection, SiteStatus } from "../api/types";
import { LEVEL_COLOR } from "../api/levels";

const style: StyleSpecification = {
  version: 8,
  sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors" } },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#0b0b0e" } },
    { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.42, "raster-saturation": -0.7, "raster-brightness-max": 0.85 } },
  ],
};

function sitesFC(sites: SiteStatus[]) {
  return {
    type: "FeatureCollection",
    features: sites.map((s) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [s.lon, s.lat] },
      properties: { site_id: s.site_id, color: LEVEL_COLOR[s.level], level: s.level, r: 6 + Math.sqrt(s.value_eur / 1_000_000) * 2.4 },
    })),
  } as GeoJSON.FeatureCollection;
}
function detFC(dets: Detection[]) {
  return {
    type: "FeatureCollection",
    features: dets.map((d) => ({ type: "Feature", geometry: { type: "Point", coordinates: [d.lon, d.lat] }, properties: { frp: d.intensity_frp } })),
  } as GeoJSON.FeatureCollection;
}

export function SiteMap({ sites, detections, center = [-7.25, 42.28] as [number, number], zoom = 8.6, onSelect, height = 460 }: {
  sites: SiteStatus[]; detections: Detection[]; center?: [number, number]; zoom?: number; onSelect?: (id: string) => void; height?: number;
}) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const ready = useRef(false);

  useEffect(() => {
    if (!box.current || map.current) return;
    const m = new maplibregl.Map({ container: box.current, style, center, zoom, attributionControl: { compact: true } });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      m.addSource("dets", { type: "geojson", data: detFC(detections) });
      m.addLayer({ id: "dets-glow", type: "circle", source: "dets", paint: { "circle-radius": 9, "circle-color": "#ff6a1f", "circle-blur": 1, "circle-opacity": 0.55 } });
      m.addLayer({ id: "dets-core", type: "circle", source: "dets", paint: { "circle-radius": 2.4, "circle-color": "#ffd28a", "circle-opacity": 0.9 } });
      m.addSource("sites", { type: "geojson", data: sitesFC(sites) });
      m.addLayer({ id: "sites-halo", type: "circle", source: "sites", paint: { "circle-radius": ["+", ["get", "r"], 6], "circle-color": ["get", "color"], "circle-opacity": 0.16 } });
      m.addLayer({ id: "sites-core", type: "circle", source: "sites", paint: { "circle-radius": ["get", "r"], "circle-color": ["get", "color"], "circle-stroke-width": 1.5, "circle-stroke-color": "rgba(255,255,255,0.85)" } });
      m.on("click", "sites-core", (e) => { const id = e.features?.[0]?.properties?.site_id; if (id && onSelect) onSelect(String(id)); });
      m.on("mouseenter", "sites-core", () => { m.getCanvas().style.cursor = "pointer"; });
      m.on("mouseleave", "sites-core", () => { m.getCanvas().style.cursor = ""; });
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
  }, [sites, detections]);

  return <div ref={box} style={{ height, width: "100%", borderRadius: "var(--radius)", overflow: "hidden", border: "1px solid var(--border)" }} />;
}
