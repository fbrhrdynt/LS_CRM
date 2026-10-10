from fastapi import APIRouter, Depends, HTTPException, Response

from auth import get_current_user, require_admin, require_permission
from db import get_db
from models import QuotationCreate, QuotationUpdate
from pdf_service import build_document_pdf
from utils import log_activity, new_id, next_number, paginate, utc_now_iso

router = APIRouter(prefix="/api/quotations", tags=["quotations"], dependencies=[Depends(require_permission("quotations"))])


def _compute_totals(items):
    subtotal = discount = tax = grand = 0.0
    for it in items:
        qty = float(it.get("quantity", 0))
        up = float(it.get("unit_price", 0))
        d = float(it.get("discount_percent", 0))
        t = float(it.get("tax_percent", 0))
        s = qty * up
        d_amt = s * d / 100
        after = s - d_amt
        t_amt = after * t / 100
        subtotal += s
        discount += d_amt
        tax += t_amt
        grand += after + t_amt
    return {"subtotal": subtotal, "discount": discount, "tax": tax, "total": grand}


@router.get("")
async def list_quotations(q: str = "", status: str = "", customer_id: str = "", page: int = 1, per_page: int = 20, user: dict = Depends(get_current_user)):
    db = get_db()
    query: dict = {}
    if q:
        query["number"] = {"$regex": q, "$options": "i"}
    if status:
        query["status"] = status
    if customer_id:
        query["customer_id"] = customer_id
    docs = await db.quotations.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    # Attach customer_name and totals
    ids = list({d["customer_id"] for d in docs if d.get("customer_id")})
    cust_map = {}
    if ids:
        cust_docs = await db.customers.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "company_name": 1}).to_list(10000)
        cust_map = {c["id"]: c["company_name"] for c in cust_docs}
    for d in docs:
        d["customer_name"] = cust_map.get(d.get("customer_id"), "")
        d["totals"] = _compute_totals(d.get("items", []))
    return paginate(docs, page, per_page)


@router.post("")
async def create_quotation(payload: QuotationCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = payload.model_dump()
    if doc.get("project_id"):
        project = await db.projects.find_one({"id": doc["project_id"]}, {"_id": 0, "id": 1, "customer_id": 1})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        doc["customer_id"] = project["customer_id"]
    customer = await db.customers.find_one({"id": doc.get("customer_id")}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    for field in ("payment_terms", "payment_bank_name", "payment_bank_account_name", "payment_bank_account_number", "payment_bank_branch"):
        if not doc.get(field):
            doc[field] = customer.get(field, "") or ""
    number = await next_number("quotation")
    doc.update({
        "id": new_id(),
        "number": number,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "created_by": user["id"],
    })
    await db.quotations.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "create", "quotations", f"Quotation {number}")
    return doc


@router.get("/{qid}")
async def get_quotation(qid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.quotations.find_one({"id": qid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    cust = await db.customers.find_one({"id": doc.get("customer_id")}, {"_id": 0}) or {}
    doc["customer"] = cust
    doc["totals"] = _compute_totals(doc.get("items", []))
    return doc


@router.put("/{qid}")
async def update_quotation(qid: str, payload: QuotationUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    existing = await db.quotations.find_one({"id": qid}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates.get("project_id"):
        project = await db.projects.find_one({"id": updates["project_id"]}, {"_id": 0, "customer_id": 1})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        updates["customer_id"] = project["customer_id"]
    elif "customer_id" in updates and updates.get("customer_id"):
        updates["project_id"] = ""
    if "customer_id" in updates or "project_id" in updates:
        customer = await db.customers.find_one({"id": updates.get("customer_id", existing.get("customer_id"))}, {"_id": 0})
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        for field in ("payment_terms", "payment_bank_name", "payment_bank_account_name", "payment_bank_account_number", "payment_bank_branch"):
            if not updates.get(field):
                updates[field] = customer.get(field, "") or ""
    updates["updated_at"] = utc_now_iso()
    r = await db.quotations.update_one({"id": qid}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.quotations.find_one({"id": qid}, {"_id": 0})
    await log_activity(user, "update", "quotations", f"Quotation {doc.get('number')}")
    return doc


@router.post("/{qid}/status")
async def change_status(qid: str, status: str, user: dict = Depends(get_current_user)):
    if status not in ("draft", "sent", "approved", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status")
    db = get_db()
    r = await db.quotations.update_one({"id": qid}, {"$set": {"status": status, "updated_at": utc_now_iso()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.quotations.find_one({"id": qid}, {"_id": 0})
    await log_activity(user, f"status:{status}", "quotations", f"Quotation {doc.get('number')} -> {status}")
    return doc


@router.delete("/{qid}")
async def delete_quotation(qid: str, user: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.quotations.find_one({"id": qid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await db.quotations.delete_one({"id": qid})
    await log_activity(user, "delete", "quotations", f"Quotation {doc.get('number')}")
    return {"message": "deleted"}


@router.get("/{qid}/pdf")
async def quotation_pdf(qid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.quotations.find_one({"id": qid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    customer = await db.customers.find_one({"id": doc.get("customer_id")}, {"_id": 0}) or {}
    if doc.get("project_id"):
        project = await db.projects.find_one({"id": doc["project_id"]}, {"_id": 0, "name": 1}) or {}
        doc["project_name"] = project.get("name", "")
    settings = await db.settings.find_one({"id": "global"}, {"_id": 0}) or {}
    content = build_document_pdf("quotation", doc, customer, settings)
    await log_activity(user, "export_pdf", "quotations", f"Quotation {doc.get('number')} PDF")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.get("number","quotation")}.pdf"'},
    )
