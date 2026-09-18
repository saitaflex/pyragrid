"""geo.py — geometry helpers (TEAM_PLAN.md §5.4).

Pure functions; same maths as PostGIS ST_Distance/bearing for points.
"""
from __future__ import annotations

import math

from app.config import EARTH_RADIUS_KM

_COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def angdiff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def compass(deg: float) -> str:
    return _COMPASS[int((deg + 22.5) // 45) % 8]


def destination(lat: float, lon: float, bearing: float, km: float) -> tuple[float, float]:
    """Great-circle destination point (used by the synthetic generator)."""
    d = km / EARTH_RADIUS_KM
    br = math.radians(bearing)
    p1 = math.radians(lat)
    l1 = math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(br))
    l2 = l1 + math.atan2(
        math.sin(br) * math.sin(d) * math.cos(p1),
        math.cos(d) - math.sin(p1) * math.sin(p2),
    )
    return math.degrees(p2), (math.degrees(l2) + 540) % 360 - 180


def edge_distance_km(site, det) -> float:
    """Distance from a detection to the site's edge (0 if inside the radius)."""
    centre = haversine_km(site.lat, site.lon, det.lat, det.lon)
    return max(0.0, centre - site.radius_m / 1000.0)
