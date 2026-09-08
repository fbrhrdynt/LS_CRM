from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, require_admin, require_permission
from db import get_db
from models import LicenseCreate, LicenseUpdate
from utils import log_activity, new_id, paginate, utc_now_iso

router = APIRouter(prefix="/api/licenses", tags=["licenses"], dependencies=[Depends(require_permission("licenses"))])


def _days_left(iso_date: str) -> int | None:
    if not iso_date:
        return None
    try:
        d = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        delta = (d - datetime.now(timezone.utc)).days
        return delta
    except Exception:
        return None


@router.get("")
async def list_licenses(q: str = "", within_days: int = 0, page: int = 1, per_page: int = 20, user: dict = Depends(get_current_user)):
    db = get_db()
    query: dict = {}
    if q:
        query["$or"] = [
            {"registration_number": {"$regex": q, "$options": "i"}},
            {"license_code": {"$regex": q, "$options": "i"}},
            {"product_name": {"$regex": q, "$options": "i"}},
        ]
    docs = await db.licenses.find(query, {"_id": 0}).sort("expiry_date", 1).to_list(10000)
    ids = list({d["customer_id"] for d in docs if d.get("customer_id")})
    cust_map = {}
    if ids:
        cust_docs = await db.customers.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "company_name": 1}).to_list(10000)
        cust_map = {c["id"]: c["company_name"] for c in cust_docs}
    for d in docs:
        d["customer_name"] = cust_map.get(d.get("customer_id"), "")
        d["days_left"] = _days_left(d.get("expiry_date", ""))
    if within_days > 0:
        docs = [d for d in docs if d["days_left"] is not None and 0 <= d["days_left"] <= within_days]
    return paginate(docs, page, per_page)


@router.post("")
async def create_license(payload: LicenseCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = payload.model_dump()
    doc.update({"id": new_id(), "created_at": utc_now_iso(), "updated_at": utc_now_iso()})
    await db.licenses.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "create", "licenses", f"License {doc.get('license_code','')}")
    return doc


@router.get("/{lid}")
async def get_license(lid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.licenses.find_one({"id": lid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc["days_left"] = _days_left(doc.get("expiry_date", ""))
    return doc


@router.put("/{lid}")
async def update_license(lid: str, payload: LicenseUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updates["updated_at"] = utc_now_iso()
    r = await db.licenses.update_one({"id": lid}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.licenses.find_one({"id": lid}, {"_id": 0})
    await log_activity(user, "update", "licenses", f"License {doc.get('license_code','')}")
    return doc


@router.delete("/{lid}")
async def delete_license(lid: str, user: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.licenses.find_one({"id": lid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await db.licenses.delete_one({"id": lid})
    await log_activity(user, "delete", "licenses", f"License {doc.get('license_code','')}")
    return {"message": "deleted"}
