"""routes/sensors.py — ground-sensor mesh state and install/remove (all roles may read)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from app import sensors, state
from app.auth import AuthUser, get_current_user, require_admin
from app.db import get_db
from app.drills import now_iso
from app.models import SensorInstallRequest, SensorsResponse
from app.replay import snap

router = APIRouter(tags=["sensors"])


@router.get("/sensors", response_model=SensorsResponse)
def list_sensors(at: str | None = None, site_id: str | None = None,
                 user: AuthUser = Depends(get_current_user)) -> SensorsResponse:
    at = snap(at)
    rd = state.get_replay(user.customer_id)
    installs = get_db().list_installs(user.customer_id)
    meshes, nodes, events = sensors.snapshot(rd.sites, installs, at, site_id=site_id)
    return SensorsResponse(at=at, meshes=meshes, nodes=nodes, events=events)


@router.post("/sensors/install", status_code=201)
def install(body: SensorInstallRequest, user: AuthUser = Depends(require_admin)) -> dict:
    if body.site_id not in state.get_replay(user.customer_id).sites:
        raise HTTPException(status_code=404, detail="site not found")
    db = get_db()
    now = now_iso()
    db.add_install(user.customer_id, body.site_id, now)
    db.add_audit(user.customer_id, now, user.email, "sensor_mesh_install", body.site_id)
    return {"site_id": body.site_id, "installed": True}


@router.delete("/sensors/install/{site_id}", status_code=204)
def uninstall(site_id: str, user: AuthUser = Depends(require_admin)) -> Response:
    db = get_db()
    if site_id not in db.list_installs(user.customer_id):
        raise HTTPException(status_code=404, detail="no sensor mesh on this site")
    db.remove_install(user.customer_id, site_id)
    db.add_audit(user.customer_id, now_iso(), user.email, "sensor_mesh_remove", site_id)
    return Response(status_code=204)
