"""routes/assets.py — sites list, sample CSV, import (§2.5)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app import state
from app.auth import AuthUser, get_current_user, require_admin
from app.db import get_db
from app.importer import parse_assets, sample_csv_text
from app.models import ImportReport, Site

router = APIRouter(tags=["assets"])


@router.get("/sites", response_model=list[Site])
def list_sites(user: AuthUser = Depends(get_current_user)) -> list[Site]:
    return get_db().list_assets(user.customer_id)  # already sorted by site_id


@router.get("/assets/sample.csv")
def sample_csv(user: AuthUser = Depends(get_current_user)) -> PlainTextResponse:
    return PlainTextResponse(sample_csv_text(), media_type="text/csv")


@router.post("/assets/import", response_model=ImportReport)
async def import_assets(file: UploadFile, user: AuthUser = Depends(require_admin)) -> ImportReport:
    data = await file.read()
    try:
        sites, report = parse_assets(data, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if report.accepted == 0:
        raise HTTPException(status_code=422, detail=report.model_dump())
    get_db().replace_assets(user.customer_id, sites)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    get_db().add_audit(user.customer_id, now, user.email, "assets_import",
                       f"accepted {report.accepted}")
    state.invalidate(user.customer_id)
    return report
