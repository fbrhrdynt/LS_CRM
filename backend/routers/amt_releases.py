"""AMT release management for LogiSource CRM."""
import re
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from auth import get_current_user, require_admin, require_permission
from db import get_db
from utils import log_activity, new_id, paginate, utc_now_iso


router = APIRouter(
    prefix="/api/amt-releases",
    tags=["amt-releases"],
    dependencies=[
        Depends(require_permission("amt_releases"))
    ],
)

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?$"
)

CHANNELS = {"dev", "beta", "stable"}
STATUSES = {"draft", "testing", "published", "revoked"}


class AMTReleaseBase(BaseModel):
    product_slug: str = "ls-amt-baroid-uae"
    version: str
    channel: Literal["dev", "beta", "stable"] = "stable"
    title: str
    release_notes: str = ""
    package_url: str = ""
    sha256: str = ""
    signature: str = ""
    min_supported_version: str = ""
    mandatory: bool = False
    has_database_migration: bool = False
    requires_restart: bool = True


class AMTReleaseCreate(AMTReleaseBase):
    status: Literal[
        "draft",
        "testing",
        "published",
        "revoked",
    ] = "draft"


class AMTReleaseUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    product_slug: Optional[str] = None
    version: Optional[str] = None
    channel: Optional[
        Literal["dev", "beta", "stable"]
    ] = None
    title: Optional[str] = None
    release_notes: Optional[str] = None
    package_url: Optional[str] = None
    sha256: Optional[str] = None
    signature: Optional[str] = None
    min_supported_version: Optional[str] = None
    mandatory: Optional[bool] = None
    has_database_migration: Optional[bool] = None
    requires_restart: Optional[bool] = None


def parse_semver(value: str) -> tuple:
    value = str(value or "").strip()
    match = SEMVER_RE.fullmatch(value)
    if not match:
        raise HTTPException(
            status_code=400,
            detail=(
                "Version must use semantic versioning, "
                "for example 1.2.0 or 1.2.0-beta.1"
            ),
        )

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    pre = match.group(4)

    return (
        major,
        minor,
        patch,
        1 if pre is None else 0,
        pre or "",
    )


def clean_release_values(values: dict) -> dict:
    result = dict(values)

    for key in (
        "product_slug",
        "version",
        "channel",
        "title",
        "release_notes",
        "package_url",
        "sha256",
        "signature",
        "min_supported_version",
    ):
        if key in result and isinstance(
            result[key],
            str,
        ):
            result[key] = result[key].strip()

    if "version" in result:
        parse_semver(result["version"])

    if result.get("min_supported_version"):
        parse_semver(
            result["min_supported_version"]
        )

    if "product_slug" in result and not result["product_slug"]:
        raise HTTPException(
            status_code=400,
            detail="Product slug is required",
        )

    if "title" in result and not result["title"]:
        raise HTTPException(
            status_code=400,
            detail="Release title is required",
        )

    if "sha256" in result and result["sha256"]:
        digest = result["sha256"].lower()
        if not re.fullmatch(
            r"[0-9a-f]{64}",
            digest,
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "SHA256 must contain exactly "
                    "64 hexadecimal characters"
                ),
            )
        result["sha256"] = digest

    if "package_url" in result and result["package_url"]:
        if not result["package_url"].startswith(
            "https://"
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Package URL must use HTTPS"
                ),
            )

    return result


async def ensure_unique_release(
    values: dict,
    exclude_id: str = "",
):
    db = get_db()

    query = {
        "product_slug": values["product_slug"],
        "version": values["version"],
        "channel": values["channel"],
    }

    if exclude_id:
        query["id"] = {
            "$ne": exclude_id
        }

    if await db.amt_releases.find_one(
        query,
        {"_id": 0, "id": 1},
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "A release with the same product, "
                "version and channel already exists"
            ),
        )


def validate_publishable(doc: dict):
    missing = []

    for key in (
        "package_url",
        "sha256",
        "signature",
    ):
        if not doc.get(key):
            missing.append(key)

    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot publish release. Missing: "
                + ", ".join(missing)
            ),
        )


