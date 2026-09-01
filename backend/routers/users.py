from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, hash_password, require_admin
from db import get_db
from models import UserCreate, UserUpdate
from utils import log_activity, new_id, paginate, utc_now_iso

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
async def list_users(q: str = "", page: int = 1, per_page: int = 20, admin: dict = Depends(require_admin)):
    db = get_db()
    query = {}
    if q:
        query["$or"] = [{"name": {"$regex": q, "$options": "i"}}, {"email": {"$regex": q, "$options": "i"}}]
    docs = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(10000)
    return paginate(docs, page, per_page)


@router.post("")
async def create_user(payload: UserCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    doc = {
        "id": new_id(),
        "name": payload.name,
        "email": email,
        "role": payload.role,
        "password_hash": hash_password(payload.password),
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }
    await db.users.insert_one(doc)
    doc.pop("password_hash", None)
    doc.pop("_id", None)
    await log_activity(admin, "create", "users", f"User {email} ({payload.role})")
    return doc


@router.get("/{uid}")
async def get_user(uid: str, admin: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


@router.put("/{uid}")
async def update_user(uid: str, payload: UserUpdate, admin: dict = Depends(require_admin)):
    db = get_db()
    updates: dict = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.email is not None:
        updates["email"] = payload.email.lower().strip()
    if payload.role is not None:
        updates["role"] = payload.role
    if payload.password:
        if len(payload.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        updates["password_hash"] = hash_password(payload.password)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = utc_now_iso()
    r = await db.users.update_one({"id": uid}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    await log_activity(admin, "update", "users", f"User {doc.get('email')}")
    return doc


@router.delete("/{uid}")
async def delete_user(uid: str, admin: dict = Depends(require_admin)):
    if uid == admin["id"]:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")
    db = get_db()
    doc = await db.users.find_one({"id": uid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await db.users.delete_one({"id": uid})
    await log_activity(admin, "delete", "users", f"User {doc.get('email')}")
    return {"message": "deleted"}
