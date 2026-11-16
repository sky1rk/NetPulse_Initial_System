"""Device inventory and connectivity test endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.connectivity import PingProbeOut, PingRequest, PingTestResponse
from app.schemas.devices import DeviceDetailResponse, DeviceListResponse
from app.services import connectivity_service, devices_service

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=DeviceListResponse)
def list_devices(
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    total, items = devices_service.list_devices(
        db, status=status, search=search, limit=limit, offset=offset
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{device_id}", response_model=DeviceDetailResponse)
def device_detail(device_id: int, db: Session = Depends(get_db)) -> dict:
    return devices_service.get_device_detail(db, device_id)


@router.post("/{device_id}/ping", response_model=PingTestResponse)
def ping_device(device_id: int, payload: PingRequest, db: Session = Depends(get_db)) -> dict:
    device = devices_service.get_device_or_404(db, device_id)
    result = connectivity_service.execute_ping_test(
        db, device, count=payload.count, timeout_ms=payload.timeout_ms
    )
    test = result["test"]
    probes = [PingProbeOut.model_validate(probe) for probe in test.probes]
    return {
        "test_id": test.id,
        "device_id": test.device_id,
        "probes_sent": test.probes_sent,
        "probes_received": test.probes_received,
        "packet_loss_percent": test.packet_loss_percent,
        "avg_latency_ms": test.avg_latency_ms,
        "min_latency_ms": test.min_latency_ms,
        "max_latency_ms": test.max_latency_ms,
        "jitter_ms": result["jitter_ms"],
        "status": test.status,
        "started_at": test.started_at,
        "completed_at": test.completed_at,
        "probes": probes,
        "message": result["message"],
    }
