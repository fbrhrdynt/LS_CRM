"""Public license verification API.

No authentication — external client apps present just the license key.
Every call is audit-logged in logi_checks.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db import get_db
from utils import new_id, utc_now_iso

router = APIRouter(prefix="/api/public/license", tags=["public-license"])


class VerifyIn(BaseModel):
    license_key: str
    fingerprint: Optional[str] = ""
    product_slug: Optional[str] = ""


class ActivateIn(BaseModel):
    license_key: str
    fingerprint: str
    hostname: Optional[str] = ""
    product_slug: Optional[str] = ""


class HeartbeatIn(BaseModel):
    license_key: str
    fingerprint: str


def _client_ip(request: Request) -> str:
    xf = request.headers.get("x-forwarded-for", "")
    if xf:
        return xf.split(",")[0].strip()
    return request.client.host if request.client else ""


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


async def _record_check(license_id: Optional[str], key: str, fingerprint: str, request: Request, result: str, message: str):
    db = get_db()
    await db.logi_checks.insert_one({
        "id": new_id(),
        "license_id": license_id,
        "key_prefix": (key or "")[:9],  # LOGI-XXXX
        "fingerprint": fingerprint or "",
        "ip": _client_ip(request),
        "user_agent": request.headers.get("user-agent", "")[:200],
        "result": result,
        "message": message,
        "timestamp": utc_now_iso(),
    })


def _license_public_view(lic: dict) -> dict:
    """Only expose non-sensitive fields to external callers."""
    return {
        "valid": True,
        "product_name": lic.get("product_name"),
        "product_slug": lic.get("product_slug", ""),
        "plan": lic.get("plan"),
        "features": lic.get("features", []),
        "status": lic.get("status"),
        "expiry_date": lic.get("expiry_date", ""),
        "days_left": _days_left(lic.get("expiry_date", "")),
        "max_activations": lic.get("max_activations", 0),
        "activation_count": lic.get("activation_count", 0),
        "verified_at": utc_now_iso(),
    }


async def _resolve(key: str, product_slug: str = ""):
    """Fetch license by key (and optional product_slug enforcement)."""
    if not key:
        return None, "missing_key"
    db = get_db()
    lic = await db.logi_licenses.find_one({"license_key": key.strip()}, {"_id": 0})
    if not lic:
        return None, "not_found"
    if product_slug and (lic.get("product_slug") or "") and lic["product_slug"] != product_slug:
        return lic, "product_mismatch"
    return lic, None


@router.post("/verify")
async def verify(payload: VerifyIn, request: Request):
    """Silent verification. Returns valid:true/false + plan + features.
    Never throws 404 — always returns a JSON body so external clients can safely fall back to trial."""
    lic, err = await _resolve(payload.license_key, payload.product_slug or "")

    if err == "missing_key" or err == "not_found":
        await _record_check(None, payload.license_key, payload.fingerprint or "", request, "invalid", "License not found")
        return {"valid": False, "reason": "invalid_key", "message": "License key not recognised.", "plan": "trial"}

    if err == "product_mismatch":
        await _record_check(lic["id"], payload.license_key, payload.fingerprint or "", request, "product_mismatch", "Wrong product")
        return {"valid": False, "reason": "product_mismatch", "message": "License is for a different product.", "plan": "trial"}

    status = lic.get("status")
    if status == "revoked":
        await _record_check(lic["id"], payload.license_key, payload.fingerprint or "", request, "revoked", "Revoked by issuer")
        return {"valid": False, "reason": "revoked", "message": "License has been revoked.", "plan": "trial"}
    if status == "suspended":
        await _record_check(lic["id"], payload.license_key, payload.fingerprint or "", request, "suspended", "Suspended")
        return {"valid": False, "reason": "suspended", "message": "License is suspended.", "plan": "trial"}

    dl = _days_left(lic.get("expiry_date", ""))
    if dl is not None and dl < 0:
        await _record_check(lic["id"], payload.license_key, payload.fingerprint or "", request, "expired", "Past expiry date")
        return {"valid": False, "reason": "expired", "message": "License has expired.", "plan": "trial", "expiry_date": lic.get("expiry_date")}

    # Update last_seen for this fingerprint if it's activated
    if payload.fingerprint:
        db = get_db()
        await db.logi_activations.update_one(
            {"license_id": lic["id"], "fingerprint": payload.fingerprint},
            {"$set": {"last_seen_at": utc_now_iso(), "last_ip": _client_ip(request)}},
        )

    await _record_check(lic["id"], payload.license_key, payload.fingerprint or "", request, "valid", "OK")
    return _license_public_view(lic)


@router.post("/activate")
async def activate(payload: ActivateIn, request: Request):
    """Register a device fingerprint under a license, subject to max_activations."""
    lic, err = await _resolve(payload.license_key, payload.product_slug or "")

    if err in ("missing_key", "not_found"):
        await _record_check(None, payload.license_key, payload.fingerprint, request, "invalid", "License not found")
        return {"activated": False, "reason": "invalid_key", "message": "License key not recognised.", "plan": "trial"}
    if err == "product_mismatch":
        await _record_check(lic["id"], payload.license_key, payload.fingerprint, request, "product_mismatch", "Wrong product")
        return {"activated": False, "reason": "product_mismatch", "message": "Wrong product for this license.", "plan": "trial"}

    if lic["status"] != "active":
        await _record_check(lic["id"], payload.license_key, payload.fingerprint, request, lic["status"], "Not active")
        return {"activated": False, "reason": lic["status"], "message": f"License is {lic['status']}.", "plan": "trial"}

    dl = _days_left(lic.get("expiry_date", ""))
    if dl is not None and dl < 0:
        await _record_check(lic["id"], payload.license_key, payload.fingerprint, request, "expired", "Expired")
        return {"activated": False, "reason": "expired", "message": "License expired.", "plan": "trial"}

    db = get_db()
    existing = await db.logi_activations.find_one(
        {"license_id": lic["id"], "fingerprint": payload.fingerprint}, {"_id": 0}
    )
    if existing:
        # Idempotent — just refresh last_seen
        await db.logi_activations.update_one(
            {"id": existing["id"]},
            {"$set": {"last_seen_at": utc_now_iso(), "last_ip": _client_ip(request)}},
        )
        await _record_check(lic["id"], payload.license_key, payload.fingerprint, request, "valid", "Re-activated")
        return {"activated": True, "already_activated": True, **_license_public_view(lic)}

    # Check activation limit
    current = int(lic.get("activation_count", 0))
    limit = int(lic.get("max_activations", 1))
    if limit > 0 and current >= limit:
        await _record_check(lic["id"], payload.license_key, payload.fingerprint, request, "limit_reached", "Activation limit reached")
        return {"activated": False, "reason": "limit_reached", "message": f"Activation limit ({limit}) reached.", "plan": "trial"}

    # Create activation
    await db.logi_activations.insert_one({
        "id": new_id(),
        "license_id": lic["id"],
        "fingerprint": payload.fingerprint,
        "hostname": payload.hostname or "",
        "ip": _client_ip(request),
        "user_agent": request.headers.get("user-agent", "")[:200],
        "activated_at": utc_now_iso(),
        "last_seen_at": utc_now_iso(),
        "last_ip": _client_ip(request),
    })
    await db.logi_licenses.update_one(
        {"id": lic["id"]},
        {"$set": {"activation_count": current + 1, "updated_at": utc_now_iso()}},
    )
    lic["activation_count"] = current + 1
    await _record_check(lic["id"], payload.license_key, payload.fingerprint, request, "valid", "Activated")
    return {"activated": True, "already_activated": False, **_license_public_view(lic)}


@router.post("/deactivate")
async def deactivate(payload: HeartbeatIn, request: Request):
    lic, err = await _resolve(payload.license_key)
    if err or not lic:
        return {"deactivated": False, "reason": err or "not_found"}
    db = get_db()
    r = await db.logi_activations.delete_one(
        {"license_id": lic["id"], "fingerprint": payload.fingerprint}
    )
    if r.deleted_count:
        current = int(lic.get("activation_count", 0))
        await db.logi_licenses.update_one(
            {"id": lic["id"]},
            {"$set": {"activation_count": max(0, current - 1), "updated_at": utc_now_iso()}},
        )
    await _record_check(lic["id"], payload.license_key, payload.fingerprint, request, "deactivated", "Client deactivated")
    return {"deactivated": bool(r.deleted_count)}


@router.post("/heartbeat")
async def heartbeat(payload: HeartbeatIn, request: Request):
    lic, err = await _resolve(payload.license_key)
    if err or not lic:
        return {"ok": False, "reason": err or "not_found"}
    db = get_db()
    await db.logi_activations.update_one(
        {"license_id": lic["id"], "fingerprint": payload.fingerprint},
        {"$set": {"last_seen_at": utc_now_iso(), "last_ip": _client_ip(request)}},
    )
    return {"ok": True, "at": utc_now_iso()}
