"""Security assessment endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.schemas.security import (
    PortInfo,
    SecurityFindingOut,
    SecurityFindingsList,
    SecurityProfileOut,
    SecurityScanRequest,
    SecurityScanResponse,
    SecurityScanSummary,
)
from app.services import security_service

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/profiles", response_model=list[SecurityProfileOut])
def port_profiles() -> list[dict]:
    allowlist = set(settings.allowed_port_list)
    profiles = []
    for name, profile in security_service.PORT_PROFILES.items():
        profiles.append(
            {
                "name": name,
                "description": profile["description"],
                "ports": [
                    PortInfo(
                        port=port,
                        service_name=security_service.service_name(port) or "unknown",
                        note=(
                            "Conventional service label; the actual application is not verified."
                        ),
                    )
                    for port in profile["ports"]
                    if port in allowlist
                ],
            }
        )
    return profiles


@router.post("/scan", response_model=SecurityScanResponse)
def security_scan(payload: SecurityScanRequest, db: Session = Depends(get_db)) -> dict:
    scan, findings, warnings = security_service.run_security_scan(
        db,
        device_id=payload.device_id,
        requested_ports=payload.ports,
        profile_name=payload.profile_name,
        confirm_authorized=payload.confirm_authorized,
    )
    return {
        "scan_id": scan.id,
        "device_id": scan.device_id,
        "status": scan.status,
        "started_at": scan.started_at,
        "completed_at": scan.completed_at,
        "profile_name": scan.profile_name,
        "findings": [
            SecurityFindingOut(
                id=finding.id,
                port=finding.port,
                protocol=finding.protocol,
                state=finding.state,
                service_name=finding.service_name,
                severity=finding.severity,
                recommendation=finding.recommendation,
            )
            for finding in findings
        ],
        "warnings": warnings,
    }


@router.get("/findings", response_model=SecurityFindingsList)
def findings(
    device_id: int | None = Query(default=None),
    state: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    total, items = security_service.list_findings(
        db, device_id=device_id, state=state, limit=limit, offset=offset
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/scans", response_model=list[SecurityScanSummary])
def scans(
    device_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    return security_service.scan_summaries(db, device_id=device_id, limit=limit)
