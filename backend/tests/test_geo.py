"""test_geo.py — geometry (TEAM_PLAN.md §5.12 T1-M3)."""
from app.geo import angdiff, bearing_deg, compass


def test_bearing_north_and_east():
    assert abs(bearing_deg(42, -7, 43, -7) - 0) <= 1 or abs(bearing_deg(42, -7, 43, -7) - 360) <= 1
    assert abs(bearing_deg(42, -7, 42, -6) - 90) <= 1


def test_angdiff():
    assert angdiff(350, 10) == 20


def test_compass():
    assert compass(225) == "SW"
    assert compass(350) == "N"
