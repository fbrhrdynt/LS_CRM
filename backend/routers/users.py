from fastapi import APIRouter, Depends, HTTPException

from auth import PERMISSION_ORDER, hash_password, normalize_user_permissions, require_admin, validate_permissions
from db import get_db
from models import ResetPasswordIn, UserCreate, UserUpdate
from utils import log_activity, new_id, paginate, utc_now_iso

router = APIRouter(prefix="/api/users", tags=["users"])


def _public_user(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    doc["permissions"] = normalize_user_permissions(doc)
    return doc


@router.get("/permissions")
async def permission_catalog(admin: dict = Depends(require_admin)):
    labels = {
        "customers": "Customers",
        "products": "Products",
        "quotations": "Quotations",
        "invoices": "Invoices",
        "projects": "Projects",
        "accounts": "Credential Vault",
        "licenses": "Licenses",
        "logi_license": "LogiLicense",
        "activity_logs": "Activity Logs",
    }
    return [{"key": p, "label": labels[p]} for p in PERMISSION_ORDER]


@router.get("")
async def list_users(q: str = "", page: int = 1, per_page: int = 20, admin: dict = Depends(require_admin)):
    db = get_db()
    query = {}
    if q:
        query["$or"] = [{"name": {"$regex": q, "$options": "i"}}, {"email": {"$regex": q, "$options": "i"}}]
    docs = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(10000)
    return paginate([_public_user(d) for d in docs], page, per_page)


@router.post("")
async def create_user(payload: UserCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    permissions = list(PERMISSION_ORDER) if payload.role == "admin" else validate_permissions(payload.permissions)
    doc = {
        "id": new_id(), "name": payload.name, "email": email, "role": payload.role,
        "permissions": permissions, "password_hash": hash_password(payload.password),
        "created_at": utc_now_iso(), "updated_at": utc_now_iso(),
    }
    await db.users.insert_one(doc)
    await log_activity(admin, "create", "users", f"User {email} ({payload.role}) access={','.join(permissions)}")
    return _public_user(doc)


@router.get("/{uid}")
async def get_user(uid: str, admin: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _public_user(doc)


@router.put("/{uid}")
async def update_user(uid: str, payload: UserUpdate, admin: dict = Depends(require_admin)):
    db = get_db()
    current = await db.users.find_one({"id": uid}, {"_id": 0})
    if not current:
        raise HTTPException(status_code=404, detail="Not found")
    if uid == admin["id"] and payload.role is not None and payload.role != "admin":
        raise HTTPException(status_code=400, detail="You cannot remove your own administrator role")

    updates = {}
    access_changed = False
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.email is not None:
        email = payload.email.lower().strip()
        if await db.users.find_one({"email": email, "id": {"$ne": uid}}):
            raise HTTPException(status_code=400, detail="Email already registered")
        updates["email"] = email

    new_role = payload.role if payload.role is not None else current.get("role", "staff")
    if payload.role is not None and payload.role != current.get("role"):
        updates["role"] = payload.role
        access_changed = True

    if new_role == "admin":
        permissions = list(PERMISSION_ORDER)
        if normalize_user_permissions(current) != permissions:
            updates["permissions"] = permissions
            access_changed = True
    elif payload.permissions is not None:
        permissions = validate_permissions(payload.permissions)
        if normalize_user_permissions(current) != permissions:
            updates["permissions"] = permissions
            access_changed = True
    elif current.get("role") == "admin" and new_role == "staff":
        updates["permissions"] = []
        access_changed = True

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = utc_now_iso()
    await db.users.update_one({"id": uid}, {"$set": updates})
    if access_changed:
        await db.auth_sessions.delete_many({"user_id": uid})
    doc = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    await log_activity(admin, "update", "users", f"User {doc.get('email')} role/access updated")
    return _public_user(doc)


@router.post("/{uid}/reset-password")
async def reset_password(uid: str, payload: ResetPasswordIn, admin: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.users.find_one({"id": uid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await db.users.update_one({"id": uid}, {"$set": {"password_hash": hash_password(payload.new_password), "updated_at": utc_now_iso()}})
    await db.auth_sessions.delete_many({"user_id": uid})
    await log_activity(admin, "reset_password", "users", f"Password reset for {doc.get('email')}")
    return {"message": "Password reset. All active sessions were signed out."}


@router.delete("/{uid}")
async def delete_user(uid: str, admin: dict = Depends(require_admin)):
    if uid == admin["id"]:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")
    db = get_db()
    doc = await db.users.find_one({"id": uid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await db.users.delete_one({"id": uid})
    await db.auth_sessions.delete_many({"user_id": uid})
    await log_activity(admin, "delete", "users", f"User {doc.get('email')}")
    return {"message": "deleted"}
