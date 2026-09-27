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


class WeatherApiProvider(WeatherProvider):
    """Real-time current conditions from weatherapi.com, for live operation.

    The replay runs on August 2025, so historical hours come from the committed Open-Meteo
    archive; this provider answers "what is the weather at this site right now", which is
    what a real deployment scores against. Needs WEATHERAPI_KEY. Never raises: a weather
    provider that throws would take the whole risk score down with it, so a failure returns
    None and the chain falls through to the next provider.
    """

    BASE = "https://api.weatherapi.com/v1/current.json"

    def __init__(self, key: str, ttl_s: int = 600) -> None:
        self._key = key
        self._ttl = ttl_s
        self._cache: dict[str, tuple[float, Optional[WeatherReading]]] = {}

    def current(self, lat: float, lon: float) -> Optional[WeatherReading]:
        import time as _time

        ck = f"{lat:.3f},{lon:.3f}"
        hit = self._cache.get(ck)
        if hit and _time.time() - hit[0] < self._ttl:
            return hit[1]
        try:
            import httpx

            r = httpx.get(self.BASE, params={"key": self._key, "q": ck, "aqi": "no"},
                          timeout=8.0)
            r.raise_for_status()
            c = r.json()["current"]
            reading = WeatherReading(
                temp_c=float(c["temp_c"]), rh_pct=float(c["humidity"]),
                speed_kmh=float(c["wind_kph"]),
                from_deg=int(round(float(c["wind_degree"]))) % 360,
                status="observed",
            )
        except Exception:  # noqa: BLE001 — see the class docstring
            reading = None
        self._cache[ck] = (_time.time(), reading)
        return reading

    def get(self, site_id: str, at: str) -> Optional[WeatherReading]:
        """Not used for replay times: the archive owns history. See `current()`."""
        return None


def live_provider() -> Optional[WeatherApiProvider]:
    key = os.environ.get("WEATHERAPI_KEY", "")
    return WeatherApiProvider(key) if key else None
