"""test_sop.py — SOP matching (TEAM_PLAN.md §5.12 T1-M3)."""
from app.defaults import default_rules
from app.sop import match_actions


def test_critical_substation_wind_toward_site_order():
    rules = default_rules()
    actions, rule_ids = match_actions(rules, "CRITICAL", "substation", 5,
                                      fire_moving_toward_site=True)
    assert rule_ids == ["R-001", "R-002", "R-003", "R-004"]
    # duplicates removed, first occurrence kept
    assert len(actions) == len(set(actions))
    assert actions[-1] == "Escalate to emergency protocol"


def test_disabled_rule_never_matches():
    rules = default_rules()
    rules[0].enabled = False  # R-001
    _, rule_ids = match_actions(rules, "CRITICAL", "substation", 5, True)
    assert "R-001" not in rule_ids


def test_elevated_matches_nothing():
    actions, rule_ids = match_actions(default_rules(), "ELEVATED", "solar_farm", 4, None)
    assert actions == []
    assert rule_ids == []


def test_null_fire_moving_never_matches_wind_condition():
    # R-004 requires wind_toward_site=True; a null fire_moving must not match it
    _, rule_ids = match_actions(default_rules(), "CRITICAL", "solar_farm", 4,
                                fire_moving_toward_site=None)
    assert "R-004" not in rule_ids
