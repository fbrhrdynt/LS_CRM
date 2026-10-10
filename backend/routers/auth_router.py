import asyncio
import hashlib
import html
import logging
import os
import secrets
import smtplib
import ssl
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pymongo import ReturnDocument

from auth import create_access_token, decode_token, get_current_user, hash_password, normalize_user_permissions, verify_password
from db import get_db
from models import ChangePasswordIn, CompletePasswordResetIn, ForgotPasswordIn, LoginIn
from security_controls import clear_login_failures, client_ip, ensure_login_allowed, record_login_failure
from utils import log_activity, utc_now_iso

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

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


def _send_password_reset_email(recipient: str, reset_url: str, expiry_minutes: int = 30):
    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    implicit_tls = _env_bool("SMTP_SECURE", False)
    username = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASS", "").strip()
    sender = os.environ.get("SMTP_FROM", "LogiSource Digital <info@logisourcedigital.web.id>").strip()
    reply_to = os.environ.get("SMTP_REPLY_TO", "support@logisourcedigital.web.id").strip()
    if not host or not username or not password or password.upper() in {"SET", "CHANGE_ME"}:
        raise RuntimeError("SMTP is not configured: set SMTP_HOST, SMTP_USER, and SMTP_PASS in backend/.env")

    safe_url = html.escape(reset_url, quote=True)
    text_body = (
        "LogiSource Digital - Integrated System\n\n"
        "Kami menerima permintaan untuk mengatur ulang password akun LogiSource CRM Anda.\n"
        f"Buka tautan berikut untuk membuat password baru (berlaku {expiry_minutes} menit):\n{reset_url}\n\n"
        "Jika Anda tidak meminta reset password, abaikan email ini.\n"
        "Bantuan: support@logisourcedigital.web.id"
    )
    html_body = f'''<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f5f9;font-family:Arial,Helvetica,sans-serif;color:#172033;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f5f9;padding:32px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;background:#ffffff;border:1px solid #e4e8f0;border-radius:12px;overflow:hidden;">
        <tr><td style="background:#10264a;padding:28px 32px;color:#ffffff;">
          <div style="font-size:21px;font-weight:700;letter-spacing:.2px;">LogiSource Digital</div>
          <div style="font-size:12px;letter-spacing:1.4px;text-transform:uppercase;color:#cbd7f0;margin-top:7px;">Integrated System</div>
        </td></tr>
        <tr><td style="padding:34px 32px 28px;">
          <p style="margin:0 0 12px;font-size:13px;font-weight:700;color:#315aa8;letter-spacing:1px;text-transform:uppercase;">Account Security</p>
          <h1 style="margin:0 0 18px;font-size:26px;line-height:1.25;color:#172033;">Reset your password</h1>
          <p style="margin:0 0 18px;font-size:15px;line-height:1.7;color:#46536a;">Kami menerima permintaan untuk mengatur ulang password akun LogiSource CRM Anda. Klik tombol di bawah untuk membuat password baru.</p>
          <table role="presentation" cellspacing="0" cellpadding="0" style="margin:24px 0 22px;"><tr><td bgcolor="#2459c4" style="border-radius:7px;">
            <a href="{safe_url}" style="display:inline-block;padding:14px 24px;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;">Reset Password</a>
          </td></tr></table>
          <p style="margin:0 0 8px;font-size:13px;line-height:1.65;color:#667085;">Tautan ini berlaku selama <strong>{expiry_minutes} menit</strong> dan hanya dapat digunakan satu kali.</p>
          <p style="margin:18px 0 8px;font-size:12px;line-height:1.6;color:#667085;">Jika tombol tidak berfungsi, salin tautan berikut ke browser Anda:</p>
          <p style="margin:0;word-break:break-all;font-size:12px;line-height:1.6;"><a href="{safe_url}" style="color:#2459c4;">{safe_url}</a></p>
          <div style="height:1px;background:#e8ecf3;margin:26px 0 20px;"></div>
          <p style="margin:0;font-size:13px;line-height:1.65;color:#667085;">Jika Anda tidak meminta reset password, abaikan email ini. Password Anda tidak akan berubah sampai tautan digunakan.</p>
        </td></tr>
        <tr><td style="background:#f8f9fc;padding:20px 32px;border-top:1px solid #e8ecf3;">
          <div style="font-size:12px;font-weight:700;color:#344054;">LogiSource Digital - Integrated System</div>
          <div style="font-size:12px;line-height:1.7;color:#667085;margin-top:5px;">Perlu bantuan? Balas email ini atau hubungi <a href="mailto:support@logisourcedigital.web.id" style="color:#2459c4;text-decoration:none;">support@logisourcedigital.web.id</a>.</div>
          <div style="font-size:11px;color:#98a2b3;margin-top:14px;">Email otomatis terkait keamanan akun. Mohon jangan membagikan tautan reset ini.</div>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>'''
    message = EmailMessage()
    message["Subject"] = "Reset Password - LogiSource Digital"
    message["From"] = sender
    message["To"] = recipient
    message["Reply-To"] = reply_to
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    context = ssl.create_default_context()
    if implicit_tls:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
            server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            if not server.has_extn("starttls"):
                raise RuntimeError("SMTP server does not advertise STARTTLS; refusing unencrypted login")
            server.starttls(context=context)
            server.ehlo()
            server.login(username, password)
            server.send_message(message)


