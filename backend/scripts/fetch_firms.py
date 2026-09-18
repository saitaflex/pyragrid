"""fetch_firms.py — NASA FIRMS VIIRS detections (TEAM_PLAN.md §5.8).

Needs FIRMS_MAP_KEY (free from the FIRMS website). One call per date and source.
On zero rows for every date, falls back to NRT sources, then to the synthetic generator.
Writes data/detections.csv, data/ingestion_runs.json, data/meta.json. Cite NASA FIRMS.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import BBOX  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
Z = "%Y-%m-%dT%H:%M:%SZ"
BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
SP = ["VIIRS_SNPP_SP", "VIIRS_NOAA20_SP"]
NRT = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT"]
DATES = [date(2025, 8, 8) + timedelta(days=i) for i in range(18)]  # 08-08..08-25


def _area(map_key: str, source: str, day: date, client: httpx.Client):
    bbox = f"{BBOX['west']},{BBOX['south']},{BBOX['east']},{BBOX['north']}"
    url = f"{BASE}/{map_key}/{source}/{bbox}/1/{day.isoformat()}"
    r = client.get(url, timeout=60)
    text = r.text
    if not text.lstrip().lower().startswith("latitude"):
        print(f"  {source} {day}: error/empty -> {text[:80]!r}")
        return None
    return list(csv.DictReader(io.StringIO(text)))


def _collect(map_key: str, sources: list[str], received: str, client: httpx.Client):
    rows, rejected = [], 0
    for source in sources:
        src_tag = "firms_nrt" if source.endswith("NRT") else "firms_sp"
        for day in DATES:
            recs = _area(map_key, source, day, client)
            if recs is None:
                rejected += 1
                time.sleep(1)
                continue
            for rec in recs:
                hhmm = str(rec.get("acq_time", "0")).zfill(4)
                observed = f"{rec['acq_date']}T{hhmm[:2]}:{hhmm[2:]}:00Z"
                rows.append({
                    "source": src_tag,
                    "external_id": "",
                    "lat": round(float(rec["latitude"]), 5),
                    "lon": round(float(rec["longitude"]), 5),
                    "observed_at": observed,
                    "received_at": received,
                    "satellite": rec.get("satellite", ""),
                    "confidence": "h" if str(rec.get("confidence", "n")).lower().startswith("h") else "n",
                    "intensity_frp": round(float(rec.get("frp", 0.0)), 1),
                })
            time.sleep(1)
    return rows, rejected


def main() -> None:
    map_key = os.environ.get("FIRMS_MAP_KEY", "")
    if not map_key:
        print("No FIRMS_MAP_KEY; running the synthetic generator instead.")
        import generate_synthetic_detections as gen
        gen.main()
        return

    received = datetime.now(timezone.utc).strftime(Z)
    with httpx.Client() as client:
        rows, rejected = _collect(map_key, SP, received, client)
        if not rows:
            rows, rejected = _collect(map_key, NRT, received, client)

    if not rows:
        print("FIRMS returned no rows; running the synthetic generator instead.")
        import generate_synthetic_detections as gen
        gen.main()
        return

    # Deduplicate on (lat 4dp, lon 4dp, observed_at); sort; assign ids.
    seen, deduped = set(), []
    for row in rows:
        key = (round(row["lat"], 4), round(row["lon"], 4), row["observed_at"])
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    deduped.sort(key=lambda r: r["observed_at"])
    for i, row in enumerate(deduped, start=1):
        row["id"] = f"d-{i:04d}"

    cols = ["id", "source", "external_id", "lat", "lon", "observed_at",
            "received_at", "satellite", "confidence", "intensity_frp"]
    with open(DATA / "detections.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in deduped:
            w.writerow({c: row[c] for c in cols})

    data_source = deduped[0]["source"]
    run = {
        "run_id": f"run-firms-{received}",
        "source": data_source,
        "started_at": received,
        "completed_at": datetime.now(timezone.utc).strftime(Z),
        "records_received": len(rows),
        "records_inserted": len(deduped),
        "records_rejected": rejected,
        "error_message": None,
    }
    (DATA / "ingestion_runs.json").write_text(json.dumps([run], indent=1), encoding="utf-8")
    (DATA / "meta.json").write_text(
        json.dumps({"data_source": data_source, "fetched_at": received}, indent=1),
        encoding="utf-8")
    print(f"Wrote {len(deduped)} FIRMS detections (source {data_source}).")


if __name__ == "__main__":
    main()
