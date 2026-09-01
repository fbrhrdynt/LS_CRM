from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from auth import get_current_user
from db import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _month_key(iso_str: str) -> str | None:
    if not iso_str:
        return None
    try:
        d = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return d.strftime("%Y-%m")
    except Exception:
        return None


def _last_12_months():
    now = datetime.now(timezone.utc)
    months = []
    for i in range(11, -1, -1):
        m = now - timedelta(days=i * 30)
        months.append(m.strftime("%Y-%m"))
    seen = set()
    ordered = []
    for m in months:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered[-12:]


def _days_left(iso_date: str) -> int | None:
    if not iso_date:
        return None
    try:
        d = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (d - datetime.now(timezone.utc)).days
    except Exception:
        return None


@router.get("/summary")
async def summary(user: dict = Depends(get_current_user)):
    db = get_db()
    counts = {
        "customers": await db.customers.count_documents({}),
        "products": await db.products.count_documents({}),
        "projects": await db.projects.count_documents({}),
        "quotations": await db.quotations.count_documents({}),
        "invoices": await db.invoices.count_documents({}),
        "accounts": await db.accounts.count_documents({}),
        "licenses": await db.licenses.count_documents({}),
        "users": await db.users.count_documents({}),
    }

    # Alerts
    licenses = await db.licenses.find({}, {"_id": 0}).to_list(10000)
    alerts_license_30 = []
    alerts_license_7 = []
    for l in licenses:
        dl = _days_left(l.get("expiry_date", ""))
        if dl is not None and 0 <= dl <= 30:
            item = {"id": l["id"], "name": l.get("product_name") or l.get("license_code"), "days_left": dl, "expiry_date": l.get("expiry_date")}
            alerts_license_30.append(item)
            if dl <= 7:
                alerts_license_7.append(item)

    # Account expiring (registrations / subscriptions)
    accounts = await db.accounts.find({}, {"_id": 0}).to_list(10000)
    alerts_registration = []
    for a in accounts:
        dl = _days_left(a.get("expiry_date", ""))
        if dl is not None and 0 <= dl <= 30:
            alerts_registration.append({
                "id": a["id"], "name": a.get("name"), "category": a.get("category"),
                "days_left": dl, "expiry_date": a.get("expiry_date")
            })

    # Unpaid invoices
    unpaid = await db.invoices.find({"status": {"$in": ["unpaid", "partial"]}}, {"_id": 0}).sort("due_date", 1).to_list(50)
    for u in unpaid:
        u["days_overdue"] = None
        if u.get("due_date"):
            dl = _days_left(u["due_date"])
            u["days_overdue"] = -dl if dl is not None and dl < 0 else 0
        # attach customer name
        cust = await db.customers.find_one({"id": u.get("customer_id")}, {"_id": 0, "company_name": 1}) if u.get("customer_id") else None
        u["customer_name"] = cust.get("company_name") if cust else ""

    # Monthly charts (last 12 months)
    months = _last_12_months()
    qts = await db.quotations.find({}, {"_id": 0, "created_at": 1}).to_list(20000)
    invs = await db.invoices.find({}, {"_id": 0, "created_at": 1}).to_list(20000)
    custs = await db.customers.find({}, {"_id": 0, "created_at": 1}).to_list(20000)

    def bucket(rows):
        counter = {m: 0 for m in months}
        for r in rows:
            k = _month_key(r.get("created_at", ""))
            if k in counter:
                counter[k] += 1
        return [{"month": m, "count": counter[m]} for m in months]

    charts = {
        "monthly_quotations": bucket(qts),
        "monthly_invoices": bucket(invs),
        "monthly_customers": bucket(custs),
    }

    # Recent activity
    recent = await db.activity_logs.find({}, {"_id": 0}).sort("timestamp", -1).to_list(10)

    return {
        "counts": counts,
        "alerts": {
            "licenses_30d": alerts_license_30,
            "licenses_7d": alerts_license_7,
            "registrations_30d": alerts_registration,
            "unpaid_invoices": unpaid,
        },
        "charts": charts,
        "recent_activity": recent,
    }
