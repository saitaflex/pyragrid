"""scoring.py — transparent risk engine rules-1.0 (TEAM_PLAN.md §5.5).

Produces a SiteStatus (sop_actions left empty; filled at request time from current rules).
"""
from __future__ import annotations

import math

from app import config
from app.geo import angdiff, bearing_deg, compass, edge_distance_km
from app.models import (
    AccessRoute, Factors, FactorStatuses, Site, SiteStatus, Weather, Wind,
)
from app.providers.weather import WeatherReading


def _c(x: float) -> float:
    return max(0.0, min(1.0, x))


def _level_for(score: int) -> str:
    for threshold, level in config.LEVELS:
        if score <= threshold:
            return level
    return "CRITICAL"


def score_site(site: Site, weather: WeatherReading | None, dets: list) -> tuple[SiteStatus, str]:
    """Return (SiteStatus with empty sop_actions, headline string)."""
    weather_known = weather is not None

    if weather_known:
        weather_pts = 15.0 * (
            _c((weather.temp_c - 20) / 20)
            + _c((60 - weather.rh_pct) / 50)
            + _c(weather.speed_kmh / 40)
        ) / 3.0
        wind_to = (weather.from_deg + 180) % 360
    else:
        weather_pts = None
        wind_to = None

    fuel_pts = 15.0 * config.FUEL_FACTOR[site.fuel_class]
    vuln_pts = 10.0 * config.VULNERABILITY[site.type]

    # Candidate detections within 25 km of the site edge; pick the highest prox+wind.
    candidates = []
    for d in dets:
        dist = edge_distance_km(site, d)
        if dist > config.FIRE_RADIUS_KM:
            continue
        prox = 35.0 * _c(1 - dist / config.FIRE_RADIUS_KM)
        if weather_known:
            align = max(0.0, math.cos(math.radians(
                angdiff(wind_to, bearing_deg(d.lat, d.lon, site.lat, site.lon)))))
            wind_pts = 25.0 * align * min(1.0, weather.speed_kmh / 30)
        else:
            wind_pts = 0.0
        candidates.append((prox + wind_pts, dist, d.id, prox, wind_pts, d))

    if candidates:
        # max key; ties -> smaller dist, then smaller detection id
        candidates.sort(key=lambda t: (-t[0], t[1], t[2]))
        _, dist, _, prox, wind_pts, chosen = candidates[0]
        nearest_fire_km = round(dist, 1)
        fire_bearing_deg = round(bearing_deg(site.lat, site.lon, chosen.lat, chosen.lon)) % 360
        triggering_id = chosen.id
        if weather_known:
            cosv = math.cos(math.radians(
                angdiff(wind_to, bearing_deg(chosen.lat, chosen.lon, site.lat, site.lon))))
            fire_moving = cosv > 0.5
            relation = "toward site" if cosv > 0.5 else ("away from site" if cosv < -0.5 else "crosswind")
        else:
            fire_moving = None
            relation = "unknown"
    else:
        prox = 0.0
        wind_pts = 0.0
        nearest_fire_km = fire_bearing_deg = triggering_id = fire_moving = None
        relation = None

    proximity = round(prox, 1)
    wind_alignment = round(wind_pts, 1) if weather_known else None
    weather_factor = round(weather_pts, 1) if weather_known else None
    fuel = round(fuel_pts, 1)
    vulnerability = round(vuln_pts, 1)

    total = sum(v for v in (proximity, wind_alignment, weather_factor, fuel, vulnerability)
                if v is not None)
    score = min(100, math.floor(total + 0.5))
    level = _level_for(score)

    weather_status = weather.status if weather_known else "unknown"
    factor_status = FactorStatuses(
        proximity="observed",
        wind_alignment=weather_status if weather_known else "unknown",
        weather=weather_status,
        fuel="customer_provided",
        vulnerability="customer_provided",
    )

    if nearest_fire_km is not None:
        headline = f"Fire {nearest_fire_km:.1f} km {compass(fire_bearing_deg)}, wind {relation}"
    else:
        headline = "No fire within 25 km"

    primary = site.primary_access_bearing_deg
    secondary = (primary + 180) % 360

    def route_status(bearing: int) -> str:
        if (nearest_fire_km is not None and nearest_fire_km <= config.ROUTE_EXPOSURE_KM
                and angdiff(bearing, fire_bearing_deg) <= 45):
            return "potentially_exposed"
        return "available"

    access_routes = [
        AccessRoute(name="Primary access", bearing_deg=primary, status=route_status(primary)),
        AccessRoute(name="Secondary access", bearing_deg=secondary, status=route_status(secondary)),
    ]

    exposed = site.components if level in ("HIGH", "CRITICAL") else []

    status = SiteStatus(
        site_id=site.site_id, name=site.name, type=site.type, lat=site.lat, lon=site.lon,
        radius_m=site.radius_m, value_eur=site.value_eur,
        personnel_on_site=site.personnel_on_site, criticality=site.criticality,
        score=score, level=level,
        factors=Factors(proximity=proximity, wind_alignment=wind_alignment,
                        weather=weather_factor, fuel=fuel, vulnerability=vulnerability),
        factor_status=factor_status,
        nearest_fire_km=nearest_fire_km, fire_bearing_deg=fire_bearing_deg,
        fire_moving_toward_site=fire_moving, triggering_detection_id=triggering_id,
        wind=Wind(speed_kmh=weather.speed_kmh, from_deg=weather.from_deg, to_deg=wind_to)
        if weather_known else None,
        weather=Weather(temp_c=weather.temp_c, rh_pct=weather.rh_pct) if weather_known else None,
        access_routes=access_routes, exposed_components=list(exposed), sop_actions=[],
    )
    return status, headline
