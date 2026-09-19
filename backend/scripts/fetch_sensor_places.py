"""fetch_sensor_places.py — real places around each site where ground sensors can go.

Queries OpenStreetMap (Overpass API) for buildings (houses, cabins, huts, farm buildings)
and vegetation (forest, scrub, grassland, farmland) within each site's sensor coverage and
writes data/sensor_places.json. The engine places sensors on these points at runtime and
falls back to an even grid where OSM has nothing. Run once; the data file is committed:

    python scripts/fetch_sensor_places.py [--refresh-buildings] [--refresh-green]
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.importer import seed_sites  # noqa: E402
from app.sensors import coverage_m  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "sensor_places.json"
URLS = ["https://overpass-api.de/api/interpreter",
        "https://overpass.private.coffee/api/interpreter"]
HEADERS = {"User-Agent": "rural-valley-wildfire-hackathon/1.0 (sensor placement)"}

BUILDING_KIND = {
    "house": "House", "detached": "House", "residential": "House", "semidetached_house": "House",
    "bungalow": "House", "cabin": "Cabin", "hut": "Cabin", "farm": "Farm building",
    "barn": "Farm building", "farm_auxiliary": "Farm building", "shed": "Shed",
    "stable": "Farm building", "cowshed": "Farm building", "chapel": "Chapel",
    "church": "Church", "industrial": "Industrial building",
}
GREEN_KIND = {
    "forest": "Forest edge", "wood": "Forest edge", "scrub": "Scrubland", "heath": "Scrubland",
    "grassland": "Grassland", "grass": "Grassland", "meadow": "Grassland",
    "farmland": "Farmland", "orchard": "Farmland", "vineyard": "Farmland",
}


def _dist_m(lat1, lon1, lat2, lon2):
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return 6371008.8 * math.hypot(x, y)


def query(q: str) -> list[dict]:
    last = None
    for url in URLS:
        for attempt in range(3):
            try:
                r = httpx.post(url, data={"data": q}, headers=HEADERS, timeout=90)
                if r.status_code == 200:
                    return r.json()["elements"]
                last = f"HTTP {r.status_code}"
            except Exception as e:  # network hiccup, try again / next mirror
                last = str(e)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Overpass failed: {last}")


def fetch_buildings(site) -> list[dict]:
    cov, lat, lon = coverage_m(site), site.lat, site.lon
    q = f"""[out:json][timeout:60];
(
  way["building"](around:{cov},{lat},{lon});
  node["building"](around:{cov},{lat},{lon});
  node["tourism"~"alpine_hut|wilderness_hut"](around:{cov},{lat},{lon});
);
out tags center 600;"""
    out = []
    for e in query(q):
        t = e.get("tags", {})
        c = e.get("center") or ({"lat": e["lat"], "lon": e["lon"]} if "lat" in e else None)
        if not c or _dist_m(lat, lon, c["lat"], c["lon"]) > cov:
            continue
        kind = "Mountain hut" if t.get("tourism") else BUILDING_KIND.get(t.get("building"), "Building")
        out.append({"lat": round(c["lat"], 6), "lon": round(c["lon"], 6),
                    "place": kind, "name": t.get("name", "")})
    return out[:400]


def fetch_green(site) -> list[dict]:
    cov, lat, lon = coverage_m(site), site.lat, site.lon
    q = f"""[out:json][timeout:80];
(
  way["landuse"~"^(forest|meadow|grass|farmland|orchard|vineyard)$"](around:{cov},{lat},{lon});
  way["natural"~"^(wood|scrub|grassland|heath)$"](around:{cov},{lat},{lon});
);
out tags geom;"""
    out = []
    for e in query(q):
        t = e.get("tags", {})
        kind = GREEN_KIND.get(t.get("landuse") or t.get("natural"))
        geom = e.get("geometry") or []
        if not kind:
            continue
        # polygon vertices = the edge of the vegetation (where fire meets people and assets)
        for p in geom[:: max(1, len(geom) // 40)]:
            if _dist_m(lat, lon, p["lat"], p["lon"]) <= cov:
                out.append({"lat": round(p["lat"], 6), "lon": round(p["lon"], 6), "place": kind})
    return out[:600]


def main() -> None:
    """Fills what is missing; --refresh-buildings / --refresh-green force a re-download."""
    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    for site in seed_sites():
        entry = out.setdefault(site.site_id, {"coverage_m": coverage_m(site)})
        for key, fetch in (("buildings", fetch_buildings), ("green", fetch_green)):
            if key in entry and f"--refresh-{key}" not in sys.argv:
                continue
            try:
                entry[key] = fetch(site)
                print(f"{site.site_id}: {len(entry[key])} {key}", flush=True)
            except RuntimeError as e:
                print(f"{site.site_id}: {key} {e} (grid fallback at runtime)", flush=True)
            OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
            time.sleep(3)  # be polite to the public Overpass servers
    out["_source"] = "© OpenStreetMap contributors, ODbL (via Overpass API)"
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
