"""test_alerts.py — alert transitions + synthetic replay (TEAM_PLAN.md §5.12 T1-M3)."""
from types import SimpleNamespace

from app.defaults import default_rules
from app.importer import seed_sites
from app.models import Factors, FactorStatuses
from app.replay import ReplayData, build_alerts, build_summary

_F = Factors(proximity=0.0, wind_alignment=0.0, weather=0.0, fuel=0.0, vulnerability=0.0)
_FS = FactorStatuses(proximity="observed", wind_alignment="observed", weather="observed",
                     fuel="customer_provided", vulnerability="customer_provided")


def _status(level, score):
    return SimpleNamespace(level=level, score=score, fire_moving_toward_site=None,
                           triggering_detection_id=None, factors=_F, factor_status=_FS)


def test_transition_sequence_four_alerts():
    levels = ["NORMAL", "ELEVATED", "HIGH", "CRITICAL", "HIGH", "ELEVATED"]
    site = SimpleNamespace(name="S", type="solar_farm", criticality=4)
    rd = SimpleNamespace(
        sites={"S": site},
        steps=[f"2025-08-14T{h:02d}:00:00Z" for h in range(0, 18, 3)][:len(levels)],
        statuses={"S": [_status(lv, 50) for lv in levels]},
        headlines={"S": ["h"] * len(levels)},
        processed_at="2026-09-18T00:00:00Z",
    )
    alerts = build_alerts(rd, [], {})
    assert len(alerts) == 4
    kinds = [(a.from_level, a.to_level, a.kind) for a in alerts]
    assert ("ELEVATED", "HIGH", "escalation") in kinds
    assert ("HIGH", "CRITICAL", "escalation") in kinds
    assert ("CRITICAL", "HIGH", "de-escalation") in kinds
    assert ("HIGH", "ELEVATED", "de-escalation") in kinds


def test_synthetic_replay_reaches_critical():
    rd = ReplayData("demo", seed_sites())
    assert rd.total_detections > 0
    all_status = [st for seq in rd.statuses.values() for st in seq]
    assert any(st.level == "CRITICAL" for st in all_status)
    summary = build_summary(rd)
    assert summary.sites_ever_critical >= 1
    assert summary.sites_ever_high >= summary.sites_ever_critical
    assert summary.missed_exposures >= 0
    assert 0.0 <= summary.explanation_coverage_pct <= 100.0
    alerts = build_alerts(rd, default_rules(), {})
    assert sum(1 for a in alerts if a.kind == "escalation") == summary.alerts_raised
