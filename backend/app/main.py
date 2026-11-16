"""NetPulse FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api import websocket as websocket_routes
from app.api.routes import (
    analytics,
    dashboard,
    devices,
    diagnostics,
    health,
    monitoring,
    network,
    reports,
    security,
)
from app.core.config import settings
from app.core.logging import configure_logging
from app.database.session import SessionLocal, init_db
from app.services.errors import NetPulseError
from app.services.monitoring_service import monitoring_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger.info("Starting %s %s", settings.app_name, settings.app_version)
    init_db()
    with SessionLocal() as db:
        monitoring_manager.mark_stale_sessions(db)
    yield
    logger.info("Shutting down NetPulse backend")
    await monitoring_manager.shutdown()


app = FastAPI(
    title="NetPulse API",
    version=__version__,
    description=(
        "Local-first network monitoring, performance analytics and limited security assessment. "
        "Only test networks and devices you own or are authorized to assess."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(NetPulseError)
async def netpulse_error_handler(_: Request, exc: NetPulseError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "VALIDATION_ERROR",
                "message": "The request parameters failed validation.",
                "details": details,
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, str):
        content = {"detail": {"code": f"HTTP_{exc.status_code}", "message": detail}}
    else:
        content = {"detail": detail}
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected server error occurred. Review the backend log.",
            }
        },
    )


api_prefix = settings.api_prefix
app.include_router(health.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)
app.include_router(network.router, prefix=api_prefix)
app.include_router(devices.router, prefix=api_prefix)
app.include_router(monitoring.router, prefix=api_prefix)
app.include_router(analytics.router, prefix=api_prefix)
app.include_router(security.router, prefix=api_prefix)
app.include_router(diagnostics.router, prefix=api_prefix)
app.include_router(reports.router, prefix=api_prefix)
app.include_router(websocket_routes.router)


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{api_prefix}/health",
    }
