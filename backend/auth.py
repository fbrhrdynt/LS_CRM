"""JWT + bcrypt authentication utilities."""
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status

from db import get_db


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str, role: str, remember: bool = False) -> str:
    access_minutes = int(os.environ.get("JWT_ACCESS_MINUTES", "60"))
    remember_days = int(os.environ.get("JWT_REMEMBER_DAYS", "7"))
    ttl = timedelta(days=remember_days) if remember else timedelta(minutes=access_minutes)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": now + ttl,
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=os.environ.get("JWT_ALGORITHM", "HS256"))


def decode_token(token: str) -> dict:
    return jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[os.environ.get("JWT_ALGORITHM", "HS256")])


def _extract_token(request: Request) -> Optional[str]:
    # Browser sessions prefer the HttpOnly cookie. Bearer remains supported
    # for scripts/integrations so existing API clients keep working.
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def get_current_user(request: Request) -> dict:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    db = get_db()
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user
