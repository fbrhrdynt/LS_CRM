from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, require_admin, require_permission
from db import get_db
from models import ProjectCreate, ProjectUpdate
from utils import log_activity, new_id, next_number, paginate, utc_now_iso

router = APIRouter(prefix="/api/projects", tags=["projects"], dependencies=[Depends(require_permission("projects"))])


@router.get("")
async def list_projects(q: str = "", status: str = "", customer_id: str = "", page: int = 1, per_page: int = 20, user: dict = Depends(get_current_user)):
    db = get_db()
    query: dict = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"number": {"$regex": q, "$options": "i"}},
        ]
    if status:
        query["status"] = status
    if customer_id:
        query["customer_id"] = customer_id
    docs = await db.projects.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    ids = list({d["customer_id"] for d in docs if d.get("customer_id")})
    cust_map = {}
    if ids:
        cust_docs = await db.customers.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "company_name": 1}).to_list(10000)
        cust_map = {c["id"]: c["company_name"] for c in cust_docs}
    for d in docs:
        d["customer_name"] = cust_map.get(d.get("customer_id"), "")
    return paginate(docs, page, per_page)


@router.get("/all")
async def list_all(user: dict = Depends(get_current_user)):
    db = get_db()
    return await db.projects.find({}, {"_id": 0}).sort("name", 1).to_list(10000)


@router.post("")
async def create_project(payload: ProjectCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    number = await next_number("project")
    doc = payload.model_dump()
    doc.update({"id": new_id(), "number": number, "created_at": utc_now_iso(), "updated_at": utc_now_iso()})
    await db.projects.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "create", "projects", f"Project {number} — {doc['name']}")
    return doc


@router.get("/{pid}")
async def get_project(pid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc["customer"] = await db.customers.find_one({"id": doc.get("customer_id")}, {"_id": 0}) or {}
    if doc.get("product_ids"):
        doc["products"] = await db.products.find({"id": {"$in": doc["product_ids"]}}, {"_id": 0}).to_list(500)
    else:
        doc["products"] = []
    if doc.get("account_ids"):
        docs = await db.accounts.find({"id": {"$in": doc["account_ids"]}}, {"_id": 0}).to_list(500)
        for a in docs:
            a.pop("password", None)
            a.pop("api_key", None)
            a.pop("secret_key", None)
        doc["accounts"] = docs
    else:
        doc["accounts"] = []
    if doc.get("license_ids"):
        doc["licenses"] = await db.licenses.find({"id": {"$in": doc["license_ids"]}}, {"_id": 0}).to_list(500)
    else:
        doc["licenses"] = []
    return doc


@router.put("/{pid}")
async def update_project(pid: str, payload: ProjectUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updates["updated_at"] = utc_now_iso()
    r = await db.projects.update_one({"id": pid}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.projects.find_one({"id": pid}, {"_id": 0})
    await log_activity(user, "update", "projects", f"Project {doc.get('number')}")
    return doc


@router.delete("/{pid}")
async def delete_project(pid: str, user: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await db.projects.delete_one({"id": pid})
    await log_activity(user, "delete", "projects", f"Project {doc.get('number')}")
    return {"message": "deleted"}
