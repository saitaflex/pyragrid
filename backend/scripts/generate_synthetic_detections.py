"""generate_synthetic_detections.py — offline deterministic fallback (TEAM_PLAN.md §5.8).

Two spreading fires observed twice daily; ~720 detections. random.seed(42).
Writes data/detections.csv, appends data/ingestion_runs.json, updates data/meta.json.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.geo import destination  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
Z = "%Y-%m-%dT%H:%M:%SZ"


def _dt(s: str) -> datetime:
    return datetime.strptime(s, Z).replace(tzinfo=timezone.utc)


FIRES = [
    {"lat": 42.245, "lon": -7.360, "ignition": _dt("2025-08-08T13:00:00Z"),
     "bearing": 45.0, "speed": 0.25, "max_radius": 20.0, "stop": _dt("2025-08-20T13:00:00Z")},
    {"lat": 42.340, "lon": -7.160, "ignition": _dt("2025-08-13T13:00:00Z"),
     "bearing": 300.0, "speed": 0.30, "max_radius": 25.0, "stop": _dt("2025-08-24T13:00:00Z")},
]

REPLAY_START = _dt("2025-08-08T00:00:00Z")
REPLAY_END = _dt("2025-08-26T00:00:00Z")


def overpasses() -> list[datetime]:
    times = []
    day = REPLAY_START
    while day < REPLAY_END:
        for hh in (2, 13):
            t = day.replace(hour=hh)
            if REPLAY_START <= t < REPLAY_END:
                times.append(t)
        day += timedelta(days=1)
    return times


def main() -> None:
    random.seed(42)
    rows = []
    received = datetime.now(timezone.utc).strftime(Z)
    for t in overpasses():
        for fire in FIRES:
            if not (fire["ignition"] <= t <= fire["stop"]):
                continue
            hours = (t - fire["ignition"]).total_seconds() / 3600.0
            r = min(fire["max_radius"], fire["speed"] * hours)
            for _ in range(15):
                dist = max(0.2, r + random.uniform(-1, 1))
                brg = fire["bearing"] + random.uniform(-60, 60)
                lat, lon = destination(fire["lat"], fire["lon"], brg, dist)
                conf = "h" if random.random() < 0.6 else "n"
                frp = round(random.uniform(5, 80), 1)
                rows.append({
                    "source": "synthetic_fallback",
                    "external_id": "",
                    "lat": round(lat, 5),
                    "lon": round(lon, 5),
                    "observed_at": t.strftime(Z),
                    "received_at": received,
                    "satellite": "N20",
                    "confidence": conf,
                    "intensity_frp": frp,
                })

    # Deduplicate on (lat 4dp, lon 4dp, observed_at); sort by observed_at; assign ids.
    seen, deduped = set(), []
    for row in rows:
        key = (round(row["lat"], 4), round(row["lon"], 4), row["observed_at"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    deduped.sort(key=lambda r: r["observed_at"])
    for i, row in enumerate(deduped, start=1):
        row["id"] = f"d-{i:04d}"

    DATA.mkdir(parents=True, exist_ok=True)
    cols = ["id", "source", "external_id", "lat", "lon", "observed_at",
            "received_at", "satellite", "confidence", "intensity_frp"]
    with open(DATA / "detections.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in deduped:
            w.writerow({c: row[c] for c in cols})

    run = {
        "run_id": "run-synthetic-0001",
        "source": "synthetic_fallback",
        "started_at": received,
        "completed_at": received,
        "records_received": len(rows),
        "records_inserted": len(deduped),
        "records_rejected": 0,
        "error_message": None,
    }
    (DATA / "ingestion_runs.json").write_text(
        json.dumps([run], indent=1), encoding="utf-8")
    (DATA / "meta.json").write_text(
        json.dumps({"data_source": "synthetic_fallback", "fetched_at": received}, indent=1),
        encoding="utf-8")
    print(f"Wrote {len(deduped)} detections (received {len(rows)}).")


if __name__ == "__main__":
    main()
