import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from auth import create_access_token, decode_token, get_current_user, hash_password, normalize_user_permissions, verify_password
from db import get_db
from models import ChangePasswordIn, LoginIn
from security_controls import clear_login_failures, client_ip, ensure_login_allowed, record_login_failure
from utils import log_activity, utc_now_iso

router = APIRouter(prefix="/api/auth", tags=["auth"])

def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

def _cookie_samesite() -> str:
    value = os.environ.get("COOKIE_SAMESITE", "lax").strip().lower()
    return value if value in {"lax", "strict", "none"} else "lax"

def _delete_auth_cookie(response: Response):
    response.delete_cookie("access_token", path="/", secure=_env_bool("COOKIE_SECURE", True), samesite=_cookie_samesite())

@router.post("/login")
async def login(payload: LoginIn, response: Response, request: Request):
    db = get_db()
    email = payload.email.lower().strip()
    await ensure_login_allowed(email, request)
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        await record_login_failure(email, request)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await clear_login_failures(email, request)
    token = create_access_token(user["id"], user["email"], user["role"], remember=payload.remember)
    claims = decode_token(token)
    expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc).replace(tzinfo=None)
    await db.auth_sessions.insert_one({
        "jti": claims["jti"], "user_id": user["id"],
        "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        "expires_at": expires_at, "ip": client_ip(request),
        "user_agent": request.headers.get("user-agent", "")[:300],
    })
    remember_days = int(os.environ.get("JWT_REMEMBER_DAYS", "7"))
    response.set_cookie(
        key="access_token", value=token, httponly=True,
        secure=_env_bool("COOKIE_SECURE", True), samesite=_cookie_samesite(),
        max_age=remember_days * 24 * 60 * 60 if payload.remember else None, path="/",
    )
    user.pop("password_hash", None)
    user["permissions"] = normalize_user_permissions(user)
    await log_activity(user, "login", "auth", f"User {user['email']} logged in")
    return {"access_token": token, "token_type": "bearer", "user": user}

@router.post("/logout")
async def logout(request: Request, response: Response, user: dict = Depends(get_current_user)):
    db = get_db()
    jti = getattr(request.state, "session_jti", None)
    if jti:
        await db.auth_sessions.delete_one({"jti": jti, "user_id": user["id"]})
    _delete_auth_cookie(response)
    await log_activity(user, "logout", "auth", f"User {user['email']} logged out")
    return {"message": "Logged out"}

@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user

@router.post("/change-password")
async def change_password(payload: ChangePasswordIn, response: Response, user: dict = Depends(get_current_user)):
    db = get_db()
    full = await db.users.find_one({"id": user["id"]})
    if not full or not verify_password(payload.old_password, full["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(payload.new_password) < 12:
        raise HTTPException(status_code=400, detail="New password must be at least 12 characters")
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_password(payload.new_password), "updated_at": utc_now_iso()}})
    await db.auth_sessions.delete_many({"user_id": user["id"]})
    _delete_auth_cookie(response)
    await log_activity(user, "change_password", "auth", "Password changed; all sessions revoked")
    return {"message": "Password updated. Please sign in again.", "reauthenticate": True}
