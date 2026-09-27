"""wildfire.py — WildfireProvider interface + FileDetectionsProvider (§5.1, §5.8)."""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path

from app.geo import haversine_km
from app.models import Detection

_DETECTIONS = Path(__file__).resolve().parent.parent.parent / "data" / "detections.csv"


class WildfireProvider:
    def detections(self) -> list[Detection]:
        raise NotImplementedError


class FileDetectionsProvider(WildfireProvider):
    """Reads the committed data/detections.csv (FIRMS output or synthetic fallback)."""

    def __init__(self, path: Path = _DETECTIONS) -> None:
        self._path = path

    def detections(self) -> list[Detection]:
        if not self._path.exists():
            return []
        out: list[Detection] = []
        for r in csv.DictReader(open(self._path, encoding="utf-8-sig")):
            out.append(Detection(
                id=r["id"],
                source=r["source"],
                external_id=r["external_id"] or None,
                lat=float(r["lat"]),
                lon=float(r["lon"]),
                observed_at=r["observed_at"],
                received_at=r["received_at"],
                satellite=r["satellite"],
                confidence=r["confidence"],
                intensity_frp=float(r["intensity_frp"]),
            ))
        return out


class FirmsLiveProvider:
    """NASA FIRMS near-real-time active fire detections, for live operation.

    The replay scores the committed August 2025 archive; this answers "what is burning near
    this site in the last N hours, right now". NRT products lag the satellite pass by roughly
    3 hours, which is a property of the data and not something we can improve.

    Needs FIRMS_MAP_KEY (free). Like the live weather provider it never raises: a dead
    upstream must degrade to "no live data", not take a request down.
    """

    BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    SOURCES = ("VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT")

    def __init__(self, map_key: str, ttl_s: int = 900) -> None:
        self._key = map_key
        self._ttl = ttl_s
        self._cache: dict[str, tuple[float, list[dict]]] = {}

    def near(self, lat: float, lon: float, radius_km: float = 25.0,
             days: int = 1) -> list[dict] | None:
        import csv as _csv
        import io as _io
        import time as _time

        ck = f"{lat:.2f},{lon:.2f},{radius_km:.0f},{days}"
        hit = self._cache.get(ck)
        if hit and _time.time() - hit[0] < self._ttl:
            return hit[1]

        d_lat = radius_km / 111.0
        d_lon = radius_km / (111.0 * max(0.01, math.cos(math.radians(lat))))
        bbox = f"{lon - d_lon:.4f},{lat - d_lat:.4f},{lon + d_lon:.4f},{lat + d_lat:.4f}"
        rows: list[dict] = []
        try:
            import httpx

            for source in self.SOURCES:
                r = httpx.get(f"{self.BASE}/{self._key}/{source}/{bbox}/{days}", timeout=10.0)
                if not r.text.lstrip().lower().startswith("latitude"):
                    continue
                for rec in _csv.DictReader(_io.StringIO(r.text)):
                    hhmm = str(rec.get("acq_time", "0")).zfill(4)
                    rows.append({
                        "lat": round(float(rec["latitude"]), 5),
                        "lon": round(float(rec["longitude"]), 5),
                        "observed_at": f"{rec['acq_date']}T{hhmm[:2]}:{hhmm[2:]}:00Z",
                        "satellite": rec.get("satellite", ""),
                        "confidence": ("h" if str(rec.get("confidence", "n")).lower()
                                       .startswith("h") else "n"),
                        "frp": round(float(rec.get("frp", 0.0)), 1),
                        "distance_km": round(
                            haversine_km(lat, lon, float(rec["latitude"]),
                                         float(rec["longitude"])), 2),
                    })
        except Exception:  # noqa: BLE001 — see the class docstring
            return None
        rows = [r for r in rows if r["distance_km"] <= radius_km]
        rows.sort(key=lambda r: r["distance_km"])
        self._cache[ck] = (_time.time(), rows)
        return rows


def firms_live() -> "FirmsLiveProvider | None":
    key = os.environ.get("FIRMS_MAP_KEY", "")
    return FirmsLiveProvider(key) if key else None
