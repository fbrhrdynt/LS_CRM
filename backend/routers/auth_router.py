from fastapi import APIRouter, Depends, HTTPException, Response

from auth import create_access_token, get_current_user, hash_password, verify_password
from db import get_db
from models import ChangePasswordIn, LoginIn
from utils import log_activity, utc_now_iso

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(payload: LoginIn, response: Response):
    db = get_db()
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], user["email"], user["role"])
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7 if payload.remember else 60 * 60 * 12,
        path="/",
    )
    user.pop("password_hash", None)
    await log_activity(user, "login", "auth", f"User {user['email']} logged in")
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    await log_activity(user, "logout", "auth", f"User {user['email']} logged out")
    return {"message": "Logged out"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/change-password")
async def change_password(payload: ChangePasswordIn, user: dict = Depends(get_current_user)):
    db = get_db()
    full = await db.users.find_one({"id": user["id"]})
    if not full or not verify_password(payload.old_password, full["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(payload.new_password), "updated_at": utc_now_iso()}},
    )
    await log_activity(user, "change_password", "auth", "Password changed")
    return {"message": "Password updated"}
