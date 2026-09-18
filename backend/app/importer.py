"""importer.py — CSV/GeoJSON asset validation and component generation (§5.3)."""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

from app import config
from app.models import Component, ImportReport, RejectedRow, Site

SITE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
COLUMNS = ["site_id", "name", "type", "lat", "lon", "radius_m", "value_eur",
           "fuel_class", "personnel_on_site", "primary_access_bearing_deg", "criticality"]
_SEED = Path(__file__).resolve().parent.parent / "data" / "seed_sites.csv"


def build_components(value_eur: int, site_type: str) -> list[Component]:
    """Split value into components by type; remainder added to the first (exact sum)."""
    shares = config.COMPONENT_SHARES[site_type]
    values = [round(value_eur * share) for _, share in shares]
    values[0] += value_eur - sum(values)
    return [Component(name=name, value_eur=v) for (name, _), v in zip(shares, values)]


def _validate_row(raw: dict, seen_ids: set[str]) -> tuple[Site | None, str | None]:
    try:
        sid = (raw.get("site_id") or "").strip()
        if not SITE_ID_RE.match(sid):
            return None, "invalid site_id"
        if sid in seen_ids:
            return None, "duplicate site_id"
        name = (raw.get("name") or "").strip()
        if not name:
            return None, "empty name"
        stype = (raw.get("type") or "").strip()
        if stype not in config.SITE_TYPES:
            return None, "invalid type"
        fuel = (raw.get("fuel_class") or "").strip()
        if fuel not in config.FUEL_CLASSES:
            return None, "invalid fuel_class"
        lat = float(raw["lat"]); lon = float(raw["lon"])
        if not (-90 <= lat <= 90):
            return None, "lat out of range"
        if not (-180 <= lon <= 180):
            return None, "lon out of range"
        radius = int(float(raw["radius_m"]))
        if not (10 <= radius <= 10000):
            return None, "radius_m out of range"
        value_eur = int(float(raw["value_eur"]))
        if value_eur < 0:
            return None, "value_eur negative"
        personnel = int(float(raw["personnel_on_site"]))
        if personnel < 0:
            return None, "personnel_on_site negative"
        bearing = int(float(raw["primary_access_bearing_deg"]))
        if not (0 <= bearing <= 359):
            return None, "bearing out of range"
        criticality = int(float(raw["criticality"]))
        if not (1 <= criticality <= 5):
            return None, "criticality out of range"
    except (KeyError, ValueError, TypeError):
        return None, "malformed row"

    site = Site(
        site_id=sid, name=name, type=stype, lat=lat, lon=lon, radius_m=radius,
        value_eur=value_eur, fuel_class=fuel, personnel_on_site=personnel,
        primary_access_bearing_deg=bearing, criticality=criticality,
        components=build_components(value_eur, stype),
    )
    return site, None


def _rows_from_geojson(text: str) -> list[dict]:
    fc = json.loads(text)
    rows = []
    for feat in fc.get("features", []):
        props = dict(feat.get("properties", {}))
        coords = feat.get("geometry", {}).get("coordinates", [None, None])
        props["lon"], props["lat"] = coords[0], coords[1]
        rows.append(props)
    return rows


def parse_assets(data: bytes, filename: str) -> tuple[list[Site], ImportReport]:
    """Parse and validate an upload. Raises ValueError on wrong type / too many rows."""
    text = data.decode("utf-8-sig")
    lower = filename.lower()
    if lower.endswith(".csv"):
        rows = list(csv.DictReader(io.StringIO(text)))
    elif lower.endswith(".geojson") or lower.endswith(".json"):
        rows = _rows_from_geojson(text)
    else:
        raise ValueError("unsupported file type")

    if len(rows) > config.MAX_IMPORT_ROWS:
        raise ValueError(f"too many rows (max {config.MAX_IMPORT_ROWS})")

    sites: list[Site] = []
    rejected: list[RejectedRow] = []
    seen: set[str] = set()
    for i, raw in enumerate(rows, start=1):
        site, reason = _validate_row(raw, seen)
        if site is None:
            sid = (raw.get("site_id") or "").strip() or None
            rejected.append(RejectedRow(row=i, site_id=sid, reason=reason))
        else:
            seen.add(site.site_id)
            sites.append(site)

    report = ImportReport(accepted=len(sites), rejected=rejected, total_sites=len(sites))
    return sites, report


def seed_sites() -> list[Site]:
    """The 20 demo sites as Site objects (also served as sample.csv)."""
    sites, _ = parse_assets(_SEED.read_bytes(), "seed_sites.csv")
    return sites


def sample_csv_text() -> str:
    return _SEED.read_text(encoding="utf-8-sig")
