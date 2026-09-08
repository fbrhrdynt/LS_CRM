"""JWT + bcrypt authentication utilities."""
import os
import uuid
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
    payload = {"sub": user_id, "email": email, "role": role, "jti": str(uuid.uuid4()), "exp": now + ttl, "iat": now, "type": "access"}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=os.environ.get("JWT_ALGORITHM", "HS256"))

def decode_token(token: str) -> dict:
    payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[os.environ.get("JWT_ALGORITHM", "HS256")])
    if payload.get("type") != "access" or not payload.get("sub") or not payload.get("jti"):
        raise jwt.InvalidTokenError("Invalid access token")
    return payload

def _extract_token(request: Request) -> Optional[str]:
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
    session = await db.auth_sessions.find_one({"jti": payload["jti"], "user_id": payload["sub"]}, {"_id": 0, "jti": 1})
    if not session:
        raise HTTPException(status_code=401, detail="Session revoked or expired")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    request.state.session_jti = payload["jti"]
    return user

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user
