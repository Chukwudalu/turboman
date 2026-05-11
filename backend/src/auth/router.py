"""
Auth endpoints for the dashboard frontend.

POST /auth/token   — email + password → short-lived access JWT + opaque refresh token.
POST /auth/refresh — swap a valid refresh token for a new access JWT.
POST /auth/logout  — revoke a refresh token so it can never be used again.
POST /auth/users   — create a new dashboard user (requires X-Admin-Secret header).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Request
from jose import jwt
import bcrypt
from pydantic import BaseModel

from src.config import settings
from src.db import db
from src.utils.ratelimit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 15
_REFRESH_TOKEN_EXPIRE_DAYS = 7


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class CreateUserRequest(BaseModel):
    email: str
    password: str
    tenant_id: str


def _make_access_token(email: str, tenant_id: str) -> str:
    payload = {
        "sub": email,
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def _make_refresh_token(email: str, tenant_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)
    db.table("refresh_tokens").insert({
        "token": token,
        "user_email": email,
        "tenant_id": tenant_id,
        "expires_at": expires_at.isoformat(),
    }).execute()
    return token


@router.post("/token", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    result = db.table("users").select("email, password_hash, tenant_id, active").eq("email", body.email).execute()
    user = result.data[0] if result.data else None

    if not user or not user.get("active") or not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = _make_access_token(user["email"], user["tenant_id"])
    refresh_token = _make_refresh_token(user["email"], user["tenant_id"])
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    result = db.table("refresh_tokens").select("*").eq("token", body.refresh_token).eq("revoked", False).execute()
    row = result.data[0] if result.data else None

    if not row:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    access_token = _make_access_token(row["user_email"], row["tenant_id"])
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(body: LogoutRequest):
    db.table("refresh_tokens").update({"revoked": True}).eq("token", body.refresh_token).execute()
    return {"ok": True}


#admin secret might be used for creating a new tenant when they onboard or pay the service, not creating a new user
#under a tenant that already uses our services. ---- Still exploring the implementation 
@router.post("/users", status_code=201)
async def create_user(body: CreateUserRequest, x_admin_secret: str = Header(...)):
    """Create a dashboard user. Protected by X-Admin-Secret header."""
    if not settings.admin_secret or x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    result = db.table("users").insert({
        "email": body.email,
        "password_hash": hashed,
        "tenant_id": body.tenant_id,
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user = result.data[0]
    return {"id": user["id"], "email": user["email"], "tenant_id": user["tenant_id"]}


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
