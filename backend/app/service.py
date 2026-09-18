"""service.py — request-time assembly shared by routes (sop_actions, portfolio)."""
from __future__ import annotations

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
