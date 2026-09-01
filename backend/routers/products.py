from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File

from auth import get_current_user, require_admin
from db import get_db
from excel_service import rows_to_xlsx, xlsx_to_dicts
from models import CategoryIn, ProductCreate, ProductUpdate
from pdf_service import build_product_catalog_pdf
from utils import log_activity, new_id, next_product_code, paginate, utc_now_iso

router = APIRouter(prefix="/api/products", tags=["products"])


# Categories
@router.get("/categories")
async def list_categories(user: dict = Depends(get_current_user)):
    db = get_db()
    return await db.product_categories.find({}, {"_id": 0}).sort("name", 1).to_list(500)


@router.post("/categories")
async def create_category(payload: CategoryIn, user: dict = Depends(get_current_user)):
    db = get_db()
    if await db.product_categories.find_one({"name": payload.name}):
        raise HTTPException(status_code=400, detail="Category exists")
    doc = {"id": new_id(), "name": payload.name, "created_at": utc_now_iso()}
    await db.product_categories.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "create", "products", f"Category {payload.name}")
    return doc


@router.delete("/categories/{cat_id}")
async def delete_category(cat_id: str, user: dict = Depends(require_admin)):
    db = get_db()
    r = await db.product_categories.delete_one({"id": cat_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await log_activity(user, "delete", "products", f"Category {cat_id}")
    return {"message": "deleted"}


# Products
@router.get("")
async def list_products(q: str = "", product_type: str = "", category: str = "", status: str = "", page: int = 1, per_page: int = 20, user: dict = Depends(get_current_user)):
    db = get_db()
    query: dict = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
            {"sku": {"$regex": q, "$options": "i"}},
            {"brand": {"$regex": q, "$options": "i"}},
        ]
    if product_type:
        query["product_type"] = product_type
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    docs = await db.products.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    return paginate(docs, page, per_page)


@router.get("/all")
async def list_all(user: dict = Depends(get_current_user)):
    db = get_db()
    return await db.products.find({}, {"_id": 0}).sort("name", 1).to_list(10000)


@router.post("")
async def create_product(payload: ProductCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    code = payload.code or await next_product_code(payload.product_type)
    if await db.products.find_one({"code": code}):
        raise HTTPException(status_code=400, detail="Product code already exists")
    doc = payload.model_dump()
    doc.update({"id": new_id(), "code": code, "created_at": utc_now_iso(), "updated_at": utc_now_iso()})
    await db.products.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "create", "products", f"Product {doc['name']} ({code})")
    return doc


@router.get("/export/pdf")
async def export_pdf(user: dict = Depends(get_current_user)):
    db = get_db()
    products = await db.products.find({}, {"_id": 0}).sort("name", 1).to_list(10000)
    settings = await db.settings.find_one({"id": "global"}, {"_id": 0}) or {}
    content = build_product_catalog_pdf(products, settings)
    await log_activity(user, "export", "products", "PDF catalog")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="products.pdf"'},
    )


@router.get("/export/xlsx")
async def export_xlsx(user: dict = Depends(get_current_user)):
    db = get_db()
    rows = await db.products.find({}, {"_id": 0}).sort("created_at", -1).to_list(10000)
    headers = ["code", "name", "product_type", "category", "brand", "description", "unit",
               "selling_price", "purchase_price", "tax_percent", "status", "sku", "stock",
               "warranty", "sla", "duration", "support_period"]
    data = [[r.get(h, "") for h in headers] for r in rows]
    content = rows_to_xlsx("Products", headers, data)
    await log_activity(user, "export", "products", "Excel export")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="products.xlsx"'},
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
        name = r.get("name")
        if not name:
            skipped += 1
            continue
        ptype = str(r.get("product_type") or "goods").lower()
        code = r.get("code") or await next_product_code(ptype)
        if await db.products.find_one({"code": code}):
            skipped += 1
            continue
        doc = {
            "id": new_id(),
            "code": code,
            "name": str(name),
            "product_type": ptype if ptype in ("goods", "service") else "goods",
            "category": str(r.get("category") or ""),
            "brand": str(r.get("brand") or ""),
            "description": str(r.get("description") or ""),
            "unit": str(r.get("unit") or "pcs"),
            "selling_price": float(r.get("selling_price") or 0),
            "purchase_price": float(r.get("purchase_price") or 0),
            "tax_percent": float(r.get("tax_percent") or 0),
            "status": str(r.get("status") or "active"),
            "sku": str(r.get("sku") or ""),
            "stock": int(r.get("stock") or 0),
            "warranty": str(r.get("warranty") or ""),
            "sla": str(r.get("sla") or ""),
            "duration": str(r.get("duration") or ""),
            "support_period": str(r.get("support_period") or ""),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        await db.products.insert_one(doc)
        created += 1
    await log_activity(user, "import", "products", f"Imported {created}, skipped {skipped}")
    return {"created": created, "skipped": skipped}


@router.get("/{product_id}")
async def get_product(product_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return doc


@router.put("/{product_id}")
async def update_product(product_id: str, payload: ProductUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = utc_now_iso()
    r = await db.products.update_one({"id": product_id}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    await log_activity(user, "update", "products", f"Product {doc.get('name')}")
    return doc


@router.delete("/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.products.delete_one({"id": product_id})
    await log_activity(user, "delete", "products", f"Product {doc.get('name')}")
    return {"message": "Deleted"}
