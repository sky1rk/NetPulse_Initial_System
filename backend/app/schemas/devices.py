"""Device schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDateTime


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: str
    mac_address: str | None = None
    hostname: str | None = None
    vendor: str | None = None
    first_seen: UtcDateTime
    last_seen: UtcDateTime
    created_at: UtcDateTime
    updated_at: UtcDateTime


class DeviceWithObservation(DeviceOut):
    latest_observation: str = "not_tested"
    latest_latency_ms: float | None = None
    latest_observation_at: UtcDateTime | None = None
    latest_packet_loss_percent: float | None = None


class DeviceListResponse(BaseModel):
    items: list[DeviceWithObservation] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class PingTestSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: UtcDateTime
    completed_at: UtcDateTime | None = None
    probes_sent: int
    probes_received: int
    packet_loss_percent: float | None = None
    avg_latency_ms: float | None = None
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    status: str


class MonitoringObservationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    observed_at: UtcDateTime
    icmp_success: bool
    latency_ms: float | None = None
    observation: str


class SecurityScanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: UtcDateTime
    completed_at: UtcDateTime | None = None
    profile_name: str
    status: str


class DeviceDetailResponse(DeviceWithObservation):
    recent_ping_tests: list[PingTestSummary] = Field(default_factory=list)
    recent_observations: list[MonitoringObservationSummary] = Field(default_factory=list)
    recent_security_scans: list[SecurityScanSummary] = Field(default_factory=list)