async def _check_reset_rate_limit(email: str, request: Request):
    db = get_db()
    now = datetime.utcnow()
    window_seconds = 15 * 60
    bucket = int(now.timestamp() // window_seconds)
    scope = hashlib.sha256(f"{client_ip(request)}|{email.lower().strip()}".encode("utf-8")).hexdigest()
    key = f"password-reset:{scope}:{bucket}"
    result = await db.rate_limits.find_one_and_update(
        {"key": key},
        {"$inc": {"count": 1}, "$setOnInsert": {"scope": f"password-reset:{scope}", "created_at": now, "expires_at": now + timedelta(hours=1)}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    if int((result or {}).get("count", 0)) > 3:
        raise HTTPException(status_code=429, detail="Too many reset requests. Please try again in 15 minutes.", headers={"Retry-After": str(window_seconds)})
    # Also cap requests per source IP so rotating email addresses cannot bypass the limit.
    ip_scope = hashlib.sha256(client_ip(request).encode("utf-8")).hexdigest()
    ip_key = f"password-reset-ip:{ip_scope}:{bucket}"
    ip_result = await db.rate_limits.find_one_and_update(
        {"key": ip_key},
        {"$inc": {"count": 1}, "$setOnInsert": {"scope": f"password-reset-ip:{ip_scope}", "created_at": now, "expires_at": now + timedelta(hours=1)}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    if int((ip_result or {}).get("count", 0)) > 10:
        raise HTTPException(status_code=429, detail="Too many reset requests from this network. Please try again later.", headers={"Retry-After": str(window_seconds)})


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordIn, request: Request):
    email = payload.email.lower().strip()
    await _check_reset_rate_limit(email, request)
    db = get_db()
    user = await db.users.find_one({"email": email}, {"_id": 0, "id": 1, "email": 1})
    if user:
        raw_token = secrets.token_urlsafe(40)
        now = datetime.utcnow()
        await db.password_reset_tokens.delete_many({"user_id": user["id"], "used": False})
        await db.password_reset_tokens.insert_one({
            "token_hash": hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            "user_id": user["id"],
            "created_at": now,
            "expires_at": now + timedelta(minutes=30),
            "used": False,
        })
        app_url = os.environ.get("APP_URL", "https://crm.logisourcedigital.web.id").strip().rstrip("/")
        reset_url = f"{app_url}/reset-password?token={raw_token}"
        try:
            await asyncio.to_thread(_send_password_reset_email, email, reset_url, 30)
        except Exception:
            logger.exception("Unable to send password reset email")
    # Deliberately identical response for known and unknown addresses.
    return {"message": "If the email address is registered, a password reset link will be sent shortly."}


@router.post("/reset-password")
async def complete_password_reset(payload: CompletePasswordResetIn, response: Response):
    db = get_db()
    now = datetime.utcnow()
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    token_doc = await db.password_reset_tokens.find_one_and_update(
        {"token_hash": token_hash, "used": False, "expires_at": {"$gt": now}},
        {"$set": {"used": True, "used_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if not token_doc:
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired. Please request a new link.")
    user = await db.users.find_one({"id": token_doc["user_id"]}, {"_id": 0, "id": 1, "email": 1, "name": 1})
    if not user:
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired. Please request a new link.")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(payload.new_password), "updated_at": utc_now_iso()}},
    )
    await db.auth_sessions.delete_many({"user_id": user["id"]})
    await db.password_reset_tokens.update_many({"user_id": user["id"]}, {"$set": {"used": True, "used_at": now}})
    _delete_auth_cookie(response)
    await log_activity(user, "reset_password", "auth", "Password reset through email link; all sessions revoked")
    return {"message": "Password updated successfully. Please sign in with your new password."}

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
