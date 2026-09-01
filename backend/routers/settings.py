import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response

from auth import get_current_user, require_admin
from db import get_db
from installation_pdf import build_installation_pdf
from models import SettingsUpdate
from utils import log_activity, utc_now_iso

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/installation-guide/pdf")
async def installation_guide_pdf(user: dict = Depends(get_current_user)):
    """LogiSource installation & deployment tutorial PDF (local PC + hosting)."""
    db = get_db()
    settings = await db.settings.find_one({"id": "global"}, {"_id": 0}) or {}
    content = build_installation_pdf(settings)
    await log_activity(user, "export_pdf", "settings", "Downloaded installation guide")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="LogiSource-Installation-Guide.pdf"'},
    )


@router.get("")
async def get_settings(user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.settings.find_one({"id": "global"}, {"_id": 0}) or {}
    return doc


@router.put("")
async def update_settings(payload: SettingsUpdate, admin: dict = Depends(require_admin)):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = utc_now_iso()
    await db.settings.update_one({"id": "global"}, {"$set": updates}, upsert=True)
    await log_activity(admin, "update", "settings", "Company settings updated")
    doc = await db.settings.find_one({"id": "global"}, {"_id": 0})
    return doc


@router.get("/backup")
async def backup(admin: dict = Depends(require_admin)):
    """Export ALL collections as a single JSON file."""
    db = get_db()
    collections = ["users", "customers", "products", "product_categories", "quotations",
                   "invoices", "projects", "accounts", "licenses", "settings",
                   "activity_logs", "counters"]
    out = {"exported_at": datetime.now(timezone.utc).isoformat(), "collections": {}}
    for c in collections:
        docs = await db[c].find({}, {"_id": 0}).to_list(100000)
        out["collections"][c] = docs
    content = json.dumps(out, indent=2, default=str).encode("utf-8")
    await log_activity(admin, "backup", "settings", "Database backup exported")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="logisource-backup-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}.json"'},
    )


