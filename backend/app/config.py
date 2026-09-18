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
