"""Diagnostics schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import UtcDateTime


class RecommendationOut(BaseModel):
    rule_id: str
    title: str
    severity: str
    observed_condition: str
    recommendation: str
    created_at: UtcDateTime
    device_id: int | None = None
    device_ip: str | None = None
    evidence: dict | None = None


class RecommendationsResponse(BaseModel):
    items: list[RecommendationOut] = Field(default_factory=list)
    generated_at: UtcDateTime
    note: str = (
        "Recommendations are deterministic, rule-based guidance derived from recorded observations. "
        "They do not establish a root cause."
    )
