"""Dashboard summary schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.analytics import HealthScoreOut
from app.schemas.common import UtcDateTime


class ActivityItem(BaseModel):
    activity_type: str
    title: str
    description: str
    timestamp: UtcDateTime
    status: str | None = None


class DashboardSummary(BaseModel):
    devices_total: int = 0
    responding_hosts: int = 0
    no_icmp_hosts: int = 0
    not_tested_hosts: int = 0
    avg_latency_ms: float | None = None
    packet_loss_percent: float | None = None
    health_score: HealthScoreOut | None = None
    health_label: str = "Insufficient data"
    last_scan_at: UtcDateTime | None = None
    latest_observation_at: UtcDateTime | None = None
    active_monitoring_sessions: int = 0
    open_security_findings: int = 0
    reports_count: int = 0
    recent_activity: list[ActivityItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
