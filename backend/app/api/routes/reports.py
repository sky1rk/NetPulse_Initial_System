"""Report generation, history and download endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Report
from app.schemas.reports import ReportGenerateRequest, ReportListResponse, ReportOut
from app.services import report_service
from app.services.errors import NetPulseError

router = APIRouter(prefix="/reports", tags=["reports"])


def _report_payload(report: Report) -> dict:
    payload = ReportOut.model_validate(report).model_dump()
    if report.status == "completed":
        payload["download_url"] = f"/api/reports/{report.id}/download"
    return payload


@router.post("/generate", response_model=ReportOut)
def generate(
    payload: ReportGenerateRequest, db: Session = Depends(get_db)
) -> dict:
    report = report_service.generate_report(
        db,
        report_format=payload.format,
        from_dt=payload.from_date,
        to_dt=payload.to_date,
        device_ids=payload.device_ids,
    )
    return _report_payload(report)


@router.get("", response_model=ReportListResponse)
def list_reports(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    total = db.scalar(select(func.count(Report.id))) or 0
    reports = db.scalars(select(Report).order_by(Report.generated_at.desc()).limit(limit)).all()
    return {"items": [_report_payload(report) for report in reports], "total": int(total)}


@router.get("/{report_id}/download")
def download(report_id: int, db: Session = Depends(get_db)) -> FileResponse:
    report = db.get(Report, report_id)
    if report is None:
        raise NetPulseError("REPORT_NOT_FOUND", f"Report {report_id} was not found.", status_code=404)
    path = Path(report_service.resolve_report_file(report))
    media_type = "application/pdf" if report.report_type == "pdf" else "text/csv"
    return FileResponse(
        path,
        media_type=media_type,
        filename=report.file_name or path.name,
        headers={"Cache-Control": "no-store"},
    )
