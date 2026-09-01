from fastapi import APIRouter, Depends, HTTPException, Response

from auth import get_current_user, require_admin
from db import get_db
from models import InvoiceCreate, InvoiceUpdate
from pdf_service import build_document_pdf
from utils import log_activity, new_id, next_number, paginate, utc_now_iso

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


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
async def list_invoices(q: str = "", status: str = "", customer_id: str = "", page: int = 1, per_page: int = 20, user: dict = Depends(get_current_user)):
    db = get_db()
    query: dict = {}
    if q:
        query["number"] = {"$regex": q, "$options": "i"}
    if status:
        query["status"] = status
    if customer_id:
        query["customer_id"] = customer_id
    docs = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
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
async def create_invoice(payload: InvoiceCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    number = await next_number("invoice")
    doc = payload.model_dump()
    doc.update({
        "id": new_id(),
        "number": number,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "created_by": user["id"],
    })
    await db.invoices.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "create", "invoices", f"Invoice {number}")
    return doc


@router.post("/from-quotation/{qid}")
async def create_from_quotation(qid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    q = await db.quotations.find_one({"id": qid}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    number = await next_number("invoice")
    doc = {
        "id": new_id(),
        "number": number,
        "customer_id": q["customer_id"],
        "quotation_id": qid,
        "date": q.get("date", ""),
        "due_date": "",
        "currency": q.get("currency", "IDR"),
        "items": q.get("items", []),
        "notes": q.get("notes", ""),
        "payment_terms": q.get("payment_terms", ""),
        "status": "unpaid",
        "paid_amount": 0,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "created_by": user["id"],
    }
    await db.invoices.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "create", "invoices", f"Invoice {number} from Quotation {q['number']}")
    return doc


@router.get("/{iid}")
async def get_invoice(iid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.invoices.find_one({"id": iid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    cust = await db.customers.find_one({"id": doc.get("customer_id")}, {"_id": 0}) or {}
    doc["customer"] = cust
    doc["totals"] = _compute_totals(doc.get("items", []))
    return doc


@router.put("/{iid}")
async def update_invoice(iid: str, payload: InvoiceUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updates["updated_at"] = utc_now_iso()
    r = await db.invoices.update_one({"id": iid}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.invoices.find_one({"id": iid}, {"_id": 0})
    await log_activity(user, "update", "invoices", f"Invoice {doc.get('number')}")
    return doc


@router.post("/{iid}/status")
async def change_status(iid: str, status: str, user: dict = Depends(get_current_user)):
    if status not in ("draft", "unpaid", "partial", "paid", "cancelled"):
        raise HTTPException(status_code=400, detail="Invalid status")
    db = get_db()
    r = await db.invoices.update_one({"id": iid}, {"$set": {"status": status, "updated_at": utc_now_iso()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.invoices.find_one({"id": iid}, {"_id": 0})
    await log_activity(user, f"status:{status}", "invoices", f"Invoice {doc.get('number')} -> {status}")
    return doc


@router.delete("/{iid}")
async def delete_invoice(iid: str, user: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.invoices.find_one({"id": iid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await db.invoices.delete_one({"id": iid})
    await log_activity(user, "delete", "invoices", f"Invoice {doc.get('number')}")
    return {"message": "deleted"}


@router.get("/{iid}/pdf")
async def invoice_pdf(iid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.invoices.find_one({"id": iid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    customer = await db.customers.find_one({"id": doc.get("customer_id")}, {"_id": 0}) or {}
    settings = await db.settings.find_one({"id": "global"}, {"_id": 0}) or {}
    content = build_document_pdf("invoice", doc, customer, settings)
    await log_activity(user, "export_pdf", "invoices", f"Invoice {doc.get('number')} PDF")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.get("number","invoice")}.pdf"'},
    )
