"""routes/auth.py — login and current user (§2.5)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app import config
from app.auth import AuthUser, get_current_user, make_token, verify_password
from app.db import get_db
from app.models import LoginRequest, LoginResponse, User

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    row = get_db().get_user(body.email)
    if not row or not verify_password(body.password, row["salt"], row["hash"]):
        raise HTTPException(status_code=401, detail="invalid credentials")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    get_db().add_audit(row["customer_id"], now, row["email"], "login", "")
    token = make_token(row["email"], row["customer_id"], row["role"])
    user = User(email=row["email"], name=row["name"],
                customer_id=row["customer_id"], role=row["role"])
    return LoginResponse(access_token=token, expires_in=config.TOKEN_HOURS * 3600, user=user)


@router.get("/auth/me", response_model=User)
def me(user: AuthUser = Depends(get_current_user)) -> User:
    return User(email=user.email, name=user.name,
                customer_id=user.customer_id, role=user.role)