@router.post("/restore")
async def restore(file: UploadFile = File(...), admin: dict = Depends(require_admin)):
    content = await file.read()
    try:
        data = json.loads(content.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid backup file: {e}")
    if "collections" not in data:
        raise HTTPException(status_code=400, detail="Missing 'collections' in backup")
    db = get_db()
    restored = {}
    for cname, docs in data["collections"].items():
        # never overwrite users collection wholesale to avoid losing admin
        if cname == "users":
            continue
        await db[cname].delete_many({})
        if docs:
            await db[cname].insert_many(docs)
        restored[cname] = len(docs)
    await log_activity(admin, "restore", "settings", f"Restored {sum(restored.values())} documents")
    return {"restored": restored}


@router.get("/full-export")
async def full_export(include_build: bool = False, admin: dict = Depends(require_admin)):
    """Bundle backend + frontend source + MongoDB dump + memory files → single ZIP.

    Skips: node_modules, __pycache__, .git, build artefacts, .venv.
    If `include_build=true`, runs `yarn build` on the frontend first and includes
    `frontend/build/` (production static bundle, ready for Netlify/S3/nginx).
    Returns application/zip. Administrator only.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    workdir = Path(tempfile.mkdtemp(prefix="logisource_export_"))
    build_warning = None
    try:
        # 0. Optional: build the frontend so we can include the compiled static bundle
        if include_build:
            try:
                subprocess.run(
                    ["yarn", "build"],
                    cwd="/app/frontend",
                    check=True, capture_output=True, timeout=240,
                    env={**os.environ, "CI": "false", "GENERATE_SOURCEMAP": "false"},
                )
            except subprocess.CalledProcessError as e:
                build_warning = f"yarn build failed: {e.stderr.decode('utf-8', 'ignore')[-500:]}"
            except subprocess.TimeoutExpired:
                build_warning = "yarn build timed out after 240s"
            except FileNotFoundError:
                build_warning = "yarn not found in PATH"

        # 1. Dump MongoDB
        dump_dir = workdir / "database"
        dump_dir.mkdir(parents=True, exist_ok=True)
        mongo_url = os.environ["MONGO_URL"]
        db_name = os.environ["DB_NAME"]
        try:
            subprocess.run(
                ["mongodump", "--uri", mongo_url, "--db", db_name, "--out", str(dump_dir)],
                check=True, capture_output=True, timeout=90,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # Fallback: JSON dump using our own backup logic
            db = get_db()
            collections = [
                "users", "customers", "products", "product_categories", "quotations",
                "invoices", "projects", "accounts", "licenses", "settings",
                "activity_logs", "counters", "logi_licenses", "logi_activations", "logi_checks",
            ]
            fallback = {"exported_at": utc_now_iso(), "collections": {}}
            for c in collections:
                docs = await db[c].find({}, {"_id": 0}).to_list(200000)
                fallback["collections"][c] = docs
            (dump_dir / f"{db_name}-fallback.json").write_text(json.dumps(fallback, indent=2, default=str))

        # 2. Copy source code, skipping heavy / secret artefacts
        skip_dirs = {"node_modules", "__pycache__", ".git", ".venv", "build", "dist", ".next", ".cache", ".pytest_cache", ".yarn"}
        skip_files = {".DS_Store"}

        def _copy_tree(src: Path, dst: Path, prune_default: bool = True):
            if not src.exists():
                return
            for root, dirs, files in os.walk(src):
                if prune_default:
                    dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
                rel = Path(root).relative_to(src)
                target_root = dst / rel
                target_root.mkdir(parents=True, exist_ok=True)
                for f in files:
                    if f in skip_files:
                        continue
                    if f.endswith((".pyc", ".log")):
                        continue
                    try:
                        shutil.copy2(Path(root) / f, target_root / f)
                    except Exception:
                        pass

        _copy_tree(Path("/app/backend"), workdir / "backend")
        _copy_tree(Path("/app/frontend"), workdir / "frontend")
        _copy_tree(Path("/app/memory"), workdir / "memory")
        _copy_tree(Path("/app/backend/tests"), workdir / "backend" / "tests")

        # 2c. Always embed the Installation Guide PDF into the ZIP root
        try:
            db = get_db()
            settings_doc = await db.settings.find_one({"id": "global"}, {"_id": 0}) or {}
            install_pdf = build_installation_pdf(settings_doc)
            (workdir / "LogiSource-Installation-Guide.pdf").write_bytes(install_pdf)
        except Exception:
            pass  # non-fatal — README still has the essentials

        # 2b. Copy compiled build if requested (and it exists)
        build_size_kb = 0
        if include_build and not build_warning:
            build_src = Path("/app/frontend/build")
            if build_src.exists():
                build_dst = workdir / "frontend" / "build"
                _copy_tree(build_src, build_dst, prune_default=False)  # keep static/ etc.
                # size
                for root, _, files in os.walk(build_dst):
                    for f in files:
                        build_size_kb += (Path(root) / f).stat().st_size // 1024
            else:
                build_warning = "frontend/build directory not found after yarn build"

        # 3. README with restore instructions
        build_section = ""
        if include_build:
            if build_warning:
                build_section = f"""
## Production build

Requested but NOT included — reason: {build_warning}

To build manually inside `frontend/`:
```bash
cd frontend
yarn install
yarn build
```
The compiled static bundle will appear in `frontend/build/`.
"""
            else:
                build_section = f"""
## Production build (`frontend/build/`)

A pre-built static bundle is included ({build_size_kb} KB). Deploy directly to any
static host — Netlify, Vercel, S3+CloudFront, or plain nginx.

**Important:** the bundle was built with
`REACT_APP_BACKEND_URL={os.environ.get("REACT_APP_BACKEND_URL", "(from .env)")}`.
If your backend runs on a different domain, rebuild with the correct value:

```bash
cd frontend
REACT_APP_BACKEND_URL=https://your-backend.com yarn build
```

### nginx example
```
server {{
  listen 80;
  root /var/www/logisource/build;
  location / {{ try_files $uri /index.html; }}
  location /api/ {{ proxy_pass http://backend:8001; }}
}}
```
"""

        readme = f"""# LogiSource Integrated System — Full Export

Exported: {datetime.now(timezone.utc).isoformat()}
By:       {admin.get("email")}
Build:    {"included" if include_build and not build_warning else "not included"}

## Contents
- `backend/`         — FastAPI Python source + `.env` (rotate secrets before production!)
- `frontend/`        — React app source (run `yarn install` to restore node_modules)
{"- `frontend/build/`  — Pre-built static bundle ready for static hosting" if include_build and not build_warning else ""}
- `database/`        — MongoDB dump (BSON via mongodump, or JSON fallback if mongodump unavailable)
- `memory/`          — PRD.md, test_credentials.md

## Restore locally

### 1. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Ensure MongoDB is running locally, then:
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### 2. Frontend (dev)
```bash
cd frontend
yarn install
yarn start          # runs on http://localhost:3000
```

### 3. Database restore
If you have BSON dump:
```bash
mongorestore --uri "mongodb://localhost:27017" --db {db_name} database/{db_name}
```
Otherwise use the JSON fallback via the app: log in as admin → Website Settings → Restore.
{build_section}
## Security reminder
`backend/.env` contains JWT_SECRET, VAULT_MASTER_KEY, ADMIN_PASSWORD in cleartext.
ROTATE these before deploying to a public host.

## Seed credentials
- Admin: admin@logisource.com / Admin@12345
- Staff: staff@logisource.com / Staff@12345
"""
        (workdir / "README.md").write_text(readme)

        # 4. Zip
        zip_path = Path(tempfile.mkdtemp(prefix="logisource_zip_")) / f"logisource-full-{ts}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for root, dirs, files in os.walk(workdir):
                for f in files:
                    p = Path(root) / f
                    arcname = p.relative_to(workdir)
                    z.write(p, arcname=arcname)

        content = zip_path.read_bytes()
        size_kb = len(content) // 1024
        note = " (with build)" if include_build and not build_warning else ""
        await log_activity(admin, "full_export", "settings", f"Full export{note} {size_kb} KB")

        headers = {
            "Content-Disposition": f'attachment; filename="logisource-full-{ts}.zip"',
            "X-Export-Size-KB": str(size_kb),
            "X-Include-Build": "1" if include_build and not build_warning else "0",
        }
        if build_warning:
            headers["X-Build-Warning"] = build_warning[:200]
        return Response(content=content, media_type="application/zip", headers=headers)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
