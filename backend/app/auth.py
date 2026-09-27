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


# A dummy salt and hash so an unknown account costs the same PBKDF2 work as a real one.
# Without this, a fast 401 versus a slow 401 tells an attacker which accounts exist.
_DUMMY_SALT = "00" * 16
_DUMMY_HASH = hashlib.pbkdf2_hmac("sha256", b"x", bytes.fromhex(_DUMMY_SALT), 200_000).hex()

MIN_SECRET_LEN = 32


def _in_production() -> bool:
    return (os.environ.get("VERCEL_ENV") == "production"
            or os.environ.get("ENV", "").lower() == "production")


def _secret() -> str:
    """The signing key. In production a missing or short key is fatal rather than a warning:
    signing with a published default would let anyone mint a token for any tenant."""
    s = os.environ.get("JWT_SECRET")
    if not s:
        if _in_production():
            raise RuntimeError(
                "JWT_SECRET is not set. Refusing to sign tokens with the dev default in "
                "production, because anyone reading this source could forge a token.")
        logging.warning("JWT_SECRET not set; using the dev-only default secret.")
        return "dev-only-change-me"
    if len(s) < MIN_SECRET_LEN:
        # Deliberately a warning, not fatal. A short real secret is weaker than it should be,
        # but it is not forgeable the way the published default is, and taking a running
        # deployment down over key length would be the larger outage. Rotate it to 32+ bytes.
        logging.warning("JWT_SECRET is %d characters; HS256 wants at least %d. Rotate it.",
                        len(s), MIN_SECRET_LEN)
    return s


def dummy_verify() -> None:
    """Burn the same CPU a real password check would, for an account that does not exist."""
    verify_password("x", _DUMMY_SALT, _DUMMY_HASH)


def make_token(email: str, customer_id: str, role: str) -> str:
    now = int(time.time())
    payload = {"sub": email, "cid": customer_id, "role": role,
               "iat": now, "jti": secrets.token_hex(8),
               "exp": now + config.TOKEN_HOURS * 3600}
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> dict:
    """HS256 only, and every claim we authorise on must be present. Pinning the algorithm
    matters: without it a caller could present an unsigned `alg: none` token."""
    return jwt.decode(token, _secret(), algorithms=["HS256"],
                      options={"require": ["exp", "sub", "cid", "role"]})


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


STAFF_ROLES = ("admin", "operator")


def require_staff(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Company employees only; partner organisations use /situation and /sensors."""
    if user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="forbidden")
    return user
