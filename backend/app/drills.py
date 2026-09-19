"""drills.py — training drills ("white attempts") on a real site with simulated signals.

An admin starts a drill: the system scripts a case study (satellite hotspots and ground
sensor readings that reveal themselves over real time), alerts every participant, and
scores each employee on how fast they acknowledged and which protocol actions they chose.
Nothing in a drill touches the real alerts, incidents or sensor data.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from app import config
from app.geo import angdiff, compass, destination
from app.models import (
    DrillNotification, DrillResponse, DrillStage, DrillView, SensorNode, Site,
)
from app.sensors import fire_estimate, layout
from app.sop import match_actions

AUTO_END_S = 30 * 60          # a drill closes itself 30 min after the last signal
ACK_FULL_S, ACK_ZERO_S = 30, 300
RESP_FULL_S, RESP_ZERO_S = 120, 900

SCENARIOS = {
    "approaching": ("Wildfire approaching from upwind",
                    "Satellites pick up a fire upwind of {site}. Follow the signals as they "
                    "arrive and choose the protocol actions you would take."),
    "sensor_first": ("Ground sensors detect fire before satellites",
                     "It is night and cloudy: no satellite pass yet. The ground sensor mesh "
                     "at {site} starts reporting heat. Decide what to do."),
    "false_alarm": ("Sensor anomaly (possible false alarm)",
                    "One ground sensor at {site} reports unusual heat, then a tilt alarm. "
                    "Decide on a proportionate response."),
}

DISTRACTORS = [
    "Send employees to fight the fire with extinguishers",
    "Wait for the next satellite pass before doing anything",
    "Continue normal operations",
    "Post an update on social media",
    "Move personnel to the safest available exit route",
    "Dispatch site team to inspect the sensor",
    "Notify emergency services according to company procedure",
]
FALSE_ALARM_EXPECTED = [
    "Dispatch site team to inspect the sensor",
    "Contact site manager and confirm personnel count",
    "Increase monitoring to every satellite pass",
]
DISCLAIMER = ("TRAINING DRILL: simulated signals on a real site. Not a real fire. "
              "Drill data never enters real alerts, incidents or sensor history.")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _secs(a: str, b: str) -> int:
    fa = datetime.strptime(a, "%Y-%m-%dT%H:%M:%SZ")
    fb = datetime.strptime(b, "%Y-%m-%dT%H:%M:%SZ")
    return int((fb - fa).total_seconds())


def _pick(nodes: list[dict], bearing: float, ring: int, avoid: tuple = ()) -> dict:
    """Sensor in `ring` (0 fence, 1 inner buffer, 2 outer buffer) closest to `bearing`,
    preferring sensors on real places over open-ground filler points."""
    cand = [n for n in nodes if n["ring"] == ring and n["sensor_id"] not in avoid] \
        or [n for n in nodes if n["sensor_id"] not in avoid]
    return min(cand, key=lambda n: angdiff(n["bearing"], bearing) + (20 if n["kind"] == "grid" else 0))


def _where(n: dict) -> str:
    """'at the forest edge', 'at a house', 'on the site fence (SW)', 'on open ground'."""
    place = n["place"]
    if n["kind"] == "fence":
        return "on the " + place[0].lower() + place[1:]
    if n["kind"] == "grid":
        return "on open ground"
    if n["kind"] == "vegetation":
        return "at the " + place.lower()
    return "at a " + place.lower() + (f" ({n['name']})" if n.get("name") else "")


def build_script(site: Site, scenario: str, pace_s: int, has_mesh: bool,
                 wind_from_deg: int) -> list[DrillStage]:
    """The case study: signals revealed at offset_s = k * pace_s."""
    _, _, nodes = layout(site)
    up = wind_from_deg                           # fire starts where the wind comes from
    side = compass(up)
    stages: list[DrillStage] = []

    def add(kind, title, detail, level, lat=None, lon=None, node=None, temp=None):
        stages.append(DrillStage(
            offset_s=len(stages) * pace_s, kind=kind, title=title, detail=detail, level=level,
            lat=node["lat"] if node else lat, lon=node["lon"] if node else lon,
            sensor_id=node["sensor_id"] if node else None, temp_c=temp))

    if scenario == "approaching":
        la, lo = destination(site.lat, site.lon, up, 6.0)
        add("satellite", f"Satellite hotspot 6.0 km {side}",
            "VIIRS detection, FRP 38 MW, confidence high. Wind blowing toward the site.",
            "ELEVATED", la, lo)
        la, lo = destination(site.lat, site.lon, up, 3.2)
        add("satellite", f"New hotspot 3.2 km {side}: fire is moving toward the site",
            "Second pass: FRP 71 MW. Spread direction matches the wind.", "HIGH", la, lo)
        if has_mesh:
            n3 = _pick(nodes, up, 2)
            n2 = _pick(nodes, up, 1, avoid=(n3["sensor_id"],))
            add("sensor_warm", f"Sensor {n3['label']} {_where(n3)} ({side}) warming: 52°C",
                "Ambient is 29°C. Heat is reaching the sensor buffer zone.", "HIGH",
                node=n3, temp=52.0)
            add("sensor_fire", f"Sensor {n3['label']} reports FIRE: 84°C",
                "Ground confirmation of the satellite detections, about "
                f"{n3['dist_m']} m from the site centre.", "CRITICAL", node=n3, temp=84.0)
            add("sensor_offline", f"Sensor {n3['label']} offline",
                "Stopped reporting right after the fire reading: likely destroyed.",
                "CRITICAL", node=n3)
            add("sensor_fire", f"Sensor {n2['label']} {_where(n2)}, closer in, reports FIRE: 96°C",
                "The fire front is getting closer to the site.", "CRITICAL",
                node=n2, temp=96.0)
        else:
            la, lo = destination(site.lat, site.lon, up, 1.1)
            add("satellite", f"Hotspot 1.1 km {side}", "FRP 112 MW. Fire is close to the "
                "site boundary.", "CRITICAL", la, lo)
    elif scenario == "sensor_first":
        n2 = _pick(nodes, up, 1)
        n1 = _pick(nodes, up, 0, avoid=(n2["sensor_id"],))
        add("sensor_warm", f"Sensor {n2['label']} {_where(n2)} warming: 49°C at 02:10",
            "Night-time ambient is 18°C. No satellite pass for the next 3 hours.",
            "ELEVATED", node=n2, temp=49.0)
        add("sensor_fire", f"Sensor {n2['label']} reports FIRE: 77°C",
            "No satellite confirmation possible (night, cloud cover).", "HIGH",
            node=n2, temp=77.0)
        add("sensor_fire", f"Sensor {n1['label']} {_where(n1)} reports FIRE: 91°C",
            "Two neighbouring sensors in fire: the fire is spreading toward the site.",
            "CRITICAL", node=n1, temp=91.0)
        add("sensor_offline", f"Sensor {n2['label']} offline",
            "Destroyed by fire. The sensors are the only source of information right now.",
            "CRITICAL", node=n2)
    else:  # false_alarm
        n1 = _pick(nodes, (up + 90) % 360, 1)
        add("sensor_warm", f"Sensor {n1['label']} {_where(n1)} warming: 48°C",
            "Neighbouring sensors normal (27–29°C).", "ELEVATED", node=n1, temp=48.0)
        add("sensor_dropped", f"Sensor {n1['label']} tilt alarm",
            "Node moved or knocked over (maintenance vehicle? animal?).", "ELEVATED", node=n1)
        add("satellite_clear", "Satellite pass: no hotspot within 10 km",
            "Latest VIIRS pass shows no fire near the site.", "ELEVATED",
            site.lat, site.lon)
        add("sensor_normal", f"Sensor {n1['label']} back to 30°C",
            "Reading returned to ambient after the tilt.", "NORMAL", node=n1, temp=30.0)
    return stages


def expected_actions(site: Site, scenario: str, rules: list) -> list[str]:
    if scenario == "false_alarm":
        return list(FALSE_ALARM_EXPECTED)
    actions, _ = match_actions(rules, "CRITICAL", site.type, site.criticality, True)
    return list(dict.fromkeys(actions))


def options_for(drill_id: str, expected: list[str]) -> list[str]:
    opts = list(dict.fromkeys(expected + [d for d in DISTRACTORS if d not in expected]))
    return sorted(opts, key=lambda o: hashlib.sha256((drill_id + o).encode()).hexdigest())


def score_response(resp: dict, created_at: str, expected: list[str]) -> DrillResponse:
    ack_s = _secs(created_at, resp["acked_at"]) if resp.get("acked_at") else None
    resp_s = _secs(created_at, resp["responded_at"]) if resp.get("responded_at") else None
    chosen = set(resp.get("actions", []))
    correct = len(chosen & set(expected))
    wrong = len(chosen - set(expected))
    missed = len(set(expected) - chosen)
    score = None
    if resp_s is not None:
        def lin(v, full, zero):
            return 1.0 if v <= full else max(0.0, (zero - v) / (zero - full))
        ack_pts = 30 * lin(ack_s if ack_s is not None else resp_s, ACK_FULL_S, ACK_ZERO_S)
        acc_pts = max(0.0, 50 * correct / max(1, len(expected)) - 10 * wrong)
        speed_pts = 20 * lin(resp_s, RESP_FULL_S, RESP_ZERO_S)
        score = round(ack_pts + acc_pts + speed_pts)
    return DrillResponse(email=resp["email"], name=resp.get("name", resp["email"]),
                         acked_at=resp.get("acked_at"), responded_at=resp.get("responded_at"),
                         actions=resp.get("actions", []), note=resp.get("note", ""),
                         ack_seconds=ack_s, respond_seconds=resp_s, correct=correct,
                         wrong=wrong, missed=missed, score=score)


def drill_nodes(site: Site, has_mesh: bool, revealed: list[DrillStage]) -> list[SensorNode]:
    """The site's mesh with the drill's sensor signals applied (all others normal)."""
    if not has_mesh:
        return []
    _, _, geo = layout(site)
    kind_state = {"sensor_warm": "warm", "sensor_fire": "fire", "sensor_offline": "offline",
                  "sensor_dropped": "dropped", "sensor_normal": "ok"}
    state: dict[str, tuple[str, float | None]] = {}
    for st in revealed:
        if st.sensor_id and st.kind in kind_state:
            prev_t = state.get(st.sensor_id, ("ok", 28.0))[1]
            s = kind_state[st.kind]
            state[st.sensor_id] = (s, None if s == "offline" else
                                   (st.temp_c if st.temp_c is not None else prev_t))
    out = []
    for n in geo:
        s, t = state.get(n["sensor_id"], ("ok", 28.0))
        note = {"ok": "Normal", "warm": "Above ambient", "fire": "Fire temperature",
                "offline": "No longer reporting", "dropped": "Tilt alarm"}[s]
        out.append(SensorNode(sensor_id=n["sensor_id"], site_id=site.site_id, label=n["label"],
                              ring=n["ring"], lat=n["lat"], lon=n["lon"], kind=n["kind"],
                              place=n["place"], name=n["name"], dist_m=n["dist_m"],
                              bearing_deg=int(n["bearing"]),
                              state=s, temp_c=t, battery_pct=90, last_seen=None,
                              state_since=None, note=f"DRILL: {note}"))
    return out


def view(d: dict, responses: dict[str, dict], viewer_email: str, viewer_is_admin: bool,
         now: str) -> DrillView:
    stages = [DrillStage(**s) for s in d["stages"]]
    site = Site(**d["site"])
    elapsed = max(0, _secs(d["created_at"], now))
    ended = d.get("ended_at") or (
        now if elapsed > stages[-1].offset_s + AUTO_END_S else None)
    status = "ended" if ended else "running"
    revealed = stages if ended else [s for s in stages if s.offset_s <= elapsed]
    upcoming = [s for s in stages if s.offset_s > elapsed]
    scored = {e: score_response(r, d["created_at"], d["expected"]) for e, r in responses.items()}
    mine = scored.get(viewer_email)
    nodes = drill_nodes(site, d["has_mesh"], revealed)
    show_expected = viewer_is_admin or status == "ended" or (mine and mine.responded_at)
    visible = list(scored.values()) if viewer_is_admin else ([mine] if mine else [])
    visible.sort(key=lambda r: (-(r.score if r.score is not None else -1), r.email))
    notifications = [] if not viewer_is_admin else [
        DrillNotification(to=p, channel=ch, subject=f"[DRILL] {d['site_name']}: {d['title']}")
        for p in d["participants"] for ch in ("in_app", "email")]
    return DrillView(
        drill_id=d["drill_id"], site_id=d["site_id"], site_name=d["site_name"],
        lat=d["lat"], lon=d["lon"], radius_m=d["radius_m"], scenario=d["scenario"],
        scenario_title=d["title"], briefing=d["briefing"], pace_s=d["pace_s"], status=status,
        created_by=d["created_by"], created_at=d["created_at"], ended_at=d.get("ended_at"),
        elapsed_s=elapsed, level=revealed[-1].level if revealed else "NORMAL",
        stages=revealed, total_stages=len(stages),
        next_stage_in_s=(upcoming[0].offset_s - elapsed) if upcoming and not ended else None,
        participants=d["participants"], participant_names=d.get("names", {}),
        options=d["options"],
        expected_actions=d["expected"] if show_expected else None,
        my_response=mine, responses=visible, notifications=notifications,
        nodes=nodes, fire_estimate=fire_estimate(site, nodes) if nodes else None,
        disclaimer=DISCLAIMER)


def new_drill(drill_id: str, site: Site, scenario: str, pace_s: int, has_mesh: bool,
              participants: list[str], names: dict[str, str], rules: list,
              created_by: str) -> dict:
    wind_from = int(config.ASSUMED_WEATHER["from_deg"])
    stages = build_script(site, scenario, pace_s, has_mesh, wind_from)
    expected = expected_actions(site, scenario, rules)
    title, briefing = SCENARIOS[scenario]
    return {
        "drill_id": drill_id, "site_id": site.site_id, "site_name": site.name,
        "lat": site.lat, "lon": site.lon, "radius_m": site.radius_m,
        "site": json.loads(site.model_dump_json()), "has_mesh": has_mesh,
        "scenario": scenario, "title": title, "briefing": briefing.format(site=site.name),
        "pace_s": pace_s, "created_by": created_by, "created_at": now_iso(), "ended_at": None,
        "participants": participants, "names": {p: names.get(p, p) for p in participants},
        "stages": [s.model_dump() for s in stages],
        "expected": expected, "options": options_for(drill_id, expected),
    }
