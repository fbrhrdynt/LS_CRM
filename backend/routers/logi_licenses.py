"""LogiLicense — Admin management for external product licenses.

Each license is issued for a *product* (e.g. "MyIoT Dashboard"), has a plan
(e.g. "pro"), optional feature flags, optional expiry, and an activation limit.
External projects call the public API (see routers/public_license.py) with the
license key to verify Pro/Premium access.
"""
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict

from auth import get_current_user, require_admin
from db import get_db
from logilicense_tutorial_pdf import build_logilicense_tutorial_pdf
from utils import log_activity, new_id, paginate, utc_now_iso

router = APIRouter(prefix="/api/logi-licenses", tags=["logi-licenses"], dependencies=[Depends(require_admin)])


# ---------- Models ----------
class LogiLicenseBase(BaseModel):
    product_name: str
    product_slug: Optional[str] = ""
    plan: str = "pro"
    features: List[str] = []
    customer_id: Optional[str] = ""
    project_id: Optional[str] = ""
    max_activations: int = 1
    expiry_date: Optional[str] = ""  # empty = perpetual
    notes: Optional[str] = ""


class LogiLicenseCreate(LogiLicenseBase):
    pass


class LogiLicenseUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    product_name: Optional[str] = None
    product_slug: Optional[str] = None
    plan: Optional[str] = None
    features: Optional[List[str]] = None
    customer_id: Optional[str] = None
    project_id: Optional[str] = None
    max_activations: Optional[int] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[Literal["active", "suspended", "revoked"]] = None


# ---------- Helpers ----------
def _generate_key() -> str:
    """LOGI-XXXX-XXXX-XXXX-XXXX (uppercase alphanumeric, ambiguity-safe)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
    groups = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return "LOGI-" + "-".join(groups)


def _days_left(iso_date: str) -> Optional[int]:
    if not iso_date:
        return None
    try:
        d = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (d - datetime.now(timezone.utc)).days
    except Exception:
        return None


async def _stats(license_id: str) -> dict:
    db = get_db()
    activations = await db.logi_activations.count_documents({"license_id": license_id})
    checks = await db.logi_checks.count_documents({"license_id": license_id})
    return {"activations_count": activations, "checks_count": checks}


@router.get("/setup-guide/pdf")
async def setup_guide_pdf(request: Request, user: dict = Depends(get_current_user)):
    """Generic LogiLicense setup tutorial PDF — how to generate a license and integrate it in any project."""
    db = get_db()
    settings = await db.settings.find_one({"id": "global"}, {"_id": 0}) or {}
    base_url = str(request.base_url).rstrip("/")
    content = build_logilicense_tutorial_pdf(settings, base_url, license=None)
    await log_activity(user, "export_pdf", "logi-licenses", "Downloaded LogiLicense setup guide")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="LogiLicense-Setup-Guide.pdf"'},
    )


@router.get("/{lid}/tutorial/pdf")
async def per_license_tutorial_pdf(lid: str, request: Request, user: dict = Depends(get_current_user)):
    """LogiLicense setup tutorial personalised with THIS license's key & product_slug."""
    db = get_db()
    lic = await db.logi_licenses.find_one({"id": lid}, {"_id": 0})
    if not lic:
        raise HTTPException(status_code=404, detail="Not found")
    settings = await db.settings.find_one({"id": "global"}, {"_id": 0}) or {}
    base_url = str(request.base_url).rstrip("/")
    content = build_logilicense_tutorial_pdf(settings, base_url, license=lic)
    await log_activity(user, "export_pdf", "logi-licenses", f"Tutorial PDF for {lic['license_key']}")
    fname = f"LogiLicense-{lic.get('product_slug') or lic['id'][:8]}-guide.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ---------- Endpoints ----------
