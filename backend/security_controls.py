"""Security controls shared by authentication and HTTP middleware."""
import hashlib
import os
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from pymongo import ReturnDocument
from starlette.responses import JSONResponse

from db import get_db

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

def _utc_naive():
    return datetime.utcnow()

def client_ip(request: Request) -> str:
    host = request.client.host if request.client else ""
    if host in {"", "127.0.0.1", "::1"}:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return host or "unknown"

def _login_scope(email: str, request: Request) -> str:
    material = f"{client_ip(request)}|{email.lower().strip()}".encode()
    return hashlib.sha256(material).hexdigest()

def _bucket(seconds: int) -> int:
    return int(_utc_naive().timestamp() // seconds)

async def ensure_login_allowed(email: str, request: Request):
    window_min = max(1, int(os.environ.get("LOGIN_RATE_WINDOW_MINUTES", "15")))
    max_failures = max(1, int(os.environ.get("LOGIN_MAX_FAILURES", "5")))
    seconds = window_min * 60
    scope = _login_scope(email, request)
    key = f"login:{scope}:{_bucket(seconds)}"
    doc = await get_db().rate_limits.find_one({"key": key}, {"_id": 0, "count": 1})
    if doc and int(doc.get("count", 0)) >= max_failures:
        raise HTTPException(429, "Too many failed login attempts. Please try again later.", headers={"Retry-After": str(seconds)})

async def record_login_failure(email: str, request: Request):
    window_min = max(1, int(os.environ.get("LOGIN_RATE_WINDOW_MINUTES", "15")))
    seconds = window_min * 60
    scope = _login_scope(email, request)
    now = _utc_naive()
    key = f"login:{scope}:{_bucket(seconds)}"
    await get_db().rate_limits.find_one_and_update(
        {"key": key},
        {"$inc": {"count": 1}, "$setOnInsert": {"scope": f"login:{scope}", "created_at": now, "expires_at": now + timedelta(seconds=seconds * 2)}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

async def clear_login_failures(email: str, request: Request):
    scope = _login_scope(email, request)
    await get_db().rate_limits.delete_many({"scope": f"login:{scope}"})

async def public_license_rate_limited(request: Request) -> bool:
    limit = max(1, int(os.environ.get("PUBLIC_LICENSE_REQUESTS_PER_MINUTE", "120")))
    now = _utc_naive()
    digest = hashlib.sha256(f"{client_ip(request)}|{_bucket(60)}".encode()).hexdigest()
    doc = await get_db().rate_limits.find_one_and_update(
        {"key": f"public-license:{digest}"},
        {"$inc": {"count": 1}, "$setOnInsert": {"scope": "public-license", "created_at": now, "expires_at": now + timedelta(minutes=3)}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int((doc or {}).get("count", 0)) > limit

def _allowed_origins():
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return {x.strip().rstrip("/") for x in raw.split(",") if x.strip()}

def _request_origin(request: Request) -> str:
    origin = (request.headers.get("origin") or "").strip().rstrip("/")
    if origin:
        return origin
    referer = (request.headers.get("referer") or "").strip()
    if not referer:
        return ""
    try:
        parts = urlsplit(referer)
        return f"{parts.scheme}://{parts.netloc}".rstrip("/")
    except Exception:
        return ""

async def security_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/public/license/") and request.method == "POST":
        if await public_license_rate_limited(request):
            return JSONResponse({"detail": "Too many requests"}, status_code=429, headers={"Retry-After": "60"})

    if (path.startswith("/api/") and request.method not in SAFE_METHODS
            and request.cookies.get("access_token")
            and not request.headers.get("authorization", "").startswith("Bearer ")):
        if _request_origin(request) not in _allowed_origins():
            return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
    if (request.headers.get("x-forwarded-proto") or "").lower() == "https" or request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if path.startswith(("/api/auth", "/api/accounts", "/api/settings")):
        response.headers.setdefault("Cache-Control", "no-store")
    return response
