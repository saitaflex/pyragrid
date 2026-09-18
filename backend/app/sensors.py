"""sensors.py — optional ground temperature mesh (hexagonal layout) per site.

Each installed site gets a hexagonal grid of nodes (3 rings = 37 nodes) covering the site
plus a buffer, so fire is sensed before it reaches the fence. Readings are simulated over
the replay grid from the same detections the engine scores: ambient temperature (weather +
day/night cycle) plus radiant heat from nearby detections. Nodes can go warm, report fire,
be destroyed by fire (offline), run out of battery (offline) or be knocked over (dropped).
A production mesh would post real readings (e.g. LoRaWAN gateway -> ingest API) instead.
"""
from __future__ import annotations

import hashlib
import math
from datetime import timedelta

from app import config
from app.geo import haversine_km
from app.models import SensorEvent, SensorMesh, SensorNode, Site
from app.providers.weather import WeatherService
from app.providers.wildfire import FileDetectionsProvider
from app.replay import fmt, grid_steps, parse

RINGS = 3
WARM_C = 45.0
FIRE_C = 65.0
DESTROY_C = 150.0
_M_PER_DEG = 111_320.0
STATES = ("ok", "warm", "fire", "offline", "dropped")


def _h(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:12], 16)


def mesh_geometry(site: Site) -> tuple[int, int, list[dict]]:
    """Return (spacing_m, coverage_m, nodes): pointy-top hex cells in axial coordinates,
    ordered ring by ring, clockwise from north."""
    buffer_m = max(1000, site.radius_m)
    coverage = site.radius_m + buffer_m
    d = coverage / RINGS                      # centre-to-centre spacing
    a = d / math.sqrt(3)                      # hex circumradius
    coslat = max(0.01, math.cos(math.radians(site.lat)))

    def to_ll(x: float, y: float) -> tuple[float, float]:
        return site.lon + x / (_M_PER_DEG * coslat), site.lat + y / _M_PER_DEG

    cells = []
    for q in range(-RINGS, RINGS + 1):
        for r in range(-RINGS, RINGS + 1):
            ring = max(abs(q), abs(r), abs(q + r))
            if ring > RINGS:
                continue
            x, y = d * (q + r / 2), d * (math.sqrt(3) / 2) * r
            cells.append((ring, round((math.degrees(math.atan2(x, y)) + 360) % 360, 3), x, y))
    cells.sort(key=lambda c: (c[0], c[1]))

    nodes = []
    for i, (ring, bearing, x, y) in enumerate(cells):
        lon, lat = to_ll(x, y)
        poly = []
        for k in range(7):
            ang = math.radians(60 * (k % 6) - 30)
            plon, plat = to_ll(x + a * 0.96 * math.cos(ang), y + a * 0.96 * math.sin(ang))
            poly.append([round(plon, 6), round(plat, 6)])
        nodes.append({"sensor_id": f"{site.site_id}-H{i:02d}", "label": f"H-{i:02d}",
                      "ring": ring, "bearing": bearing, "lat": round(lat, 6),
                      "lon": round(lon, 6), "hex": poly})
    return int(d), int(coverage), nodes


class SiteSim:
    """All readings for one site's mesh over the 144-step replay grid."""

    def __init__(self, site: Site, installed_at: str, dets: list, weather: WeatherService):
        self.site = site
        self.installed_at = installed_at
        self.spacing, self.coverage, self.nodes = mesh_geometry(site)
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
                    destroyed = True          # the node melts; silent from the next step
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
                    "fire": "Fire temperature at this node", "offline": cause,
                    "dropped": "Tilt alarm: node moved or knocked over, position unreliable",
                    }[state]
            out.append(SensorNode(
                sensor_id=sid, site_id=self.site.site_id, label=n["label"], ring=n["ring"],
                lat=n["lat"], lon=n["lon"], hex=n["hex"], state=state, temp_c=temp,
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
                    "fire": f"{seq[k][1]}°C, fire temperature at the node",
                    "offline": self.causes.get(sid, "Offline"),
                    "dropped": "Tilt alarm: node moved or knocked over",
                    "recovered": f"Back to normal ({seq[k][1]}°C)",
                }[kind]
                out.append(SensorEvent(at=self.steps[k], sensor_id=sid,
                                       site_id=self.site.site_id, site_name=self.site.name,
                                       label=n["label"], kind=kind, temp_c=seq[k][1],
                                       detail=detail))
        return out

    def mesh_at(self, nodes: list[SensorNode]) -> SensorMesh:
        counts = {s: 0 for s in STATES}
        for n in nodes:
            counts[n.state] += 1
        return SensorMesh(site_id=self.site.site_id, site_name=self.site.name,
                          lat=self.site.lat, lon=self.site.lon, installed_at=self.installed_at,
                          spacing_m=self.spacing, coverage_m=self.coverage, nodes=len(nodes),
                          counts=counts, ground_fire=counts["fire"] > 0)


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
