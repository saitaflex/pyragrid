"""auth.py — PBKDF2 password hashing, JWT (HS256), FastAPI auth dependencies (§5.3)."""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException

from app import config


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return salt, h.hex()


def verify_password(password: str, salt: str, hash_hex: str) -> bool:
    _, h = hash_password(password, salt)
    return secrets.compare_digest(h, hash_hex)


def _secret() -> str:
    s = os.environ.get("JWT_SECRET")
    if not s:
        logging.warning("JWT_SECRET not set; using the dev-only default secret.")
        s = "dev-only-change-me"
    return s


def make_token(email: str, customer_id: str, role: str) -> str:
    payload = {"sub": email, "cid": customer_id, "role": role,
               "exp": int(time.time()) + config.TOKEN_HOURS * 3600}
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=["HS256"])


@dataclass
class AuthUser:
    email: str
    name: str
    customer_id: str
    role: str


def get_current_user(authorization: str = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="not authenticated")
    try:
        payload = decode_token(authorization[7:])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid credentials")
    from app.db import get_db
    row = get_db().get_user(payload["sub"])
    if not row:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return AuthUser(email=row["email"], name=row["name"],
                    customer_id=row["customer_id"], role=row["role"])


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="forbidden")
    return user
