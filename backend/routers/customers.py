from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response

from auth import get_current_user, require_admin, require_permission
from db import get_db
from excel_service import rows_to_xlsx, xlsx_to_dicts
from models import CustomerCreate, CustomerUpdate
from utils import log_activity, new_id, next_customer_code, paginate, utc_now_iso

router = APIRouter(prefix="/api/customers", tags=["customers"], dependencies=[Depends(require_permission("customers"))])


@router.get("")
async def list_customers(
    q: str = "",
    page: int = 1,
    per_page: int = 20,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    query: dict = {}
    if q:
        query["$or"] = [
            {"company_name": {"$regex": q, "$options": "i"}},
            {"pic_name": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"phone": {"$regex": q, "$options": "i"}},
        ]
    docs = await db.customers.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    return paginate(docs, page, per_page)


@router.get("/all")
async def list_all(user: dict = Depends(get_current_user)):
    db = get_db()
    docs = await db.customers.find({}, {"_id": 0}).sort("company_name", 1).to_list(10000)
    return docs


@router.post("")
async def create_customer(payload: CustomerCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    code = payload.code or await next_customer_code()
    if await db.customers.find_one({"code": code}):
        raise HTTPException(status_code=400, detail="Customer code already exists")
    doc = payload.model_dump()
    doc.update({
        "id": new_id(),
        "code": code,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    })
    await db.customers.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "create", "customers", f"Customer {doc['company_name']} ({code})")
    return doc


@router.get("/{customer_id}")
async def get_customer(customer_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Customer not found")
    return doc


@router.put("/{customer_id}")
async def update_customer(customer_id: str, payload: CustomerUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = utc_now_iso()
    res = await db.customers.update_one({"id": customer_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    doc = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    await log_activity(user, "update", "customers", f"Customer {doc.get('company_name')}")
    return doc


@router.delete("/{customer_id}")
async def delete_customer(customer_id: str, user: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Customer not found")
    await db.customers.delete_one({"id": customer_id})
    await log_activity(user, "delete", "customers", f"Customer {doc.get('company_name')}")
    return {"message": "Deleted"}


@router.get("/export/xlsx")
async def export_xlsx(user: dict = Depends(get_current_user)):
    db = get_db()
    rows = await db.customers.find({}, {"_id": 0}).sort("created_at", -1).to_list(10000)
    headers = ["code", "company_name", "pic_name", "position", "phone", "email", "address", "website", "notes"]
    data = [[r.get(h, "") for h in headers] for r in rows]
    content = rows_to_xlsx("Customers", headers, data)
    await log_activity(user, "export", "customers", "Excel export")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="customers.xlsx"'},
    )


@router.post("/import/xlsx")
async def import_xlsx(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    content = await file.read()
    try:
        rows = xlsx_to_dicts(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Excel: {e}")
    db = get_db()
    created = 0
    skipped = 0
    for r in rows:
        cn = r.get("company_name")
        if not cn:
            skipped += 1
            continue
        code = r.get("code") or await next_customer_code()
        if await db.customers.find_one({"code": code}):
            skipped += 1
            continue
        doc = {
            "id": new_id(),
            "code": code,
            "company_name": str(cn),
            "pic_name": str(r.get("pic_name") or ""),
            "position": str(r.get("position") or ""),
            "phone": str(r.get("phone") or ""),
            "email": str(r.get("email") or ""),
            "address": str(r.get("address") or ""),
            "website": str(r.get("website") or ""),
            "notes": str(r.get("notes") or ""),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        await db.customers.insert_one(doc)
        created += 1
    await log_activity(user, "import", "customers", f"Imported {created}, skipped {skipped}")
    return {"created": created, "skipped": skipped}
