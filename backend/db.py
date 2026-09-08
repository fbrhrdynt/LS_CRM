"""MongoDB connection, indexes and admin seed."""
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

_client: AsyncIOMotorClient | None = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        _db = _client[os.environ["DB_NAME"]]
    return _db


async def close_db():
    global _client
    if _client:
        _client.close()


async def init_db():
    """Create indexes and seed default admin/staff users."""
    from auth import hash_password  # local import to avoid cycles

    db = get_db()
    # Indexes
    await db.users.create_index("email", unique=True)
    await db.customers.create_index("code", unique=True)
    await db.products.create_index("code", unique=True)
    await db.quotations.create_index("number", unique=True)
    await db.invoices.create_index("number", unique=True)
    await db.projects.create_index("number", unique=True)
    await db.activity_logs.create_index([("timestamp", -1)])
    await db.logi_licenses.create_index("license_key", unique=True)
    await db.logi_activations.create_index([("license_id", 1), ("fingerprint", 1)], unique=True)
    await db.logi_checks.create_index([("license_id", 1), ("timestamp", -1)])
    await db.auth_sessions.create_index("jti", unique=True)
    await db.auth_sessions.create_index("user_id")
    await db.auth_sessions.create_index("expires_at", expireAfterSeconds=0)
    await db.rate_limits.create_index("key", unique=True)
    await db.rate_limits.create_index("expires_at", expireAfterSeconds=0)

    # Seed admin
    admin_email = os.environ["ADMIN_EMAIL"].lower()
    now = datetime.now(timezone.utc).isoformat()
    admin = await db.users.find_one({"email": admin_email})
    if not admin:
        # Production may already have an administrator whose email differs
        # from the original seed email. Do not require/reseed credentials.
        admin = await db.users.find_one({"role": "admin"})
    if not admin:
        admin_password = os.environ.get("ADMIN_PASSWORD", "")
        if len(admin_password) < 12:
            raise RuntimeError("ADMIN_PASSWORD must be at least 12 characters when seeding admin")
        await db.users.insert_one({
            "id": "user-admin-seed",
            "name": "Administrator",
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "role": "admin",
            "created_at": now,
            "updated_at": now,
        })

    # Seed staff
    staff_email = os.environ["STAFF_EMAIL"].lower()
    staff = await db.users.find_one({"email": staff_email})
    if not staff:
        # Same rule for an existing staff account.
        staff = await db.users.find_one({"role": "staff"})
    if not staff:
        staff_password = os.environ.get("STAFF_PASSWORD", "")
        if len(staff_password) < 12:
            raise RuntimeError("STAFF_PASSWORD must be at least 12 characters when seeding staff")
        await db.users.insert_one({
            "id": "user-staff-seed",
            "name": "Staff User",
            "email": staff_email,
            "password_hash": hash_password(staff_password),
            "role": "staff",
            "created_at": now,
            "updated_at": now,
        })

    # Seed default settings if absent
    settings = await db.settings.find_one({"id": "global"})
    if not settings:
        await db.settings.insert_one({
            "id": "global",
            "company_name": os.environ.get("COMPANY_NAME", "LogiSource Digital"),
            "company_tagline": os.environ.get("COMPANY_TAGLINE", "Digital. Reliable. Connected."),
            "company_logo_url": os.environ.get("COMPANY_LOGO_URL", ""),
            "company_email": "info@logisource.com",
            "company_phone": "+62-000-000-0000",
            "company_address": "Jakarta, Indonesia",
            "currency": "IDR",
            "tax_percent": 11.0,
            "quotation_prefix": "QTN",
            "invoice_prefix": "INV",
            "project_prefix": "PRJ",
            "updated_at": now,
        })
