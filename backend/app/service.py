"""service.py — request-time assembly shared by routes (sop_actions, portfolio)."""
from __future__ import annotations

import math

from app.models import Portfolio, PortfolioCounts, SiteStatus
from app.replay import ReplayData
from app.sop import RANK, match_actions


def with_sop(status: SiteStatus, site, rules) -> SiteStatus:
    """Return a copy with sop_actions computed from the CURRENT rules."""
    actions, _ = match_actions(rules, status.level, site.type, site.criticality,
                               status.fire_moving_toward_site)
    return status.model_copy(update={"sop_actions": actions})


def portfolio(rd: ReplayData, rules, at: str) -> Portfolio:
    sites = [with_sop(rd.status_at(sid, at), rd.sites[sid], rules) for sid in rd.sites]
    sites.sort(key=lambda s: (-RANK[s.level], -s.score, s.site_id))
    counts = PortfolioCounts(
        NORMAL=sum(1 for s in sites if s.level == "NORMAL"),
        ELEVATED=sum(1 for s in sites if s.level == "ELEVATED"),
        HIGH=sum(1 for s in sites if s.level == "HIGH"),
        CRITICAL=sum(1 for s in sites if s.level == "CRITICAL"),
    )
    exposed = sum(s.value_eur for s in sites if s.level in ("HIGH", "CRITICAL"))
    return Portfolio(at=at, counts=counts, total_exposed_value_eur=exposed, sites=sites)


def detections_near(rd, site, at: str):
    """Scored detections in the site's window — the same set the risk score saw."""
    from datetime import timedelta

    from app import config
    from app.providers.wildfire import FileDetectionsProvider
    from app.replay import fmt, parse

    win = fmt(parse(at) - timedelta(hours=config.DETECTION_WINDOW_HOURS))
    margin = config.FIRE_RADIUS_KM + site.radius_m / 1000.0
    dlat = margin / 111.0
    dlon = margin / (111.0 * max(0.01, math.cos(math.radians(site.lat))))
    return [d for d in FileDetectionsProvider().detections()
            if d.confidence in ("n", "h") and win < d.observed_at <= at
            and abs(d.lat - site.lat) <= dlat and abs(d.lon - site.lon) <= dlon]


def forecast_for(rd, site, at: str):
    """SpreadForecast for one site, or None when no fire is in range."""
    from app import config, spread
    from app.models import SpreadForecast
    from app.providers.weather import WeatherService

    f = spread.forecast_site(site, WeatherService().get(site.site_id, at),
                             detections_near(rd, site, at), at)
    if f is None:
        return None
    return SpreadForecast(method=config.METHOD_SPREAD, disclaimer=config.DISCLAIMER_SPREAD,
                          **vars(f))
