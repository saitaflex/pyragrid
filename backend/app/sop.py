"""sop.py — SOP rule matching (TEAM_PLAN.md §5.6). Rules choose actions, not the score."""
from __future__ import annotations

from typing import Optional

from app.models import SopRule

RANK = {"NORMAL": 0, "ELEVATED": 1, "HIGH": 2, "CRITICAL": 3}


def _matches(rule: SopRule, level: str, site_type: str, criticality: int,
             fire_moving_toward_site: Optional[bool]) -> bool:
    if not rule.enabled:
        return False
    c = rule.conditions
    if RANK[level] < RANK[c.min_level]:
        return False
    if c.asset_types and site_type not in c.asset_types:
        return False
    if criticality < c.min_criticality:
        return False
    if c.wind_toward_site is not None:
        # a null fire_moving_toward_site never matches a non-null condition
        if fire_moving_toward_site is None or fire_moving_toward_site != c.wind_toward_site:
            return False
    return True


def match_actions(rules: list[SopRule], level: str, site_type: str, criticality: int,
                  fire_moving_toward_site: Optional[bool]) -> tuple[list[str], list[str]]:
    matched = [r for r in rules
               if _matches(r, level, site_type, criticality, fire_moving_toward_site)]
    matched.sort(key=lambda r: (r.priority, r.rule_id))
    actions: list[str] = []
    for r in matched:
        for a in r.actions:
            if a not in actions:
                actions.append(a)
    return actions, [r.rule_id for r in matched]