@router.get("")
async def list_licenses(
    q: str = "",
    status: str = "",
    plan: str = "",
    page: int = 1,
    per_page: int = 20,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    query: dict = {}
    if q:
        query["$or"] = [
            {"product_name": {"$regex": q, "$options": "i"}},
            {"product_slug": {"$regex": q, "$options": "i"}},
            {"license_key": {"$regex": q, "$options": "i"}},
            {"notes": {"$regex": q, "$options": "i"}},
        ]
    if status:
        query["status"] = status
    if plan:
        query["plan"] = plan
    docs = await db.logi_licenses.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)

    # attach counts & customer name
    ids = list({d["customer_id"] for d in docs if d.get("customer_id")})
    cust_map = {}
    if ids:
        cust_docs = await db.customers.find(
            {"id": {"$in": ids}}, {"_id": 0, "id": 1, "company_name": 1}
        ).to_list(10000)
        cust_map = {c["id"]: c["company_name"] for c in cust_docs}
    for d in docs:
        d["customer_name"] = cust_map.get(d.get("customer_id"), "")
        stats = await _stats(d["id"])
        d.update(stats)
        d["days_left"] = _days_left(d.get("expiry_date", ""))
    return paginate(docs, page, per_page)


@router.post("")
async def create_license(payload: LogiLicenseCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    # Ensure unique key
    for _ in range(5):
        key = _generate_key()
        if not await db.logi_licenses.find_one({"license_key": key}):
            break
    else:
        raise HTTPException(status_code=500, detail="Could not generate a unique key")

    doc = payload.model_dump()
    doc.update({
        "id": new_id(),
        "license_key": key,
        "status": "active",
        "activation_count": 0,
        "issued_at": utc_now_iso(),
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "issued_by": user["id"],
    })
    await db.logi_licenses.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "create", "logi-licenses", f"License {key} for {payload.product_name}")
    return doc


@router.get("/{lid}")
async def get_license(lid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.logi_licenses.find_one({"id": lid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc.update(await _stats(lid))
    doc["days_left"] = _days_left(doc.get("expiry_date", ""))
    return doc


@router.put("/{lid}")
async def update_license(lid: str, payload: LogiLicenseUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = utc_now_iso()
    r = await db.logi_licenses.update_one({"id": lid}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.logi_licenses.find_one({"id": lid}, {"_id": 0})
    await log_activity(user, "update", "logi-licenses", f"License {doc['license_key']}")
    return doc


@router.post("/{lid}/revoke")
async def revoke_license(lid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    r = await db.logi_licenses.update_one(
        {"id": lid}, {"$set": {"status": "revoked", "updated_at": utc_now_iso()}}
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.logi_licenses.find_one({"id": lid}, {"_id": 0})
    await log_activity(user, "revoke", "logi-licenses", f"License {doc['license_key']}")
    return doc


@router.post("/{lid}/reactivate")
async def reactivate_license(lid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    r = await db.logi_licenses.update_one(
        {"id": lid}, {"$set": {"status": "active", "updated_at": utc_now_iso()}}
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.logi_licenses.find_one({"id": lid}, {"_id": 0})
    await log_activity(user, "reactivate", "logi-licenses", f"License {doc['license_key']}")
    return doc


@router.delete("/{lid}")
async def delete_license(lid: str, user: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.logi_licenses.find_one({"id": lid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await db.logi_licenses.delete_one({"id": lid})
    await db.logi_activations.delete_many({"license_id": lid})
    await db.logi_checks.delete_many({"license_id": lid})
    await log_activity(user, "delete", "logi-licenses", f"License {doc['license_key']}")
    return {"message": "deleted"}


# --- Activations ---
@router.get("/{lid}/activations")
async def list_activations(lid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    docs = await db.logi_activations.find(
        {"license_id": lid}, {"_id": 0}
    ).sort("activated_at", -1).to_list(1000)
    return docs


@router.delete("/{lid}/activations/{aid}")
async def deactivate(lid: str, aid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    r = await db.logi_activations.delete_one({"id": aid, "license_id": lid})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Activation not found")
    # decrement counter (safe if goes below 0 we clamp)
    lic = await db.logi_licenses.find_one({"id": lid})
    if lic:
        new_count = max(0, int(lic.get("activation_count", 0)) - 1)
        await db.logi_licenses.update_one(
            {"id": lid},
            {"$set": {"activation_count": new_count, "updated_at": utc_now_iso()}},
        )
    await log_activity(user, "deactivate", "logi-licenses", f"License {lid} device {aid}")
    return {"message": "deactivated"}


# --- Check audit ---
@router.get("/{lid}/checks")
async def list_checks(lid: str, page: int = 1, per_page: int = 50, user: dict = Depends(get_current_user)):
    db = get_db()
    docs = await db.logi_checks.find(
        {"license_id": lid}, {"_id": 0}
    ).sort("timestamp", -1).to_list(2000)
    return paginate(docs, page, per_page)
