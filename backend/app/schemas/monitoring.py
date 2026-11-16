"""Monitoring schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDateTime


class MonitoringStartRequest(BaseModel):
    device_ids: list[int] = Field(min_length=1, max_length=25)
    interval_seconds: int = Field(default=10, ge=1, le=86400)


class MonitoringStopResponse(BaseModel):
    session_id: int
    status: str
    started_at: UtcDateTime
    ended_at: UtcDateTime | None = None


class MonitoringObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    device_id: int
    observed_at: UtcDateTime
    icmp_success: bool
    latency_ms: float | None = None
    observation: str


class MonitoringSessionOut(BaseModel):
    session_id: int
    status: str
    interval_seconds: int
    started_at: UtcDateTime
    ended_at: UtcDateTime | None = None
    device_ids: list[int] = Field(default_factory=list)
    observation_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    availability_percent: float | None = None
    latest_observation_at: UtcDateTime | None = None


class MonitoringSessionDetail(MonitoringSessionOut):
    observations: list[MonitoringObservationOut] = Field(default_factory=list)
    note: str = (
        "Availability reflects successful ICMP observations, not guaranteed end-to-end service uptime."
    )
