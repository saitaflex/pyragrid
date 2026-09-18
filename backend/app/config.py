"""config.py — constants (TEAM_PLAN.md §5.2)."""

CONTRACT_VERSION = "2.1.0"
MODEL_VERSION = "rules-1.0"
REPLAY_START = "2025-08-08T00:00:00Z"
REPLAY_END = "2025-08-26T00:00:00Z"   # exclusive
STEP_HOURS = 3
DETECTION_WINDOW_HOURS = 12
FIRE_RADIUS_KM = 25.0
CONTACT_KM = 1.0
ROUTE_EXPOSURE_KM = 10.0
BBOX = {"west": -7.9, "south": 41.8, "east": -6.7, "north": 42.6}
EARTH_RADIUS_KM = 6371.0088
LEVELS = [(25, "NORMAL"), (50, "ELEVATED"), (75, "HIGH"), (100, "CRITICAL")]
MAX_IMPORT_ROWS = 200    # keeps replay recompute well under Vercel limits (§5.9)
TOKEN_HOURS = 12
ASSUMED_WEATHER = {"temp_c": 32.0, "rh_pct": 22.0, "speed_kmh": 20.0, "from_deg": 225}
NOTIFY_TO = {"demo": "control-room@demo.eu", "othercorp": "ops@othercorp.eu"}
LLM_TIMEOUT_S = 15
MAX_SUGGESTIONS = 6

# Asset-derived values (§5.3)
COMPONENT_SHARES = {
    "solar_farm": [("PV array", 0.70), ("Inverter station", 0.15),
                   ("Substation", 0.10), ("Control building", 0.05)],
    "wind_farm": [("Turbines", 0.80), ("Substation", 0.15), ("Control building", 0.05)],
    "substation": [("Transformers", 0.60), ("Switchgear", 0.30), ("Control building", 0.10)],
    "forest_block": [("Standing timber", 0.90), ("Forest roads", 0.10)],
    "telecom_tower": [("Tower and antennas", 0.70), ("Power and backup", 0.30)],
    "test_plot": [("Weather station", 0.60), ("Camera", 0.40)],
}
VULNERABILITY = {"solar_farm": 0.8, "wind_farm": 0.6, "substation": 0.9,
                 "forest_block": 1.0, "telecom_tower": 0.7, "test_plot": 0.5}
FUEL_FACTOR = {"low": 0.2, "medium": 0.5, "high": 0.8, "very_high": 1.0}

SITE_TYPES = list(COMPONENT_SHARES.keys())
FUEL_CLASSES = list(FUEL_FACTOR.keys())

DISCLAIMER_INCIDENT = ("Recommended actions from the customer's approved protocol "
                       "(simulated for demo). Not an autonomous safety decision.")
DISCLAIMER_ADVISOR = ("AI-generated suggestions for the company's own operations, grounded "
                      "in the data shown. Not firefighting instructions. A human must approve "
                      "every suggestion. Always follow the fire service's orders.")
DISCLAIMER_HANDOFF = ("Information for the fire service from the site operator (simulated demo "
                      "data). The fire service decides all firefighting actions.")
