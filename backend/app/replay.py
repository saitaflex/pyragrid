"""replay.py — grid precompute, alerts, incidents, summary, outbox (TEAM_PLAN.md §5.7, §5.9).

Statuses are precomputed per customer and cached in memory. Alerts/incidents/outbox are
built on demand so they reflect the CURRENT SOP rules and acknowledgements.
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timedelta, timezone

from app import config
from app.models import (
    Alert, Incident, OutboxEmail, ReplaySummary, Site, SiteStatus, TimelinePoint,
)
from app.providers.notification import OutboxProvider
from app.providers.weather import WeatherService
from app.providers.wildfire import FileDetectionsProvider
from app.scoring import score_site
from app.sop import RANK, match_actions

Z = "%Y-%m-%dT%H:%M:%SZ"


def parse(s: str) -> datetime:
    return datetime.strptime(s, Z).replace(tzinfo=timezone.utc)


def fmt(dt: datetime) -> str:
    return dt.strftime(Z)


def compact(at: str) -> str:
    return parse(at).strftime("%Y%m%dT%H%M")


def grid_steps() -> list[str]:
    start, end = parse(config.REPLAY_START), parse(config.REPLAY_END)
    out, t = [], start
    while t < end:
        out.append(fmt(t))
        t += timedelta(hours=config.STEP_HOURS)
    return out


def snap(at: str | None) -> str:
    """Clamp into range and snap DOWN to the 3h grid; return the snapped step."""
    steps = grid_steps()
    if at is None:
        return steps[-1]
    try:
        dt = parse(at)
    except ValueError:
        return steps[-1]
    lo, hi = parse(steps[0]), parse(steps[-1])
    if dt <= lo:
        return steps[0]
    if dt >= hi:
        return steps[-1]
    # snap down to the grid
    delta_h = (dt - lo).total_seconds() / 3600.0
    k = int(delta_h // config.STEP_HOURS)
    return steps[k]


class ReplayData:
    """Precomputed per-customer statuses over all 144 steps."""

    def __init__(self, customer_id: str, sites: list[Site]) -> None:
        self.customer_id = customer_id
        self.sites = {s.site_id: s for s in sites}
        self.steps = grid_steps()
        self.processed_at = fmt(datetime.now(timezone.utc))
        self.statuses: dict[str, list[SiteStatus]] = {sid: [] for sid in self.sites}
        self.headlines: dict[str, list[str]] = {sid: [] for sid in self.sites}
        self.total_detections = 0
        self.detections_used = 0
        self._compute()

    def _compute(self) -> None:
        dets = FileDetectionsProvider().detections()
        in_range = [d for d in dets
                    if config.REPLAY_START <= d.observed_at < config.REPLAY_END]
        self.total_detections = len(in_range)
        used = [d for d in in_range if d.confidence in ("n", "h")]
        self.detections_used = len(used)
        used.sort(key=lambda d: d.observed_at)
        weather = WeatherService()

        for at in self.steps:
            win_start = fmt(parse(at) - timedelta(hours=config.DETECTION_WINDOW_HOURS))
            window = [d for d in used if win_start < d.observed_at <= at]
            for sid, site in self.sites.items():
                margin_km = config.FIRE_RADIUS_KM + site.radius_m / 1000.0
                dlat = margin_km / 111.0
                dlon = margin_km / (111.0 * max(0.01, math.cos(math.radians(site.lat))))
                near = [d for d in window
                        if abs(d.lat - site.lat) <= dlat and abs(d.lon - site.lon) <= dlon]
                status, headline = score_site(site, weather.get(sid, at), near)
                self.statuses[sid].append(status)
                self.headlines[sid].append(headline)

    def index_of(self, at: str) -> int:
        return self.steps.index(at)

    def status_at(self, site_id: str, at: str) -> SiteStatus:
        return self.statuses[site_id][self.index_of(at)]

    def headline_at(self, site_id: str, at: str) -> str:
        return self.headlines[site_id][self.index_of(at)]

    def timeline(self, site_id: str) -> list[TimelinePoint]:
        return [
            TimelinePoint(at=at, score=st.score, level=st.level,
                          nearest_fire_km=st.nearest_fire_km)
            for at, st in zip(self.steps, self.statuses[site_id])
        ]


# --------------------------------------------------------------------- alerts

def build_alerts(rd: ReplayData, rules: list, acks: dict) -> list[Alert]:
    """All level-transition alerts. acks: {alert_id: (acked_by, acked_at)}."""
    alerts: list[Alert] = []
    for sid, site in rd.sites.items():
        prev = "NORMAL"
        for at, st, hl in zip(rd.steps, rd.statuses[sid], rd.headlines[sid]):
            level = st.level
            if level != prev and (RANK[level] >= 2 or RANK[prev] >= 2):
                kind = "escalation" if RANK[level] > RANK[prev] else "de-escalation"
                actions, rule_ids = match_actions(
                    rules, level, site.type, site.criticality, st.fire_moving_toward_site)
                aid = f"{sid}_{compact(at)}_{level}"
                acked_by, acked_at = acks.get(aid, (None, None))
                alerts.append(Alert(
                    alert_id=aid, site_id=sid, site_name=site.name, at=at, kind=kind,
                    from_level=prev, to_level=level, score=st.score, headline=hl,
                    triggering_detection_id=st.triggering_detection_id,
                    factors=st.factors, factor_status=st.factor_status,
                    processed_at=rd.processed_at, actions=actions, rule_ids=rule_ids,
                    acknowledged=aid in acks, acknowledged_by=acked_by,
                    acknowledged_at=acked_at,
                ))
            prev = level
    return alerts


def build_outbox(rd: ReplayData, rules: list, acks: dict, at: str) -> list[OutboxEmail]:
    provider = OutboxProvider()
    emails = [provider.email_for(a, rd.customer_id)
              for a in build_alerts(rd, rules, acks)
              if a.kind == "escalation" and a.at <= at]
    emails.reverse()  # newest first
    return emails


# ------------------------------------------------------------------ incidents

def _episodes(rd: ReplayData) -> list[tuple[str, int, int]]:
    """(site_id, i, j) half-open index ranges of consecutive HIGH/CRITICAL steps."""
    out = []
    for sid in rd.sites:
        seq = rd.statuses[sid]
        i = 0
        while i < len(seq):
            if RANK[seq[i].level] >= 2:
                j = i
                while j < len(seq) and RANK[seq[j].level] >= 2:
                    j += 1
                out.append((sid, i, j))
                i = j
            else:
                i += 1
    return out


def _incident(rd: ReplayData, sid: str, i: int, j: int, rules: list,
              at: str | None) -> Incident:
    site = rd.sites[sid]
    opened_at = rd.steps[i]
    closed_at = rd.steps[j] if j < len(rd.steps) else None
    k = j - 1  # default: last open step
    if at is not None:
        kk = rd.index_of(at)
        if i <= kk < j:
            k = kk
    st = rd.statuses[sid][k]
    hl = rd.headlines[sid][k]
    actions, rule_ids = match_actions(
        rules, st.level, site.type, site.criticality, st.fire_moving_toward_site)
    return Incident(
        incident_id=f"{sid}_{compact(opened_at)}", site_id=sid, site_name=site.name,
        level=st.level, score=st.score, opened_at=opened_at, closed_at=closed_at,
        headline=hl, actions=actions, rule_ids=rule_ids,
        disclaimer=config.DISCLAIMER_INCIDENT,
    )


def incidents_open_at(rd: ReplayData, rules: list, at: str) -> list[Incident]:
    out = []
    for sid, i, j in _episodes(rd):
        opened_at = rd.steps[i]
        closed_at = rd.steps[j] if j < len(rd.steps) else None
        if opened_at <= at and (closed_at is None or at < closed_at):
            out.append(_incident(rd, sid, i, j, rules, at))
    out.sort(key=lambda inc: (0 if inc.level == "CRITICAL" else 1, -inc.score))
    return out


def incidents_history(rd: ReplayData, rules: list) -> list[Incident]:
    incs = [_incident(rd, sid, i, j, rules, None) for sid, i, j in _episodes(rd)]
    incs.sort(key=lambda inc: inc.opened_at)
    return incs


def incident_by_id(rd: ReplayData, rules: list, incident_id: str,
                   at: str | None) -> Incident | None:
    for sid, i, j in _episodes(rd):
        if f"{sid}_{compact(rd.steps[i])}" == incident_id:
            return _incident(rd, sid, i, j, rules, at)
    return None


# -------------------------------------------------------------------- summary

def build_summary(rd: ReplayData) -> ReplaySummary:
    transitions = []  # (factor_has_unknown, is_escalation)
    sites_high = sites_critical = reached = 0
    lead_times: list[float] = []
    missed = 0
    episodes = _episodes(rd)
    n_incidents = len(episodes)

    for sid in rd.sites:
        seq = rd.statuses[sid]
        prev = "NORMAL"
        ever_high = ever_crit = False
        first_high_idx = contact_idx = None
        for idx, st in enumerate(seq):
            if RANK[st.level] >= 2:
                ever_high = True
                if first_high_idx is None:
                    first_high_idx = idx
            if st.level == "CRITICAL":
                ever_crit = True
            if st.nearest_fire_km is not None and st.nearest_fire_km <= config.CONTACT_KM \
                    and contact_idx is None:
                contact_idx = idx
            if st.level != prev and (RANK[st.level] >= 2 or RANK[prev] >= 2):
                has_unknown = "unknown" in (
                    st.factor_status.proximity, st.factor_status.wind_alignment,
                    st.factor_status.weather, st.factor_status.fuel,
                    st.factor_status.vulnerability)
                transitions.append((has_unknown, RANK[st.level] > RANK[prev]))
            prev = st.level
        sites_high += 1 if ever_high else 0
        sites_critical += 1 if ever_crit else 0
        if contact_idx is not None:
            reached += 1
            if first_high_idx is not None and first_high_idx <= contact_idx:
                lead_times.append((contact_idx - first_high_idx) * config.STEP_HOURS)
            else:
                missed += 1

    alerts_raised = sum(1 for _, esc in transitions if esc)
    median_lead = round(statistics.median(lead_times), 1) if lead_times else None
    if transitions:
        coverage = round(100.0 * sum(1 for u, _ in transitions if not u) / len(transitions), 1)
    else:
        coverage = 100.0

    data_source = "synthetic_fallback"
    dets = FileDetectionsProvider().detections()
    if dets:
        data_source = dets[0].source

    return ReplaySummary(
        start=config.REPLAY_START, end=config.REPLAY_END, data_source=data_source,
        total_detections=rd.total_detections, detections_used=rd.detections_used,
        alerts_raised=alerts_raised, incidents=n_incidents,
        sites_ever_high=sites_high, sites_ever_critical=sites_critical,
        sites_reached_by_fire=reached, missed_exposures=missed,
        median_lead_time_hours=median_lead, explanation_coverage_pct=coverage,
    )
