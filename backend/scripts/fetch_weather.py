"""fetch_weather.py — Open-Meteo archive weather per site (TEAM_PLAN.md §5.8).

Saves hourly arrays to data/weather/{site_id}.json. Times are GMT = UTC.
`wind_direction_10m` is the direction the wind comes FROM.
Run once and commit the outputs; sites without a file use AssumedWeatherProvider.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import httpx

DATA = Path(__file__).resolve().parent.parent / "data"
WEATHER = DATA / "weather"
URL = "https://archive-api.open-meteo.com/v1/archive"
PARAMS = (
    "hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m"
    "&wind_speed_unit=kmh&timezone=GMT&start_date=2025-08-08&end_date=2025-08-25"
)


def main() -> None:
    WEATHER.mkdir(parents=True, exist_ok=True)
    sites = list(csv.DictReader(open(DATA / "seed_sites.csv", encoding="utf-8-sig")))
    with httpx.Client(timeout=30) as client:
        for s in sites:
            url = f"{URL}?latitude={s['lat']}&longitude={s['lon']}&{PARAMS}"
            try:
                r = client.get(url)
                r.raise_for_status()
                hourly = r.json()["hourly"]
                (WEATHER / f"{s['site_id']}.json").write_text(
                    json.dumps(hourly), encoding="utf-8")
                print(f"OK {s['site_id']}")
            except Exception as e:  # noqa: BLE001 - log and continue
                print(f"FAIL {s['site_id']}: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
