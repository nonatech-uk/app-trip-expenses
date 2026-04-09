"""Trip Expenses API — FastAPI application."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.api.deps import close_pool, init_pool
from src.api.routers import balances, expenses, ingest, members, settlements, share, trips

from mees_shared.usage_tracker import init_usage_tracker, shutdown_usage_tracker, track_usage_middleware, usage_pageview_router
from mees_shared.dashboard import register_with_dashboard
from mees_shared.spa import mount_spa

STATIC_DIR = Path(_project_root) / "static"

_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    init_usage_tracker("trips", settings.usage_dsn)
    task = asyncio.create_task(register_with_dashboard(
        label="Trips",
        href="https://trips.mees.st",
        icon="\u2708",
        sort_order=8,
        registry_key=settings.dash_registry_key,
    ))
    yield
    task.cancel()
    shutdown_usage_tracker()
    close_pool()


app = FastAPI(
    title="Trip Expenses API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(track_usage_middleware)

# Authenticated routes
app.include_router(trips.router, prefix="/api/v1", tags=["trips"])
app.include_router(members.router, prefix="/api/v1", tags=["members"])
app.include_router(expenses.router, prefix="/api/v1", tags=["expenses"])
app.include_router(settlements.router, prefix="/api/v1", tags=["settlements"])
app.include_router(balances.router, prefix="/api/v1", tags=["balances"])

# Public routes (no auth)
app.include_router(share.router, prefix="/api/v1", tags=["share"])
app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])

app.include_router(usage_pageview_router, prefix="/api/v1")

# SPA serving + /health endpoint
mount_spa(app, STATIC_DIR)
