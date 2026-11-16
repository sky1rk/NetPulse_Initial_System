"""Network information, discovery and topology endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.network import (
    NetworkInfoResponse,
    ScanDeviceOut,
    ScanRequest,
    ScanResponse,
    TopologyResponse,
)
from app.services import discovery_service, network_info_service

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/info", response_model=NetworkInfoResponse)
def network_info() -> dict:
    return network_info_service.get_network_info()


@router.post("/scan", response_model=ScanResponse)
def scan_network(payload: ScanRequest, db: Session = Depends(get_db)) -> dict:
    scan, links, warnings = discovery_service.run_scan(
        db,
        requested_cidr=payload.network_cidr,
        confirm_authorized=payload.confirm_authorized,
    )
    devices = [
        ScanDeviceOut(
            id=device.id,
            ip_address=device.ip_address,
            mac_address=device.mac_address,
            hostname=device.hostname,
            observation=link.observation,
            last_seen=device.last_seen,
        )
        for link, device in links
    ]
    return {
        "scan_id": scan.id,
        "status": scan.status,
        "started_at": scan.started_at,
        "completed_at": scan.completed_at,
        "network_cidr": scan.network_cidr,
        "discovered_count": scan.discovered_count,
        "devices": devices,
        "warnings": warnings,
    }


@router.get("/topology", response_model=TopologyResponse)
def topology(db: Session = Depends(get_db)) -> dict:
    return discovery_service.build_topology(db)
