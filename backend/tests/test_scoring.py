"""test_scoring.py — rules-1.0 scoring (TEAM_PLAN.md §5.12 T1-M3)."""
from app.geo import destination
from app.importer import build_components, seed_sites
from app.models import Detection
from app.providers.weather import WeatherReading
from app.scoring import _level_for, score_site


def _site(**over):
    s = {s.site_id: s for s in seed_sites()}["ES-OU-001"]
    return s.model_copy(update=over)


def _det(lat, lon):
    return Detection(id="d1", source="synthetic_fallback", external_id=None, lat=lat, lon=lon,
                     observed_at="2025-08-14T13:00:00Z", received_at="2025-08-14T13:00:00Z",
                     satellite="N20", confidence="h", intensity_frp=10.0)


def test_level_edges():
    assert _level_for(25) == "NORMAL"
    assert _level_for(26) == "ELEVATED"
    assert _level_for(50) == "ELEVATED"
    assert _level_for(51) == "HIGH"
    assert _level_for(75) == "HIGH"
    assert _level_for(76) == "CRITICAL"


def test_no_detections_score_at_most_40():
    site = _site()
    w = WeatherReading(temp_c=34, rh_pct=18, speed_kmh=26, from_deg=225, status="observed")
    status, headline = score_site(site, w, [])
    assert status.score <= 40
    assert headline == "No fire within 25 km"


def test_edge_detection_wind_straight_at_site():
    site = _site(lat=42.0, lon=-7.0, radius_m=1000)
    dlat, dlon = destination(42.0, -7.0, 0, 1.0)  # 1 km north = at the edge
    det = _det(dlat, dlon)
    # wind blowing from the north (from_deg=0) carries fire straight at the site
    w = WeatherReading(temp_c=30, rh_pct=20, speed_kmh=30, from_deg=0, status="observed")
    status, _ = score_site(site, w, [det])
    assert status.factors.proximity == 35.0
    assert status.factors.wind_alignment == 25.0


def test_weather_unknown_nulls_and_headline():
    site = _site(lat=42.0, lon=-7.0, radius_m=1000)
    dlat, dlon = destination(42.0, -7.0, 0, 1.0)
    status, headline = score_site(site, None, [_det(dlat, dlon)])
    assert status.factors.weather is None
    assert status.factors.wind_alignment is None
    assert status.factor_status.weather == "unknown"
    assert status.factor_status.wind_alignment == "unknown"
    assert status.fire_moving_toward_site is None
    assert headline.endswith("wind unknown")


def test_components_sum_to_value():
    for stype in ("solar_farm", "wind_farm", "substation", "forest_block",
                  "telecom_tower", "test_plot"):
        comps = build_components(1234567, stype)
        assert sum(c.value_eur for c in comps) == 1234567
