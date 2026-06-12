"""
Auth endpoints for the dashboard frontend.

POST /auth/register — self-serve company registration (public)
POST /auth/token    — email + password → short-lived access JWT + opaque refresh token
POST /auth/refresh  — swap a valid refresh token for a new access JWT
POST /auth/logout   — revoke a refresh token so it can never be used again
POST /auth/invite   — owner/admin invites a teammate (requires JWT)
POST /auth/users    — developer-only user provisioning (requires X-Admin-Secret)
"""
from __future__ import annotations

import asyncio
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
import bcrypt
from pydantic import BaseModel

from src.config import settings
from src.db import db
from src.services.twilio_provision import provision_phone_number
from src.utils.logger import logger
from src.utils.ratelimit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 60
_REFRESH_TOKEN_EXPIRE_DAYS = 7
_TRIAL_DAYS = 30

_bearer = HTTPBearer()


# ── Token helpers ──────────────────────────────────────────────────────────────

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


def _make_access_token(email: str, tenant_id: str, role: str) -> str:
    payload = {
        "sub": email,
        "tenant_id": tenant_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


async def _make_refresh_token(email: str, tenant_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)
    await db.table("refresh_tokens").insert({
        "token": token,
        "user_email": email,
        "tenant_id": tenant_id,
        "expires_at": expires_at.isoformat(),
    }).execute()
    return token


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _validate_password(password: str) -> str | None:
    """Returns an error message if the password is too weak, None if it passes."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one number"
    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must contain at least one special character"
    return None


def _require_role(allowed: list[str]):
    """Dependency — rejects request if caller's role is not in allowed list."""
    def _check(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
        payload = decode_token(credentials.credentials)
        if payload.get("role") not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return payload
    return _check


# ── Public: register ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    company_name: str
    trade_type: str
    name: str
    email: str
    password: str


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest):
    err = _validate_password(body.password)
    if err:
        raise HTTPException(status_code=422, detail=err)

    existing = await db.table("users").select("id").eq("email", body.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    trial_ends_at = (datetime.now(timezone.utc) + timedelta(days=_TRIAL_DAYS)).isoformat()
    tenant_result = await db.table("tenants").insert({
        "name": body.company_name,
        "trade_type": body.trade_type,
        "plan": "trial",
        "trial_ends_at": trial_ends_at,
    }).execute()
    if not tenant_result.data:
        raise HTTPException(status_code=500, detail="Failed to create company")
    tenant = tenant_result.data[0]

    if settings.twilio_auto_provision:
        try:
            loop = asyncio.get_running_loop()
            phone, phone_sid = await loop.run_in_executor(None, provision_phone_number)
            await db.table("tenants").update({"phone": phone, "twilio_phone_sid": phone_sid}).eq("id", tenant["id"]).execute()
            tenant["phone"] = phone
        except Exception as exc:
            logger.warning("Twilio provisioning failed — tenant created without phone", tenant_id=tenant["id"], error=str(exc))

    verification_token = secrets.token_urlsafe(32)
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user_result = await db.table("users").insert({
        "email": body.email,
        "name": body.name,
        "password_hash": hashed,
        "tenant_id": tenant["id"],
        "role": "owner",
        "active": True,
        "email_verified": False,
        "verification_token": verification_token,
    }).execute()
    if not user_result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    from src.services.email import send_verification_email
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: send_verification_email(body.email, body.name, verification_token))

    return {"message": "Account created. Please check your email to verify your account."}


# ── Public: login ──────────────────────────────────────────────────────────────

@router.post("/token", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    result = await db.table("users").select("email, password_hash, tenant_id, role, active, email_verified").eq("email", body.email).execute()
    user = result.data[0] if result.data else None

    if not user or not user.get("active") or not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("email_verified"):
        raise HTTPException(status_code=403, detail="Please verify your email before logging in. Check your inbox for the verification link.")

    access_token = _make_access_token(user["email"], user["tenant_id"], user.get("role", "member"))
    refresh_token = await _make_refresh_token(user["email"], user["tenant_id"])
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# ── Public: refresh / logout ───────────────────────────────────────────────────

@router.post("/refresh")
async def refresh(body: RefreshRequest):
    result = await db.table("refresh_tokens").select("*").eq("token", body.refresh_token).eq("revoked", False).execute()
    row = result.data[0] if result.data else None

    if not row:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = await db.table("users").select("role").eq("email", row["user_email"]).single().execute()
    role = (user.data or {}).get("role", "member")

    # Atomic revoke — if another request already revoked this token, bail.
    # This prevents two concurrent requests from each getting a new token from the same old one.
    revoked = await db.table("refresh_tokens").update({"revoked": True}).eq("token", body.refresh_token).eq("revoked", False).execute()
    if not revoked.data:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    new_refresh_token = await _make_refresh_token(row["user_email"], row["tenant_id"])

    access_token = _make_access_token(row["user_email"], row["tenant_id"], role)
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(body: LogoutRequest):
    await db.table("refresh_tokens").update({"revoked": True}).eq("token", body.refresh_token).execute()
    return {"ok": True}


# ── Public: verify email ──────────────────────────────────────────────────────

@router.get("/verify-email")
async def verify_email(token: str):
    result = await db.table("users").select("id, email_verified").eq("verification_token", token).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    if user.get("email_verified"):
        return {"message": "Email already verified. You can log in."}

    await db.table("users").update({
        "email_verified": True,
    }).eq("verification_token", token).execute()

    return {"message": "Email verified successfully. You can now log in."}


# ── Public: forgot / reset password ──────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    user = await db.table("users").select("id, name, email").eq("email", body.email).execute()
    if not user.data:
        return {"message": "If that email is registered, a reset link has been sent."}

    u = user.data[0]
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    await db.table("users").update({
        "password_reset_token": token,
        "password_reset_expires_at": expires_at,
    }).eq("id", u["id"]).execute()

    from src.services.email import send_password_reset_email
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: send_password_reset_email(u["email"], u["name"], token))
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset_password(request: Request, body: ResetPasswordRequest):
    err = _validate_password(body.new_password)
    if err:
        raise HTTPException(status_code=422, detail=err)

    result = await db.table("users").select("id, password_reset_expires_at").eq("password_reset_token", body.token).execute()
    user = result.data[0] if result.data else None
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    expires = datetime.fromisoformat(user["password_reset_expires_at"].replace("Z", "+00:00"))
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This reset link has expired. Please request a new one.")

    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    await db.table("users").update({
        "password_hash": new_hash,
        "password_reset_token": None,
        "password_reset_expires_at": None,
    }).eq("id", user["id"]).execute()
    return {"message": "Password updated successfully. You can now log in."}


# ── Authenticated: change password ────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    payload = decode_token(credentials.credentials)
    email = payload.get("sub", "")

    err = _validate_password(body.new_password)
    if err:
        raise HTTPException(status_code=422, detail=err)

    user = await db.table("users").select("id, password_hash").eq("email", email).single().execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")

    if not bcrypt.checkpw(body.current_password.encode(), user.data["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    await db.table("users").update({"password_hash": new_hash}).eq("id", user.data["id"]).execute()
    await db.table("refresh_tokens").update({"revoked": True}).eq("user_email", email).execute()
    return {"ok": True}


# ── Authenticated: invite teammate ─────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: str
    name: str
    role: str = "member"  # member | admin


@router.post("/invite", status_code=201)
async def invite_user(body: InviteRequest, payload: dict = Depends(_require_role(["owner", "admin"]))):
    if body.role not in ("member", "admin"):
        raise HTTPException(status_code=422, detail="Role must be 'member' or 'admin'")

    tenant_id = payload["tenant_id"]

    existing = await db.table("users").select("id").eq("email", body.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    temp_password = secrets.token_urlsafe(12)
    hashed = bcrypt.hashpw(temp_password.encode(), bcrypt.gensalt()).decode()

    result = await db.table("users").insert({
        "email": body.email,
        "name": body.name,
        "password_hash": hashed,
        "tenant_id": tenant_id,
        "role": body.role,
        "active": True,
        "email_verified": True,
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user = result.data[0]

    from src.services.email import send_invite_email
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: send_invite_email(body.email, body.name, temp_password))

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    }


# ── Developer-only: direct user provisioning ───────────────────────────────────

class CreateUserRequest(BaseModel):
    email: str
    password: str
    tenant_id: str
    role: str = "member"


@router.post("/users", status_code=201)
async def create_user(body: CreateUserRequest, x_admin_secret: str = Header(...)):
    """Turboman developer provisioning. Protected by X-Admin-Secret — not for tenants."""
    if not settings.admin_secret or not secrets.compare_digest(x_admin_secret, settings.admin_secret):
        raise HTTPException(status_code=403, detail="Forbidden")

    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    result = await db.table("users").insert({
        "email": body.email,
        "password_hash": hashed,
        "tenant_id": body.tenant_id,
        "role": body.role,
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user = result.data[0]
    return {"id": user["id"], "email": user["email"], "tenant_id": user["tenant_id"], "role": user["role"]}
