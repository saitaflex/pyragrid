"""sensors.py — optional ground temperature sensors placed on real places around a site.

Sensors are dots on real features, not a grid: each one sits inside the site's coverage
(site + at least 1 km buffer) on the site fence, at nearby buildings from OpenStreetMap
(houses, cabins, huts, farm buildings) or along vegetation edges (forest, scrub, grassland,
farmland). Where OSM has nothing, evenly spaced "open ground" points fill the gaps.
Readings of neighbouring sensors are combined into one estimated fire position.

Readings are simulated over the replay grid from the same detections the engine scores:
ambient temperature (weather + day/night cycle) plus radiant heat from nearby detections.
Sensors can go warm, report fire, be destroyed by fire (offline), run out of battery
(offline) or be knocked over (dropped). A production deployment would post real readings
(e.g. LoRaWAN gateway -> ingest API) instead.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from app import config
from app.geo import bearing_deg, compass, destination, haversine_km
from app.models import FireEstimate, SensorEvent, SensorMesh, SensorNode, Site
from app.providers.weather import WeatherService
from app.providers.wildfire import FileDetectionsProvider
from app.replay import fmt, grid_steps, parse

WARM_C = 45.0
FIRE_C = 65.0
DESTROY_C = 150.0
STATES = ("ok", "warm", "fire", "offline", "dropped")
KINDS = ("fence", "structure", "vegetation", "grid")
MAX_STRUCTURES, MAX_VEGETATION = 10, 12
_PLACES = Path(__file__).resolve().parent.parent / "data" / "sensor_places.json"


def _h(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:12], 16)


def _m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return haversine_km(lat1, lon1, lat2, lon2) * 1000


def coverage_m(site: Site) -> int:
    """Sensors cover the site plus a buffer of at least 1 km, so fire is sensed early."""
    return site.radius_m + max(1000, site.radius_m)


@lru_cache(maxsize=1)
def _places() -> dict:
    try:
        return json.loads(_PLACES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _spread(cands: list[dict], chosen: list[dict], k: int, min_m: float) -> list[dict]:
    """Farthest-point sampling: up to k candidates, each as far as possible from everything
    already chosen and never closer than min_m, so sensors spread over the area."""
    picked: list[dict] = []
    pool = list(cands)
    while pool and len(picked) < k:
        ref = chosen + picked
        best, best_d = None, -1.0
        for c in pool:
            d = min((_m(c["lat"], c["lon"], r["lat"], r["lon"]) for r in ref), default=1e9)
            if d > best_d:
                best, best_d = c, d
        if best is None or best_d < min_m:
            break
        picked.append(best)
        pool.remove(best)
    return picked


@lru_cache(maxsize=256)
def _layout_cached(site_json: str) -> tuple[int, str, tuple]:
    site = Site.model_validate_json(site_json)
    cov = coverage_m(site)
    chosen: list[dict] = []
    fence_km = max(site.radius_m, 60) / 1000
    for b in range(0, 360, 60):
        la, lo = destination(site.lat, site.lon, b, fence_km)
        chosen.append({"lat": la, "lon": lo, "kind": "fence",
                       "place": f"Site fence ({compass(b)})", "name": ""})

    osm = _places().get(site.site_id, {})
    buildings = [dict(b, kind="structure") for b in osm.get("buildings", [])]
    green = [dict(g, kind="vegetation", name="") for g in osm.get("green", [])]
    # isolated cabins, huts and farms first: they are the most exposed structures
    buildings.sort(key=lambda b: (b["place"] not in ("Cabin", "Mountain hut", "Farm building"),
                                  _m(site.lat, site.lon, b["lat"], b["lon"])))
    chosen += _spread(buildings, chosen, MAX_STRUCTURES, 150)
    chosen += _spread(green, chosen, MAX_VEGETATION, 250)

    # fill the gaps with evenly spaced open-ground points
    d = cov / 3
    grid = []
    for q in range(-3, 4):
        for r in range(-3, 4):
            if 1 <= max(abs(q), abs(r), abs(q + r)) <= 3:
                x, y = d * (q + r / 2), d * (math.sqrt(3) / 2) * r
                b = (math.degrees(math.atan2(x, y)) + 360) % 360
                la, lo = destination(site.lat, site.lon, b, math.hypot(x, y) / 1000)
                grid.append({"lat": la, "lon": lo, "kind": "grid", "place": "Open ground",
                             "name": ""})
    chosen += _spread(grid, chosen, 36, d * 0.7)

    inner = site.radius_m + (cov - site.radius_m) / 2
    for c in chosen:
        dist = _m(site.lat, site.lon, c["lat"], c["lon"])
        c["dist_m"] = int(dist)
        c["bearing"] = round(bearing_deg(site.lat, site.lon, c["lat"], c["lon"]), 1)
        c["ring"] = 0 if dist <= site.radius_m + 60 else 1 if dist <= inner else 2
    chosen.sort(key=lambda c: (c["ring"], c["bearing"]))
    nodes = tuple(
        {"sensor_id": f"{site.site_id}-S{i:02d}", "label": f"S-{i:02d}",
         "lat": round(c["lat"], 6), "lon": round(c["lon"], 6), "kind": c["kind"],
         "place": c["place"], "name": c.get("name", ""), "dist_m": c["dist_m"],
         "bearing": c["bearing"], "ring": c["ring"]}
        for i, c in enumerate(chosen))
    source = "openstreetmap" if (buildings or green) else "grid"
    return cov, source, nodes


def layout(site: Site) -> tuple[int, str, list[dict]]:
    """(coverage_m, source, nodes) — deterministic for a given site."""
    cov, source, nodes = _layout_cached(site.model_dump_json())
    return cov, source, [dict(n) for n in nodes]


def fire_estimate(site: Site, nodes: list[SensorNode]) -> FireEstimate | None:
    """Combine the hot sensors into one fire position: heat-weighted centroid of the warm
    and fire sensors (weight = excess over the median temperature of all sensors, squared)."""
    temps = [n.temp_c for n in nodes if n.temp_c is not None]
    hot = [n for n in nodes if n.state in ("warm", "fire") and n.temp_c is not None]
    if not hot:
        return None
    base = statistics.median(temps)
    w = [max(1.0, n.temp_c - base) ** 2 for n in hot]
    tw = sum(w)
    lat = sum(n.lat * wi for n, wi in zip(hot, w)) / tw
    lon = sum(n.lon * wi for n, wi in zip(hot, w)) / tw
    spread = math.sqrt(sum(wi * _m(lat, lon, n.lat, n.lon) ** 2 for n, wi in zip(hot, w)) / tw)
    hottest = max(hot, key=lambda n: n.temp_c)
    return FireEstimate(
        lat=round(lat, 6), lon=round(lon, 6),
        radius_m=int(max(150, spread + 120)) if len(hot) > 1 else 300,
        sensors=len(hot),
        confidence="high" if len(hot) >= 3 else "medium" if len(hot) == 2 else "low",
        distance_m=int(_m(site.lat, site.lon, lat, lon)),
        bearing_deg=int(bearing_deg(site.lat, site.lon, lat, lon)),
        hottest=f"{hottest.label} · {hottest.place} ({hottest.temp_c}°C)")


class SiteSim:
    """All readings for one site's sensors over the 144-step replay grid."""

    def __init__(self, site: Site, installed_at: str, dets: list, weather: WeatherService):
        self.site = site
        self.installed_at = installed_at
        self.coverage, self.source, self.nodes = layout(site)
        self.steps = grid_steps()
        reach_km = self.coverage / 1000 + 3
        near = [d for d in dets if haversine_km(site.lat, site.lon, d.lat, d.lon) <= reach_km]
        base = []
        for at in self.steps:
            w = weather.get(site.site_id, at)
            hour = parse(at).hour
            base.append((w.temp_c if w else 25.0) - 3
                        + 7 * math.cos((hour - 15) / 24 * 2 * math.pi))

        self.states: dict[str, list[tuple[str, float | None]]] = {}
        self.causes: dict[str, str] = {}
        for n in self.nodes:
            sid = n["sensor_id"]
            hv = _h(sid)
            offset = ((hv % 300) / 100.0) - 1.5
            dead_step = 20 + (hv // 7) % 110 if hv % 100 < 4 else None
            drop_step = 10 + (hv // 11) % 125 if 4 <= hv % 100 < 7 else None
            destroyed = False
            seq: list[tuple[str, float | None]] = []
            for i, at in enumerate(self.steps):
                if destroyed or (dead_step is not None and i >= dead_step):
                    self.causes.setdefault(sid, "Destroyed by fire" if destroyed
                                           else "No heartbeat (battery or radio failure)")
                    seq.append(("offline", None))
                    continue
                win_start = fmt(parse(at) - timedelta(hours=config.DETECTION_WINDOW_HOURS))
                heat = 0.0
                for d in near:
                    if not (win_start < d.observed_at <= at):
                        continue
                    km = haversine_km(n["lat"], n["lon"], d.lat, d.lon)
                    if km > 3:
                        continue
                    age_h = (parse(at) - parse(d.observed_at)).total_seconds() / 3600
                    heat += (d.intensity_frp / 50) * 520 * math.exp(-km / 0.3) \
                        * math.exp(-age_h / 6)
                temp = round(base[i] + offset + min(heat, 700), 1)
                if temp >= DESTROY_C:
                    destroyed = True          # the sensor melts; silent from the next step
                if temp >= FIRE_C:
                    state = "fire"
                elif drop_step is not None and i >= drop_step:
                    state = "dropped"
                elif temp >= WARM_C:
                    state = "warm"
                else:
                    state = "ok"
                seq.append((state, temp))
            self.states[sid] = seq

    def nodes_at(self, i: int) -> list[SensorNode]:
        out = []
        for n in self.nodes:
            sid = n["sensor_id"]
            seq = self.states[sid]
            state, temp = seq[i]
            j = i
            while j > 0 and seq[j - 1][0] == state:
                j -= 1
            last = j - 1 if state == "offline" else i
            cause = self.causes.get(sid, "")
            battery = 0 if state == "offline" and cause.startswith("No heartbeat") \
                else max(5, 100 - _h(sid, "b") % 17 - int(i * 0.08))
            note = {"ok": "Normal", "warm": "Above ambient: heat nearby",
                    "fire": "Fire temperature at this sensor", "offline": cause,
                    "dropped": "Tilt alarm: sensor moved or knocked over, position unreliable",
                    }[state]
            out.append(SensorNode(
                sensor_id=sid, site_id=self.site.site_id, label=n["label"], ring=n["ring"],
                lat=n["lat"], lon=n["lon"], kind=n["kind"], place=n["place"], name=n["name"],
                dist_m=n["dist_m"], bearing_deg=int(n["bearing"]), state=state, temp_c=temp,
                battery_pct=battery, last_seen=self.steps[last] if last >= 0 else None,
                state_since=self.steps[j], note=note))
        return out

    def events_until(self, i: int) -> list[SensorEvent]:
        out = []
        for n in self.nodes:
            sid = n["sensor_id"]
            seq = self.states[sid]
            for k in range(1, i + 1):
                prev, cur = seq[k - 1][0], seq[k][0]
                if prev == cur:
                    continue
                kind = "recovered" if cur == "ok" else cur
                detail = {
                    "warm": f"{seq[k][1]}°C, above ambient: heat nearby",
                    "fire": f"{seq[k][1]}°C, fire temperature at the sensor",
                    "offline": self.causes.get(sid, "Offline"),
                    "dropped": "Tilt alarm: sensor moved or knocked over",
                    "recovered": f"Back to normal ({seq[k][1]}°C)",
                }[kind]
                out.append(SensorEvent(at=self.steps[k], sensor_id=sid,
                                       site_id=self.site.site_id, site_name=self.site.name,
                                       label=n["label"], place=n["place"], kind=kind,
                                       temp_c=seq[k][1], detail=detail))
        return out

    def mesh_at(self, nodes: list[SensorNode]) -> SensorMesh:
        counts = {s: 0 for s in STATES}
        placed = {k: 0 for k in KINDS}
        for n in nodes:
            counts[n.state] += 1
            placed[n.kind] += 1
        return SensorMesh(site_id=self.site.site_id, site_name=self.site.name,
                          lat=self.site.lat, lon=self.site.lon, installed_at=self.installed_at,
                          coverage_m=self.coverage, nodes=len(nodes), counts=counts,
                          placement=placed, layout_source=self.source,
                          ground_fire=counts["fire"] > 0,
                          fire_estimate=fire_estimate(self.site, nodes))


_cache: dict[tuple, SiteSim] = {}


def site_sim(site: Site, installed_at: str) -> SiteSim:
    key = (site.model_dump_json(), installed_at)
    if key not in _cache:
        dets = [d for d in FileDetectionsProvider().detections() if d.confidence in ("n", "h")]
        _cache[key] = SiteSim(site, installed_at, dets, WeatherService())
    return _cache[key]


def snapshot(sites: dict[str, Site], installs: dict[str, str], at: str,
             site_id: str | None = None, event_limit: int = 200):
    """(meshes, nodes, events newest first) at replay time `at`."""
    i = grid_steps().index(at)
    meshes, nodes, events = [], [], []
    for sid in sorted(installs):
        if sid not in sites or (site_id and sid != site_id):
            continue
        sim = site_sim(sites[sid], installs[sid])
        ns = sim.nodes_at(i)
        meshes.append(sim.mesh_at(ns))
        nodes.extend(ns)
        events.extend(sim.events_until(i))
    events.sort(key=lambda e: (e.at, e.sensor_id), reverse=True)
    return meshes, nodes, events[:event_limit]


def ground_fire_sites(sites: dict[str, Site], installs: dict[str, str], at: str) -> set[str]:
    meshes, _, _ = snapshot(sites, installs, at, event_limit=0)
    return {m.site_id for m in meshes if m.ground_fire}
