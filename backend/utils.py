"""Shared utility helpers: activity logging, auto-numbering, pagination."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from db import get_db


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def log_activity(user: dict, action: str, module: str, details: Optional[str] = None):
    db = get_db()
    await db.activity_logs.insert_one({
        "id": new_id(),
        "user_id": user.get("id"),
        "user_email": user.get("email"),
        "user_name": user.get("name"),
        "action": action,
        "module": module,
        "details": details or "",
        "timestamp": utc_now_iso(),
    })


async def next_number(prefix_kind: str) -> str:
    """Generate atomic monotonic doc numbers like QTN-2026-00001."""
    db = get_db()
    year = datetime.now(timezone.utc).year
    settings = await db.settings.find_one({"id": "global"}, {"_id": 0}) or {}
    prefix_map = {
        "quotation": settings.get("quotation_prefix", "QTN"),
        "invoice": settings.get("invoice_prefix", "INV"),
        "project": settings.get("project_prefix", "PRJ"),
    }
    prefix = prefix_map.get(prefix_kind, prefix_kind.upper()[:3])
    key = f"{prefix_kind}:{year}"
    doc = await db.counters.find_one_and_update(
        {"key": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = doc["seq"] if doc else 1
    return f"{prefix}-{year}-{seq:05d}"


async def next_customer_code() -> str:
    db = get_db()
    year = datetime.now(timezone.utc).year
    key = f"customer:{year}"
    doc = await db.counters.find_one_and_update(
        {"key": key}, {"$inc": {"seq": 1}}, upsert=True, return_document=True,
    )
    seq = doc["seq"] if doc else 1
    return f"CUS-{year}-{seq:04d}"


async def next_product_code(kind: str = "goods") -> str:
    db = get_db()
    prefix = "PRD" if kind == "goods" else "SRV"
    key = f"product:{prefix}"
    doc = await db.counters.find_one_and_update(
        {"key": key}, {"$inc": {"seq": 1}}, upsert=True, return_document=True,
    )
    seq = doc["seq"] if doc else 1
    return f"{prefix}-{seq:04d}"


def paginate(items: list, page: int, per_page: int) -> dict:
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }
