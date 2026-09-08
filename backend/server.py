"""LogiSource Integrated System - Backend main app."""
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

import logging
import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from db import close_db, get_db, init_db
from routers.accounts import router as accounts_router
from routers.activity_logs import router as activity_router
from routers.auth_router import router as auth_router
from routers.customers import router as customers_router
from routers.dashboard import router as dashboard_router
from routers.invoices import router as invoices_router
from routers.licenses import router as licenses_router
from routers.logi_licenses import router as logi_licenses_router
from routers.products import router as products_router
from routers.projects import router as projects_router
from routers.public_license import router as public_license_router
from routers.quotations import router as quotations_router
from routers.settings import router as settings_router
from routers.users import router as users_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
logger = logging.getLogger("logisource")

app = FastAPI(title="LogiSource Integrated System")

# CORS
origins_env = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.on_event("startup")
async def _startup():
    await init_db()
    logger.info("LogiSource DB initialised — admin & staff seeded, indexes created")


@app.on_event("shutdown")
async def _shutdown():
    await close_db()


@app.get("/api/")
async def root():
    return {"app": "LogiSource Integrated System", "status": "ok"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


for r in (
    auth_router,
    customers_router,
    products_router,
    quotations_router,
    invoices_router,
    projects_router,
    accounts_router,
    licenses_router,
    logi_licenses_router,
    public_license_router,
    users_router,
    settings_router,
    activity_router,
    dashboard_router,
):
    app.include_router(r)
