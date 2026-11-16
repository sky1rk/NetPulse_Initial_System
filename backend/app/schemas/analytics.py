"""Analytics schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import UtcDateTime


class HealthThresholds(BaseModel):
    good_ms: float
    fair_ms: float
    poor_ms: float


class HealthScoreOut(BaseModel):
    score: float
    latency_score: float
    packet_loss_score: float
    availability_score: float
    thresholds: HealthThresholds
    label: str = "NetPulse indicative score (not an industry standard)"


class AnalyticsSummary(BaseModel):
    device_id: int | None = None
    window_from: UtcDateTime
    window_to: UtcDateTime
    sample_count: int = 0
    successful_samples: int = 0
    avg_latency_ms: float | None = None
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    packet_loss_percent: float | None = None
    jitter_ms: float | None = None
    observation_count: int = 0
    successful_observations: int = 0
    availability_percent: float | None = None
    health_score: HealthScoreOut | None = None
    notes: list[str] = Field(default_factory=list)


class HistoryPoint(BaseModel):
    timestamp: UtcDateTime
    device_id: int
    latency_ms: float | None = None
    success: bool
    observation: str
    source: str


class HistoryResponse(BaseModel):
    device_id: int | None = None
    window_from: UtcDateTime
    window_to: UtcDateTime
    points: list[HistoryPoint] = Field(default_factory=list)
    sample_count: int = 0
    success_count: int = 0
    notes: list[str] = Field(default_factory=list)
