"""test_import.py — CSV/GeoJSON import (TEAM_PLAN.md §5.12 T1-M4)."""
import json

from tests.conftest import auth

HEADER = ("site_id,name,type,lat,lon,radius_m,value_eur,fuel_class,"
          "personnel_on_site,primary_access_bearing_deg,criticality")


def test_import_one_valid_two_invalid(client):
    csv = "\n".join([
        HEADER,
        "AA-1,Good Site,solar_farm,42.3,-7.2,600,1000000,high,3,200,4",       # valid (row 1)
        "AA-2,Bad Type,not_a_type,42.3,-7.2,600,1000000,high,3,200,4",          # row 2 invalid
        "AA-3,Bad Fuel,solar_farm,42.3,-7.2,600,1000000,plasma,3,200,4",        # row 3 invalid
    ]) + "\n"
    files = {"file": ("assets.csv", csv.encode(), "text/csv")}
    r = client.post("/api/assets/import", files=files, headers=auth(client))
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["accepted"] == 1
    assert [row["row"] for row in report["rejected"]] == [2, 3]
    # portfolio replaced with the single valid site
    sites = client.get("/api/sites", headers=auth(client)).json()
    assert [s["site_id"] for s in sites] == ["AA-1"]


def test_geojson_import(client):
    fc = {"type": "FeatureCollection", "features": [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-7.2, 42.3]},
        "properties": {"site_id": "GJ-1", "name": "Geo Site", "type": "substation",
                       "radius_m": 150, "value_eur": 500000, "fuel_class": "low",
                       "personnel_on_site": 2, "primary_access_bearing_deg": 90,
                       "criticality": 5},
    }]}
    files = {"file": ("assets.geojson", json.dumps(fc).encode(), "application/json")}
    r = client.post("/api/assets/import", files=files, headers=auth(client))
    assert r.status_code == 200
    assert r.json()["accepted"] == 1


def test_wrong_file_type_422(client):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    r = client.post("/api/assets/import", files=files, headers=auth(client))
    assert r.status_code == 422
