"""Security assessment schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import UtcDateTime


class PortInfo(BaseModel):
    port: int
    service_name: str
    note: str | None = None


class SecurityProfileOut(BaseModel):
    name: str
    description: str
    ports: list[PortInfo]


class SecurityScanRequest(BaseModel):
    device_id: int
    ports: list[int] | None = Field(
        default=None,
        description="Ports to check. Must be a subset of the configured allowlist.",
    )
    profile_name: str | None = None
    confirm_authorized: bool = False


class SecurityFindingOut(BaseModel):
    id: int | None = None
    port: int
    protocol: str = "tcp"
    state: str
    service_name: str | None = None
    severity: str
    recommendation: str | None = None


class SecurityScanResponse(BaseModel):
    scan_id: int
    device_id: int
    status: str
    started_at: UtcDateTime
    completed_at: UtcDateTime | None = None
    profile_name: str
    findings: list[SecurityFindingOut] = Field(default_factory=list)
    disclaimer: str = "An open port is an observation, not proof of a vulnerability."
    warnings: list[str] = Field(default_factory=list)


class SecurityFindingRecord(SecurityFindingOut):
    id: int
    scan_id: int
    device_id: int
    device_ip: str
    scanned_at: UtcDateTime
    scan_status: str


class SecurityFindingsList(BaseModel):
    items: list[SecurityFindingRecord] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    disclaimer: str = "An open port is an observation, not proof of a vulnerability."


class SecurityScanSummary(BaseModel):
    scan_id: int
    device_id: int
    device_ip: str
    status: str
    profile_name: str
    started_at: UtcDateTime
    completed_at: UtcDateTime | None = None
    open_port_count: int = 0
    tested_port_count: int = 0
