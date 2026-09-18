"""defaults.py — seed users, SOP rules and the othercorp site (TEAM_PLAN.md §2.2, §2.7, §5.3)."""
from __future__ import annotations

from app.importer import build_components
from app.models import Site, SopConditions, SopRule

# (email, name, customer_id, role, password)
DEMO_USERS = [
    ("admin@demo.eu", "Demo Admin", "demo", "admin", "demo1234"),
    ("operator@demo.eu", "Demo Operator", "demo", "operator", "demo1234"),
    ("other@othercorp.eu", "Other Admin", "othercorp", "admin", "demo1234"),
]


def default_rules() -> list[SopRule]:
    return [
        SopRule(rule_id="R-001", name="High exposure: Level 2", enabled=True, priority=10,
                conditions=SopConditions(min_level="HIGH", asset_types=[], min_criticality=1,
                                         wind_toward_site=None),
                actions=["Notify regional control centre",
                         "Contact site manager and confirm personnel count",
                         "Verify secondary access route is available",
                         "Increase monitoring to every satellite pass"]),
        SopRule(rule_id="R-002", name="Critical exposure: Level 3", enabled=True, priority=20,
                conditions=SopConditions(min_level="CRITICAL", asset_types=[], min_criticality=1,
                                         wind_toward_site=None),
                actions=["Notify regional control centre immediately",
                         "Contact site manager and confirm personnel location",
                         "Move personnel to the safest available exit route",
                         "Prepare controlled shutdown if authorised",
                         "Notify emergency services according to company procedure"]),
        SopRule(rule_id="R-003", name="Substation control room", enabled=True, priority=30,
                conditions=SopConditions(min_level="HIGH", asset_types=["substation"],
                                         min_criticality=1, wind_toward_site=None),
                actions=["Notify control room of substation exposure"]),
        SopRule(rule_id="R-004", name="Critical with wind toward site", enabled=True, priority=40,
                conditions=SopConditions(min_level="CRITICAL", asset_types=[], min_criticality=1,
                                         wind_toward_site=True),
                actions=["Escalate to emergency protocol"]),
    ]


def othercorp_site() -> Site:
    return Site(
        site_id="OC-001", name="Other Corp Depot", type="substation",
        lat=42.340, lon=-7.864, radius_m=100, value_eur=2000000, fuel_class="low",
        personnel_on_site=1, primary_access_bearing_deg=0, criticality=3,
        components=build_components(2000000, "substation"),
    )
