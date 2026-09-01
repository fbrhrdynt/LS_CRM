"""Account Management (Credential Vault) — encrypts secrets at rest."""
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_current_user, require_admin
from db import get_db
from models import AccountCreate, AccountUpdate
from security import decrypt_secret, encrypt_secret
from utils import log_activity, new_id, paginate, utc_now_iso

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

SECRET_FIELDS = ("password", "api_key", "secret_key")

CATEGORIES = [
    "Starlink", "Google Workspace", "Microsoft 365", "Cloudflare",
    "Domain", "Hosting", "VPS", "cPanel", "VPN",
    "MikroTik", "UniFi", "Synology", "CCTV", "Custom",
]


def _mask(doc: dict) -> dict:
    """Return doc without decrypted secrets (for listing)."""
    out = {k: v for k, v in doc.items() if k not in SECRET_FIELDS}
    for f in SECRET_FIELDS:
        out[f"has_{f}"] = bool(doc.get(f))
    return out


def _encrypt_secrets(data: dict) -> dict:
    out = dict(data)
    for f in SECRET_FIELDS:
        if f in out and out[f] is not None:
            out[f] = encrypt_secret(out[f]) if out[f] else ""
    return out


@router.get("/categories")
async def get_categories(user: dict = Depends(get_current_user)):
    return CATEGORIES


@router.post("/generate-password")
async def generate_password(length: int = Query(16, ge=8, le=64), user: dict = Depends(get_current_user)):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+?"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw) and any(c in "!@#$%^&*-_=+?" for c in pw)):
            return {"password": pw}


@router.get("")
async def list_accounts(q: str = "", category: str = "", customer_id: str = "", project_id: str = "", page: int = 1, per_page: int = 20, user: dict = Depends(get_current_user)):
    db = get_db()
    query: dict = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"username": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"login_url": {"$regex": q, "$options": "i"}},
        ]
    if category:
        query["category"] = category
    if customer_id:
        query["customer_id"] = customer_id
    if project_id:
        query["project_id"] = project_id
    docs = await db.accounts.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    ids = list({d["customer_id"] for d in docs if d.get("customer_id")})
    cust_map = {}
    if ids:
        cust_docs = await db.customers.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "company_name": 1}).to_list(10000)
        cust_map = {c["id"]: c["company_name"] for c in cust_docs}
    masked = []
    for d in docs:
        m = _mask(d)
        m["customer_name"] = cust_map.get(d.get("customer_id"), "")
        masked.append(m)
    return paginate(masked, page, per_page)


@router.post("")
async def create_account(payload: AccountCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    data = _encrypt_secrets(payload.model_dump())
    data.update({"id": new_id(), "created_at": utc_now_iso(), "updated_at": utc_now_iso()})
    await db.accounts.insert_one(data)
    data.pop("_id", None)
    await log_activity(user, "create", "accounts", f"Account {data['name']} ({data['category']})")
    return _mask(data)


@router.get("/{aid}")
async def get_account(aid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.accounts.find_one({"id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _mask(doc)


@router.get("/{aid}/reveal")
async def reveal_secrets(aid: str, user: dict = Depends(get_current_user)):
    """Returns decrypted secrets — always logged."""
    db = get_db()
    doc = await db.accounts.find_one({"id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await log_activity(user, "view_secret", "accounts", f"Revealed secret for {doc.get('name')}")
    return {
        "password": decrypt_secret(doc.get("password", "")),
        "api_key": decrypt_secret(doc.get("api_key", "")),
        "secret_key": decrypt_secret(doc.get("secret_key", "")),
    }


@router.put("/{aid}")
async def update_account(aid: str, payload: AccountUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    raw = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not raw:
        raise HTTPException(status_code=400, detail="No fields to update")
    # Preserve existing secrets when caller sends empty string
    for f in SECRET_FIELDS:
        if f in raw and raw[f] == "":
            raw.pop(f)
    updates = _encrypt_secrets(raw)
    updates["updated_at"] = utc_now_iso()
    r = await db.accounts.update_one({"id": aid}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.accounts.find_one({"id": aid}, {"_id": 0})
    await log_activity(user, "update", "accounts", f"Account {doc.get('name')}")
    return _mask(doc)


@router.delete("/{aid}")
async def delete_account(aid: str, user: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.accounts.find_one({"id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await db.accounts.delete_one({"id": aid})
    await log_activity(user, "delete", "accounts", f"Account {doc.get('name')}")
    return {"message": "deleted"}
