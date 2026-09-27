"""routes/risk.py — portfolio, site status, timeline, detections, summary, handoff (§2.5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app import handoff as handoff_mod
from app import service, state
from app.auth import AuthUser, get_current_user, require_staff
from app.db import get_db
from app.models import (
    Detection, HandoffPack, Portfolio, ReplaySummary, SiteStatus, SpreadForecast,
    TimelinePoint,
)
from app.providers.weather import live_provider
from app.providers.wildfire import FileDetectionsProvider, firms_live
from app.replay import build_summary, parse, snap

router = APIRouter(tags=["risk"])


@router.get("/portfolio", response_model=Portfolio)
def portfolio(at: str | None = None, user: AuthUser = Depends(require_staff)) -> Portfolio:
    rd = state.get_replay(user.customer_id)
    rules = get_db().list_rules(user.customer_id)
    return service.portfolio(rd, rules, snap(at))


@router.get("/sites/{site_id}/status", response_model=SiteStatus)
def site_status(site_id: str, at: str | None = None,
                user: AuthUser = Depends(require_staff)) -> SiteStatus:
    rd = state.get_replay(user.customer_id)
    if site_id not in rd.sites:
        raise HTTPException(status_code=404, detail="site not found")
    rules = get_db().list_rules(user.customer_id)
    return service.with_sop(rd.status_at(site_id, snap(at)), rd.sites[site_id], rules)


@router.get("/sites/{site_id}/weather/live")
def live_weather(site_id: str, user: AuthUser = Depends(require_staff)) -> dict:
    """Current observed conditions at the site from weatherapi.com. The replay scores against
    the committed Open-Meteo archive; this is what a live deployment would use instead."""
    rd = state.get_replay(user.customer_id)
    if site_id not in rd.sites:
        raise HTTPException(status_code=404, detail="site not found")
    provider = live_provider()
    if provider is None:
        return {"available": False,
                "reason": "WEATHERAPI_KEY is not set; the replay uses the observed archive"}
    site = rd.sites[site_id]
    reading = provider.current(site.lat, site.lon)
    if reading is None:
        return {"available": False, "reason": "live weather provider unreachable"}
    return {"available": True, "site_id": site_id, "source": "weatherapi.com",
            "temp_c": reading.temp_c, "rh_pct": reading.rh_pct,
            "wind_speed_kmh": reading.speed_kmh, "wind_from_deg": reading.from_deg,
            "status": reading.status}


@router.get("/sites/{site_id}/fire/live")
def live_fire(site_id: str, radius_km: float = Query(default=25.0, ge=1.0, le=200.0),
              days: int = Query(default=1, ge=1, le=2),
              user: AuthUser = Depends(require_staff)) -> dict:
    """NASA FIRMS near-real-time detections around the site, right now.

    The replay scores the committed August 2025 archive; this is what a live deployment
    watches. NRT data lags the satellite pass by about 3 hours, which the response states so
    nobody reads an empty list as "nothing is burning".
    """
    rd = state.get_replay(user.customer_id)
    if site_id not in rd.sites:
        raise HTTPException(status_code=404, detail="site not found")
    provider = firms_live()
    if provider is None:
        return {"available": False, "reason": "FIRMS_MAP_KEY is not set"}
    site = rd.sites[site_id]
    rows = provider.near(site.lat, site.lon, radius_km, days)
    if rows is None:
        return {"available": False, "reason": "FIRMS near-real-time feed unreachable"}
    return {"available": True, "site_id": site_id, "source": "NASA FIRMS VIIRS NRT",
            "radius_km": radius_km, "days": days, "count": len(rows),
            "latency_note": "NRT detections lag the satellite pass by about 3 hours",
            "nearest_km": rows[0]["distance_km"] if rows else None,
            "detections": rows[:50]}


@router.get("/sites/{site_id}/forecast", response_model=SpreadForecast)
def site_forecast(site_id: str, at: str | None = None,
                  user: AuthUser = Depends(require_staff)) -> SpreadForecast:
    """How the fire is likely to develop toward this site: rate of spread, time to arrival
    and the front's position over the next 12 hours. 404 when no fire is within range."""
    rd = state.get_replay(user.customer_id)
    if site_id not in rd.sites:
        raise HTTPException(status_code=404, detail="site not found")
    f = service.forecast_for(rd, rd.sites[site_id], snap(at))
    if f is None:
        raise HTTPException(status_code=404, detail="no fire within range of this site")
    return f


@router.get("/sites/{site_id}/timeline", response_model=list[TimelinePoint])
def timeline(site_id: str, user: AuthUser = Depends(require_staff)) -> list[TimelinePoint]:
    rd = state.get_replay(user.customer_id)
    if site_id not in rd.sites:
        raise HTTPException(status_code=404, detail="site not found")
    return rd.timeline(site_id)


@router.get("/detections", response_model=list[Detection])
def detections(at: str | None = None,
               window_hours: int = Query(default=12, ge=1, le=48),
               user: AuthUser = Depends(get_current_user)) -> list[Detection]:
    """Raw satellite detections. `get_current_user`, not `require_staff`, is deliberate:
    these are public NASA FIRMS records carrying no site, asset or personnel data, and the
    partner roles exist precisely to see the fire situation. Every endpoint that joins a
    detection to a site requires staff. window_hours is capped so this cannot be used to pull
    the whole archive in one request."""
    at = snap(at)
    from datetime import timedelta
    from app.replay import fmt
    win_start = fmt(parse(at) - timedelta(hours=window_hours))
    out = [d for d in FileDetectionsProvider().detections()
           if d.confidence in ("n", "h") and win_start < d.observed_at <= at]
    out.sort(key=lambda d: d.observed_at)
    return out


@router.get("/replay/summary", response_model=ReplaySummary)
def replay_summary(user: AuthUser = Depends(require_staff)) -> ReplaySummary:
    return build_summary(state.get_replay(user.customer_id))


@router.get("/sites/{site_id}/handoff", response_model=HandoffPack)
def handoff(site_id: str, at: str | None = None,
            user: AuthUser = Depends(get_current_user)) -> HandoffPack:
    if user.role not in ("admin", "operator", "firefighter"):
        raise HTTPException(status_code=403, detail="forbidden")
    rd = state.get_replay(user.customer_id)
    if site_id not in rd.sites:
        raise HTTPException(status_code=404, detail="site not found")
    rules = get_db().list_rules(user.customer_id)
    at = snap(at)
    status = service.with_sop(rd.status_at(site_id, at), rd.sites[site_id], rules)
    return handoff_mod.build_pack(rd.sites[site_id], status, rd.headline_at(site_id, at), at)
