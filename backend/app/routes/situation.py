"""routes/situation.py — shared situational picture for partners (fire service, government,
NGOs) and staff, filtered by a per-role data-sharing policy."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app import sensors, state
from app.auth import AuthUser, get_current_user
from app.db import get_db
from app.models import PortfolioCounts, SharingPolicy, Situation, SituationSite
from app.replay import snap

router = APIRouter(tags=["situation"])

POLICIES = {
    "admin": SharingPolicy(role="admin", label="Company admin", asset_values=True,
                           personnel=True, access_routes=True, criticality=True, handoff=True,
                           company_ops=True),
    "operator": SharingPolicy(role="operator", label="Company operator", asset_values=True,
                              personnel=True, access_routes=True, criticality=True,
                              handoff=True, company_ops=True),
    "firefighter": SharingPolicy(role="firefighter", label="Fire service", asset_values=False,
                                 personnel=True, access_routes=True, criticality=True,
                                 handoff=True, company_ops=False),
    "government": SharingPolicy(role="government", label="Civil protection / government",
                                asset_values=False, personnel=True, access_routes=False,
                                criticality=True, handoff=False, company_ops=False),
    "ngo": SharingPolicy(role="ngo", label="NGO / community", asset_values=False,
                         personnel=False, access_routes=False, criticality=False,
                         handoff=False, company_ops=False),
}


@router.get("/situation", response_model=Situation)
def situation(at: str | None = None, user: AuthUser = Depends(get_current_user)) -> Situation:
    at = snap(at)
    pol = POLICIES[user.role]
    rd = state.get_replay(user.customer_id)
    installs = get_db().list_installs(user.customer_id)
    burning = sensors.ground_fire_sites(rd.sites, installs, at)
    sites = []
    for sid, site in rd.sites.items():
        st = rd.status_at(sid, at)
        sites.append(SituationSite(
            site_id=sid, name=site.name, type=site.type, lat=site.lat, lon=site.lon,
            radius_m=site.radius_m, level=st.level, score=st.score,
            nearest_fire_km=st.nearest_fire_km, fire_bearing_deg=st.fire_bearing_deg,
            fire_moving_toward_site=st.fire_moving_toward_site,
            criticality=site.criticality if pol.criticality else None,
            personnel_on_site=site.personnel_on_site if pol.personnel else None,
            access_routes=st.access_routes if pol.access_routes else None,
            value_eur=site.value_eur if pol.asset_values else None,
            sensors_installed=sid in installs, ground_fire=sid in burning))
    rank = {"CRITICAL": 0, "HIGH": 1, "ELEVATED": 2, "NORMAL": 3}
    sites.sort(key=lambda s: (rank[s.level], -s.score, s.site_id))
    counts = PortfolioCounts(**{lv: sum(1 for s in sites if s.level == lv) for lv in rank})
    return Situation(at=at, viewer_role=user.role, policy=pol,
                     matrix=[POLICIES[r] for r in ("operator", "firefighter", "government", "ngo")],
                     counts=counts, sites=sites)
