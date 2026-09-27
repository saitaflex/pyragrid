"""test_spread.py — the fire spread forecast: published benchmarks, monotonicity, geometry.

The first test is the important one: it pins every fuel model to the rate of spread Anderson
(1982) publishes for it. If someone edits a coefficient or a fuel load, this fails.
"""
from dataclasses import replace

import pytest

from app import spread
from app.importer import build_components
from app.models import Site

MIDFLAME_5MPH_KMH = 5 * 1.60934


def _site(fuel="high", radius=1000, lat=36.5, lon=9.0):
    return Site(site_id="T-1", name="Test", type="forest_block", lat=lat, lon=lon,
                radius_m=radius, value_eur=1_000_000, fuel_class=fuel,
                personnel_on_site=2, primary_access_bearing_deg=90, criticality=3,
                components=build_components(1_000_000, "forest_block"))


class _Det:
    def __init__(self, lat, lon):
        self.lat, self.lon = lat, lon
        self.confidence = "h"
        self.observed_at = "2025-08-24T15:00:00Z"


class _W:
    def __init__(self, speed=20.0, from_deg=225, temp=32.0, rh=22.0):
        self.speed_kmh, self.from_deg, self.temp_c, self.rh_pct = speed, from_deg, temp, rh
        self.status = "assumed"


@pytest.mark.parametrize("key", list(spread.FUELS))
def test_matches_published_rate_of_spread(key):
    """Anderson (1982) Table 1: 5 mph midflame wind, 8% dead fine moisture, no slope."""
    fuel = spread.FUELS[key]
    ros, terms = spread.rothermel_ros(replace(fuel, waf=1.0), 0.08, MIDFLAME_5MPH_KMH, 0.0)
    got = terms["ros_chains_per_hour"]
    assert got == pytest.approx(fuel.benchmark_chains_h, rel=0.10), (
        f"{fuel.anderson} drifted from its published {fuel.benchmark_chains_h} chains/h")


def test_moisture_from_rh_and_temp():
    """Hot dry air dries fine fuel; humid air does not. Simard (1968)."""
    dry = spread.fine_fuel_moisture(35.0, 15.0)
    humid = spread.fine_fuel_moisture(15.0, 85.0)
    assert dry < humid
    assert 0.02 <= dry <= 0.10
    assert humid > 0.15


def test_wind_and_slope_increase_spread():
    fuel = spread.FUELS["medium"]
    m = spread.fine_fuel_moisture(32.0, 22.0)
    calm, windy = spread.rothermel_ros(fuel, m, 0.0, 0.0)[0], spread.rothermel_ros(fuel, m, 30.0, 0.0)[0]
    flat, steep = spread.rothermel_ros(fuel, m, 10.0, 0.0)[0], spread.rothermel_ros(fuel, m, 10.0, 60.0)[0]
    assert windy > calm * 2
    assert steep > flat


def test_wet_fuel_stops_spreading():
    """Above the moisture of extinction the bed will not carry a fire."""
    ros, _ = spread.rothermel_ros(spread.FUELS["low"], 0.35, 20.0, 0.0)
    assert ros == 0.0


def test_elliptical_spread_is_fastest_downwind():
    head = 1000.0
    downwind = spread.ros_at_bearing(head, 90, 90, 25.0)
    flank = spread.ros_at_bearing(head, 90, 0, 25.0)
    backing = spread.ros_at_bearing(head, 90, 270, 25.0)
    assert downwind == pytest.approx(head)
    assert backing < flank < downwind
    assert spread.length_breadth(40.0) > spread.length_breadth(5.0)


def test_forecast_arrival_is_sooner_when_wind_points_at_the_site():
    """Same fire, same distance: wind toward the site must shorten the arrival time."""
    site = _site(fuel="medium", radius=500)
    det = _Det(site.lat - 0.05, site.lon)          # fire due south of the site
    toward = spread.forecast_site(site, _W(from_deg=180), [det], "2025-08-24T15:00:00Z")
    away = spread.forecast_site(site, _W(from_deg=0), [det], "2025-08-24T15:00:00Z")
    assert toward.bearing_from_fire == pytest.approx(0, abs=2)
    assert toward.ros_toward_site_m_h > away.ros_toward_site_m_h
    # a backing fire may never arrive at all, which is the correct answer rather than a number
    assert away.hours_to_arrival is None or toward.hours_to_arrival < away.hours_to_arrival


def test_forecast_reports_no_arrival_when_the_fire_cannot_reach():
    site = _site(fuel="high", radius=200)
    far = _Det(site.lat - 0.20, site.lon)          # ~22 km away, backing fire
    f = spread.forecast_site(site, _W(from_deg=0, speed=5.0), [far], "2025-08-24T15:00:00Z")
    assert f.hours_to_arrival is None
    assert "no arrival" in f.arrival_confidence


def test_forecast_without_detections_is_none():
    assert spread.forecast_site(_site(), _W(), [], "2025-08-24T15:00:00Z") is None


def test_forecast_states_its_assumptions():
    """The forecast must never present itself as calibrated truth."""
    site = _site()
    f = spread.forecast_site(site, _W(), [_Det(site.lat - 0.03, site.lon)],
                             "2025-08-24T15:00:00Z")
    joined = " ".join(f.assumptions).lower()
    for must_say in ["detections, not perimeters", "no terrain layer", "wind held constant",
                     "no crown fire", "no calibration against"]:
        assert must_say in joined
    assert f.front_positions[0]["hours_ahead"] == 1
