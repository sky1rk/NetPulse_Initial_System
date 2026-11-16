"""Connectivity (ping) schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDateTime


class PingRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=100)
    timeout_ms: int = Field(default=1000, ge=50, le=30000)


class PingProbeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sequence_number: int
    success: bool
    latency_ms: float | None = None
    tested_at: UtcDateTime
    error_message: str | None = None


class PingTestResponse(BaseModel):
    test_id: int
    device_id: int
    probes_sent: int
    probes_received: int
    packet_loss_percent: float | None = None
    avg_latency_ms: float | None = None
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    jitter_ms: float | None = None
    status: str
    started_at: UtcDateTime
    completed_at: UtcDateTime | None = None
    probes: list[PingProbeOut] = Field(default_factory=list)
    message: str | None = None
