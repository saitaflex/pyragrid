"""wildfire.py — WildfireProvider interface + FileDetectionsProvider (§5.1, §5.8)."""
from __future__ import annotations

import csv
from pathlib import Path

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
