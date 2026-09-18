"""weather.py — WeatherProvider interface + archive/assumed implementations (§5.1, §5.8)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app import config

_WEATHER_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "weather"


@dataclass
class WeatherReading:
    temp_c: float
    rh_pct: float
    speed_kmh: float
    from_deg: int
    status: str  # "observed" | "assumed"


class WeatherProvider:
    def get(self, site_id: str, at: str) -> Optional[WeatherReading]:
        raise NotImplementedError


class ArchiveFileWeatherProvider(WeatherProvider):
    """Reads data/weather/{site_id}.json (Open-Meteo hourly, GMT=UTC)."""

    def __init__(self, directory: Path = _WEATHER_DIR) -> None:
        self._dir = directory
        self._cache: dict[str, dict] = {}

    def _load(self, site_id: str) -> Optional[dict]:
        if site_id in self._cache:
            return self._cache[site_id]
        f = self._dir / f"{site_id}.json"
        data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
        self._cache[site_id] = data
        return data

    def get(self, site_id: str, at: str) -> Optional[WeatherReading]:
        hourly = self._load(site_id)
        if not hourly:
            return None
        key = at[:13] + ":00"  # "2025-08-14T15:00"
        try:
            i = hourly["time"].index(key)
        except (KeyError, ValueError):
            return None
        return WeatherReading(
            temp_c=float(hourly["temperature_2m"][i]),
            rh_pct=float(hourly["relative_humidity_2m"][i]),
            speed_kmh=float(hourly["wind_speed_10m"][i]),
            from_deg=int(round(float(hourly["wind_direction_10m"][i]))) % 360,
            status="observed",
        )


class AssumedWeatherProvider(WeatherProvider):
    """Constant assumed weather when enabled (ASSUMED_WEATHER=true)."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def get(self, site_id: str, at: str) -> Optional[WeatherReading]:
        if not self.enabled:
            return None
        a = config.ASSUMED_WEATHER
        return WeatherReading(
            temp_c=a["temp_c"], rh_pct=a["rh_pct"], speed_kmh=a["speed_kmh"],
            from_deg=int(a["from_deg"]), status="assumed",
        )


def _assumed_enabled() -> bool:
    return os.environ.get("ASSUMED_WEATHER", "true").lower() == "true"


class WeatherService:
    """Archive first, then assumed; None means weather is unknown for this site/time."""

    def __init__(self) -> None:
        self._archive = ArchiveFileWeatherProvider()
        self._assumed = AssumedWeatherProvider(_assumed_enabled())

    def get(self, site_id: str, at: str) -> Optional[WeatherReading]:
        return self._archive.get(site_id, at) or self._assumed.get(site_id, at)
