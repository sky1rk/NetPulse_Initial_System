"""Report schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDateTime


class ReportGenerateRequest(BaseModel):
    format: Literal["pdf", "csv"] = "pdf"
    from_date: datetime | None = Field(default=None, alias="from")
    to_date: datetime | None = Field(default=None, alias="to")
    device_ids: list[int] = Field(default_factory=list, max_length=500)

    model_config = ConfigDict(populate_by_name=True)


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    generated_at: UtcDateTime
    report_type: str
    status: str
    file_name: str | None = None
    range_from: UtcDateTime | None = None
    range_to: UtcDateTime | None = None
    error_message: str | None = None
    download_url: str | None = None


class ReportListResponse(BaseModel):
    items: list[ReportOut] = Field(default_factory=list)
    total: int
