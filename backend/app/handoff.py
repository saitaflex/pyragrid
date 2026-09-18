"""handoff.py — Firefighter Handoff Pack builder (TEAM_PLAN.md §5.11)."""
from __future__ import annotations

from datetime import datetime, timezone

from app import config
from app.geo import destination
from app.models import Contact, HandoffPack, Hazard, Site, SiteStatus, WaterPoint

_HAZARDS = {
    "solar_farm": [
        ("PV modules", "electrical", "PV modules produce DC voltage whenever they are exposed "
         "to light and cannot be fully de-energised in daylight."),
        ("Inverter station", "electrical", "High-voltage equipment."),
    ],
    "substation": [
        ("Transformers", "electrical", "High-voltage equipment."),
        ("Transformer insulating oil", "fuel_oil",
         "Oil-filled transformers contain flammable insulating oil."),
    ],
    "wind_farm": [
        ("Turbines", "height",
         "Falling debris possible if a nacelle burns; keep clear of the tower base."),
        ("Substation", "electrical", "High-voltage equipment."),
    ],
    "telecom_tower": [
        ("Backup batteries", "battery", "Backup batteries and electrical equipment."),
        ("Tower", "height", "Height hazard."),
    ],
    "forest_block": [
        ("No built hazards", "none", "Standing timber; limited road access."),
    ],
    "test_plot": [
        ("Weather station and camera", "electrical", "Low-voltage equipment only."),
    ],
}


def _phone(site_id: str) -> str:
    digits = "".join(c for c in site_id if c.isdigit())
    return "+34 600 000 " + (digits[-3:] if len(digits) >= 3 else "000")


def build_pack(site: Site, status: SiteStatus, headline: str, at: str) -> HandoffPack:
    primary = site.primary_access_bearing_deg
    dist_km = site.radius_m / 1000.0 + 0.3
    a_lat, a_lon = destination(site.lat, site.lon, (primary + 90) % 360, dist_km)
    b_lat, b_lon = destination(site.lat, site.lon, (primary + 270) % 360, dist_km)
    water = [
        WaterPoint(name="Water tank A", lat=round(a_lat, 5), lon=round(a_lon, 5), capacity_m3=50),
        WaterPoint(name="Water tank B", lat=round(b_lat, 5), lon=round(b_lon, 5), capacity_m3=30),
    ]
    hazards = [Hazard(name=n, kind=k, note=note) for n, k, note in _HAZARDS[site.type]]
    return HandoffPack(
        site_id=site.site_id, site_name=site.name, type=site.type, at=at,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        lat=site.lat, lon=site.lon, level=status.level, score=status.score, headline=headline,
        personnel_on_site=site.personnel_on_site, criticality=site.criticality,
        access_routes=status.access_routes, hazards=hazards, water_points=water,
        contact=Contact(role="Site manager (simulated)", phone=_phone(site.site_id)),
        disclaimer=config.DISCLAIMER_HANDOFF,
    )