@router.get("")
async def list_releases(
    q: str = "",
    product_slug: str = "",
    channel: str = "",
    status: str = "",
    page: int = 1,
    per_page: int = 20,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    query: dict = {}

    if q:
        rx = {
            "$regex": re.escape(q[:100]),
            "$options": "i",
        }
        query["$or"] = [
            {"version": rx},
            {"title": rx},
            {"product_slug": rx},
            {"release_notes": rx},
        ]

    if product_slug:
        query["product_slug"] = (
            product_slug
        )

    if channel:
        if channel not in CHANNELS:
            raise HTTPException(
                status_code=400,
                detail="Invalid channel",
            )
        query["channel"] = channel

    if status:
        if status not in STATUSES:
            raise HTTPException(
                status_code=400,
                detail="Invalid status",
            )
        query["status"] = status

    docs = await db.amt_releases.find(
        query,
        {"_id": 0},
    ).sort(
        "created_at",
        -1,
    ).to_list(10000)

    docs.sort(
        key=lambda item: parse_semver(
            item.get("version", "0.0.0")
        ),
        reverse=True,
    )

    return paginate(
        docs,
        page,
        per_page,
    )


@router.get("/{release_id}")
async def get_release(
    release_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    doc = await db.amt_releases.find_one(
        {"id": release_id},
        {"_id": 0},
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Release not found",
        )

    return doc


@router.post("")
async def create_release(
    payload: AMTReleaseCreate,
    user: dict = Depends(require_admin),
):
    db = get_db()
    values = clean_release_values(
        payload.model_dump()
    )

    status = values.pop(
        "status",
        "draft",
    )

    if status == "published":
        validate_publishable(values)

    await ensure_unique_release(
        values
    )

    now = utc_now_iso()
    doc = {
        **values,
        "id": new_id(),
        "status": status,
        "created_at": now,
        "updated_at": now,
        "created_by": user["id"],
        "published_at": (
            now
            if status == "published"
            else ""
        ),
        "published_by": (
            user["id"]
            if status == "published"
            else ""
        ),
    }

    await db.amt_releases.insert_one(
        doc
    )
    doc.pop("_id", None)

    await log_activity(
        user,
        "create",
        "amt-releases",
        (
            f"{doc['product_slug']} "
            f"{doc['version']} "
            f"[{doc['channel']}]"
        ),
    )

    return doc


@router.put("/{release_id}")
async def update_release(
    release_id: str,
    payload: AMTReleaseUpdate,
    user: dict = Depends(require_admin),
):
    db = get_db()

    current = await db.amt_releases.find_one(
        {"id": release_id},
        {"_id": 0},
    )
    if not current:
        raise HTTPException(
            status_code=404,
            detail="Release not found",
        )

    if current.get("status") == "published":
        raise HTTPException(
            status_code=400,
            detail=(
                "Published releases are immutable. "
                "Revoke it and create a new version."
            ),
        )

    updates = {
        key: value
        for key, value
        in payload.model_dump().items()
        if value is not None
    }

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No fields to update",
        )

    merged = {
        **current,
        **updates,
    }
    merged = clean_release_values(
        merged
    )

    await ensure_unique_release(
        merged,
        exclude_id=release_id,
    )

    allowed_fields = {
        "product_slug",
        "version",
        "channel",
        "title",
        "release_notes",
        "package_url",
        "sha256",
        "signature",
        "min_supported_version",
        "mandatory",
        "has_database_migration",
        "requires_restart",
    }

    safe_updates = {
        key: merged[key]
        for key in allowed_fields
        if key in updates
    }
    safe_updates["updated_at"] = (
        utc_now_iso()
    )

    await db.amt_releases.update_one(
        {"id": release_id},
        {"$set": safe_updates},
    )

    doc = await db.amt_releases.find_one(
        {"id": release_id},
        {"_id": 0},
    )

    await log_activity(
        user,
        "update",
        "amt-releases",
        (
            f"{doc['product_slug']} "
            f"{doc['version']} "
            f"[{doc['channel']}]"
        ),
    )

    return doc


@router.post("/{release_id}/publish")
async def publish_release(
    release_id: str,
    user: dict = Depends(require_admin),
):
    db = get_db()

    doc = await db.amt_releases.find_one(
        {"id": release_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Release not found",
        )

    if doc.get("status") == "revoked":
        raise HTTPException(
            status_code=400,
            detail=(
                "Revoked release cannot be published"
            ),
        )

    validate_publishable(doc)

    now = utc_now_iso()

    await db.amt_releases.update_one(
        {"id": release_id},
        {
            "$set": {
                "status": "published",
                "published_at": now,
                "published_by": user["id"],
                "updated_at": now,
            }
        },
    )

    await log_activity(
        user,
        "publish",
        "amt-releases",
        (
            f"{doc['product_slug']} "
            f"{doc['version']} "
            f"[{doc['channel']}]"
        ),
    )

    return await db.amt_releases.find_one(
        {"id": release_id},
        {"_id": 0},
    )


@router.post("/{release_id}/revoke")
async def revoke_release(
    release_id: str,
    user: dict = Depends(require_admin),
):
    db = get_db()

    doc = await db.amt_releases.find_one(
        {"id": release_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Release not found",
        )

    now = utc_now_iso()

    await db.amt_releases.update_one(
        {"id": release_id},
        {
            "$set": {
                "status": "revoked",
                "revoked_at": now,
                "revoked_by": user["id"],
                "updated_at": now,
            }
        },
    )

    await log_activity(
        user,
        "revoke",
        "amt-releases",
        (
            f"{doc['product_slug']} "
            f"{doc['version']} "
            f"[{doc['channel']}]"
        ),
    )

    return await db.amt_releases.find_one(
        {"id": release_id},
        {"_id": 0},
    )


@router.delete("/{release_id}")
async def delete_release(
    release_id: str,
    user: dict = Depends(require_admin),
):
    db = get_db()

    doc = await db.amt_releases.find_one(
        {"id": release_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Release not found",
        )

    if doc.get("status") in {
        "published",
        "revoked",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Published/revoked releases are retained "
                "for release audit history"
            ),
        )

    await db.amt_releases.delete_one(
        {"id": release_id}
    )

    await log_activity(
        user,
        "delete",
        "amt-releases",
        (
            f"{doc['product_slug']} "
            f"{doc['version']} "
            f"[{doc['channel']}]"
        ),
    )

    return {"message": "deleted"}
