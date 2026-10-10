"""Public AMT update-check endpoint tied to LogiLicense."""
import re
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from db import get_db
from utils import new_id, utc_now_iso


router = APIRouter(
    prefix="/api/public/update",
    tags=["public-update"],
)

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?$"
)


class UpdateCheckIn(BaseModel):
    license_key: str
    fingerprint: str
    product_slug: str
    current_version: str
    channel: Literal[
        "dev",
        "beta",
        "stable",
    ] = "stable"


def parse_semver(value: str):
    match = SEMVER_RE.fullmatch(
        str(value or "").strip()
    )
    if not match:
        return None

    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
        1 if match.group(4) is None else 0,
        match.group(4) or "",
    )


def days_left(iso_date: str) -> Optional[int]:
    if not iso_date:
        return None

    try:
        end = datetime.fromisoformat(
            iso_date.replace(
                "Z",
                "+00:00",
            )
        )
        if end.tzinfo is None:
            end = end.replace(
                tzinfo=timezone.utc
            )

        return (
            end
            - datetime.now(
                timezone.utc
            )
        ).days
    except Exception:
        return None


def client_ip(request: Request) -> str:
    forwarded = request.headers.get(
        "x-forwarded-for",
        "",
    )
    if forwarded:
        return forwarded.split(
            ","
        )[0].strip()

    return (
        request.client.host
        if request.client
        else ""
    )


async def record_check(
    payload: UpdateCheckIn,
    request: Request,
    result: str,
    latest_version: str = "",
    message: str = "",
):
    db = get_db()

    await db.amt_update_checks.insert_one(
        {
            "id": new_id(),
            "key_prefix": (
                payload.license_key
                or ""
            )[:9],
            "fingerprint": (
                payload.fingerprint
                or ""
            ),
            "product_slug": (
                payload.product_slug
                or ""
            ),
            "channel": (
                payload.channel
            ),
            "current_version": (
                payload.current_version
            ),
            "latest_version": (
                latest_version
            ),
            "result": result,
            "message": message,
            "ip": client_ip(
                request
            ),
            "timestamp": utc_now_iso(),
        }
    )


async def resolve_license(
    payload: UpdateCheckIn,
):
    db = get_db()

    lic = await db.logi_licenses.find_one(
        {
            "license_key": (
                payload.license_key.strip()
            )
        },
        {"_id": 0},
    )

    if not lic:
        return None, "invalid_key"

    if (
        lic.get("product_slug")
        and lic.get("product_slug")
        != payload.product_slug
    ):
        return lic, "product_mismatch"

    if lic.get("status") != "active":
        return (
            lic,
            lic.get("status")
            or "inactive",
        )

    remaining = days_left(
        lic.get(
            "expiry_date",
            "",
        )
    )
    if (
        remaining is not None
        and remaining < 0
    ):
        return lic, "expired"

    activation = (
        await db.logi_activations.find_one(
            {
                "license_id": lic["id"],
                "fingerprint": (
                    payload.fingerprint
                ),
            },
            {
                "_id": 0,
                "id": 1,
            },
        )
    )

    if not activation:
        return (
            lic,
            "activation_required",
        )

    if "update_version" not in set(
        lic.get("features")
        or []
    ):
        return (
            lic,
            "feature_not_enabled",
        )

    await db.logi_activations.update_one(
        {"id": activation["id"]},
        {
            "$set": {
                "last_seen_at": utc_now_iso(),
            }
        },
    )

    return lic, None


@router.post("/check")
async def check_update(
    payload: UpdateCheckIn,
    request: Request,
):
    current_key = parse_semver(
        payload.current_version
    )
    if current_key is None:
        await record_check(
            payload,
            request,
            "invalid_current_version",
            message=(
                "Current version is not valid semantic version"
            ),
        )
        return {
            "update_available": False,
            "reason": (
                "invalid_current_version"
            ),
            "message": (
                "Current version must use semantic versioning"
            ),
        }

    license_doc, license_error = (
        await resolve_license(
            payload
        )
    )

    if license_error:
        await record_check(
            payload,
            request,
            license_error,
            message=(
                "License is not entitled "
                "to product updates"
            ),
        )
        return {
            "update_available": False,
            "reason": license_error,
            "message": (
                "Product updates are not available "
                "for this license/device"
            ),
        }

    db = get_db()

    releases = (
        await db.amt_releases.find(
            {
                "product_slug": (
                    payload.product_slug
                ),
                "channel": (
                    payload.channel
                ),
                "status": "published",
            },
            {"_id": 0},
        )
        .to_list(1000)
    )

    valid_releases = []

    for release in releases:
        key = parse_semver(
            release.get(
                "version",
                "",
            )
        )
        if key is not None:
            valid_releases.append(
                (key, release)
            )

    valid_releases.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    if not valid_releases:
        await record_check(
            payload,
            request,
            "no_release",
        )
        return {
            "update_available": False,
            "current_version": (
                payload.current_version
            ),
            "latest_version": (
                payload.current_version
            ),
            "channel": payload.channel,
        }

    latest_key, latest = (
        valid_releases[0]
    )

    if latest_key <= current_key:
        await record_check(
            payload,
            request,
            "up_to_date",
            latest_version=(
                latest["version"]
            ),
        )
        return {
            "update_available": False,
            "current_version": (
                payload.current_version
            ),
            "latest_version": (
                latest["version"]
            ),
            "channel": payload.channel,
        }

    minimum = (
        latest.get(
            "min_supported_version"
        )
        or ""
    )
    minimum_key = (
        parse_semver(minimum)
        if minimum
        else None
    )

    if (
        minimum_key is not None
        and current_key
        < minimum_key
    ):
        await record_check(
            payload,
            request,
            "manual_upgrade_required",
            latest_version=(
                latest["version"]
            ),
            message=(
                "Installed version is older than "
                "the minimum supported update source"
            ),
        )
        return {
            "update_available": True,
            "automatic_update_allowed": False,
            "requires_manual_upgrade": True,
            "current_version": (
                payload.current_version
            ),
            "latest_version": (
                latest["version"]
            ),
            "min_supported_version": (
                minimum
            ),
            "channel": payload.channel,
            "title": latest.get(
                "title"
            ),
            "release_notes": (
                latest.get(
                    "release_notes"
                )
            ),
            "mandatory": bool(
                latest.get(
                    "mandatory"
                )
            ),
        }

    await record_check(
        payload,
        request,
        "update_available",
        latest_version=(
            latest["version"]
        ),
    )

    return {
        "update_available": True,
        "automatic_update_allowed": True,
        "requires_manual_upgrade": False,
        "current_version": (
            payload.current_version
        ),
        "latest_version": (
            latest["version"]
        ),
        "channel": (
            payload.channel
        ),
        "title": (
            latest.get("title")
        ),
        "release_notes": (
            latest.get(
                "release_notes"
            )
        ),
        "mandatory": bool(
            latest.get(
                "mandatory"
            )
        ),
        "has_database_migration": bool(
            latest.get(
                "has_database_migration"
            )
        ),
        "requires_restart": bool(
            latest.get(
                "requires_restart",
                True,
            )
        ),
        "package_url": (
            latest.get(
                "package_url"
            )
        ),
        "sha256": (
            latest.get("sha256")
        ),
        "signature": (
            latest.get(
                "signature"
            )
        ),
    }
