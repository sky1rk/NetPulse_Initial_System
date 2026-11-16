"""PDF and CSV report generation.

Reports are written inside the configured reports directory.  The database
stores only a relative filename; download routes resolve it by report ID and
refuse any path outside that directory.
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.base import utcnow
from app.models import (
    Device,
    MonitoringObservation,
    MonitoringSession,
    PingTest,
    Report,
    SecurityScan,
)
from app.services import analytics_service, diagnostics_service, network_info_service
from app.services.devices_service import latest_observations
from app.services.errors import NetPulseError

logger = logging.getLogger(__name__)

_LIMITATIONS = [
    "ICMP may be blocked by firewalls or client isolation. A failed ping is not proof that a device is offline.",
    "Hostname and MAC address values are best-effort and may be unavailable.",
    "An open TCP port is an exposure observation, not proof of a vulnerability. No exploit or credential testing is performed.",
    "The logical topology and inferred relationships are not verified physical network connections.",
    "The health score, when present, is a NetPulse indicative score based on configured thresholds, not an industry standard.",
    "Discovery and TCP checks were bounded to explicitly authorized local targets.",
]


def _fmt(value, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:g}{suffix}"
    if isinstance(value, datetime):
        return value.isoformat() + "Z"
    return f"{value}{suffix}"


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)), style)


def _build_table(rows: list[list], widths: list[float], styles) -> Table:
    styled: list[list] = []
    for row_index, row in enumerate(rows):
        converted = []
        for cell in row:
            if row_index == 0:
                converted.append(_paragraph(str(cell), styles["ReportTableHeader"]))
            else:
                converted.append(_paragraph(_fmt(cell), styles["ReportTableBody"]))
        styled.append(converted)
    table = Table(styled, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2740")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9fb3c8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fa")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _report_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportSection",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#0f2740"),
            spaceBefore=10,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportTableHeader",
            parent=styles["BodyText"],
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportTableBody",
            parent=styles["BodyText"],
            fontSize=7.5,
            leading=9,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSmall",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#3b4d61"),
        )
    )
    return styles


def _collect_data(
    db: Session,
    window_from: datetime,
    window_to: datetime,
    device_ids: list[int],
) -> dict:
    devices_query = select(Device).order_by(Device.ip_address)
    if device_ids:
        devices_query = devices_query.where(Device.id.in_(device_ids))
    devices = list(db.scalars(devices_query).all())
    observations = latest_observations(db, [device.id for device in devices])

    ping_query = select(PingTest).where(
        PingTest.started_at >= window_from, PingTest.started_at <= window_to
    )
    if device_ids:
        ping_query = ping_query.where(PingTest.device_id.in_(device_ids))
    ping_tests = list(db.scalars(ping_query.order_by(PingTest.started_at.desc())).all())

    scan_query = select(SecurityScan).where(
        SecurityScan.started_at >= window_from, SecurityScan.started_at <= window_to
    )
    if device_ids:
        scan_query = scan_query.where(SecurityScan.device_id.in_(device_ids))
    security_scans = list(db.scalars(scan_query.order_by(SecurityScan.started_at.desc())).all())

    session_query = select(MonitoringSession).where(
        MonitoringSession.started_at >= window_from, MonitoringSession.started_at <= window_to
    )
    sessions = list(db.scalars(session_query.order_by(MonitoringSession.started_at.desc())).all())

    observation_query = select(MonitoringObservation).where(
        MonitoringObservation.observed_at >= window_from,
        MonitoringObservation.observed_at <= window_to,
    )
    if device_ids:
        observation_query = observation_query.where(MonitoringObservation.device_id.in_(device_ids))
    monitoring_observations = list(db.scalars(observation_query).all())

    summary = analytics_service.get_summary(
        db,
        device_id=device_ids[0] if len(device_ids) == 1 else None,
        from_dt=window_from,
        to_dt=window_to,
    )
    recommendations = diagnostics_service.build_recommendations(db)
    if device_ids:
        recommendations = [
            item
            for item in recommendations
            if item["device_id"] is None or item["device_id"] in device_ids
        ]

    return {
        "network_info": network_info_service.get_network_info(),
        "devices": devices,
        "latest_observations": observations,
        "ping_tests": ping_tests,
        "security_scans": security_scans,
        "sessions": sessions,
        "monitoring_observations": monitoring_observations,
        "summary": summary,
        "recommendations": recommendations,
        "device_lookup": {device.id: device for device in devices},
    }


def _pdf_story(report_id: int, window_from, window_to, data: dict, generated_at) -> list:
    styles = _report_styles()
    story: list = []
    story.append(_paragraph("NetPulse Network Diagnostic Report", styles["Title"]))
    story.append(
        _paragraph(
            f"Report ID: {report_id} &nbsp;&nbsp;|&nbsp;&nbsp; Generated: {_fmt(generated_at)}",
            styles["ReportSmall"],
        )
    )
    story.append(Spacer(1, 5 * mm))

    story.append(_paragraph("1. Scope", styles["ReportSection"]))
    scope_rows = [
        ["Item", "Value"],
        ["Report period from", window_from],
        ["Report period to", window_to],
        ["Devices in scope", len(data["devices"])],
        ["Monitoring observations in period", len(data["monitoring_observations"])],
    ]
    story.append(_build_table(scope_rows, [55 * mm, 110 * mm], styles))

    story.append(_paragraph("2. Local network configuration", styles["ReportSection"]))
    info = data["network_info"]
    info_rows = [
        ["Property", "Observed value"],
        ["Interface", info.get("interface_name")],
        ["Local IPv4", info.get("local_ipv4")],
        ["Subnet mask", info.get("subnet_mask")],
        ["Network CIDR", info.get("network_cidr")],
        ["Default gateway", info.get("default_gateway")],
    ]
    story.append(_build_table(info_rows, [55 * mm, 110 * mm], styles))
    for warning in info.get("warnings") or []:
        story.append(_paragraph(f"Warning: {warning}", styles["ReportSmall"]))

    story.append(_paragraph("3. Discovered device inventory", styles["ReportSection"]))
    if data["devices"]:
        rows = [["IP address", "Hostname", "MAC address", "Observation", "Last seen"]]
        for device in data["devices"]:
            observation = data["latest_observations"].get(device.id, {})
            rows.append(
                [
                    device.ip_address,
                    device.hostname or "N/A",
                    device.mac_address or "N/A",
                    observation.get("latest_observation", "not_tested"),
                    device.last_seen,
                ]
            )
        story.append(_build_table(rows, [27 * mm, 38 * mm, 34 * mm, 33 * mm, 33 * mm], styles))
    else:
        story.append(_paragraph("No devices have been recorded for this scope.", styles["BodyText"]))

    story.append(_paragraph("4. Connectivity and performance summary", styles["ReportSection"]))
    summary = data["summary"]
    metric_rows = [
        ["Metric", "Value"],
        ["Connectivity samples", summary["sample_count"]],
        ["Successful samples", summary["successful_samples"]],
        ["Average latency", _fmt(summary["avg_latency_ms"], " ms")],
        ["Minimum latency", _fmt(summary["min_latency_ms"], " ms")],
        ["Maximum latency", _fmt(summary["max_latency_ms"], " ms")],
        ["Packet loss", _fmt(summary["packet_loss_percent"], " %")],
        ["Jitter (mean absolute difference)", _fmt(summary["jitter_ms"], " ms")],
        ["Monitoring observations", summary["observation_count"]],
        ["Availability (observation-based)", _fmt(summary["availability_percent"], " %")],
    ]
    if summary["health_score"]:
        score = summary["health_score"]
        metric_rows.append(["NetPulse indicative health score", f"{score['score']:g} / 100"])
        metric_rows.append(
            [
                "Health components",
                f"latency {score['latency_score']:g}, loss {score['packet_loss_score']:g}, "
                f"availability {score['availability_score']:g}",
            ]
        )
    else:
        metric_rows.append(["NetPulse indicative health score", "Insufficient data"])
    story.append(_build_table(metric_rows, [75 * mm, 90 * mm], styles))
    for note in summary.get("notes") or []:
        story.append(_paragraph(f"Note: {note}", styles["ReportSmall"]))

    if data["ping_tests"]:
        story.append(_paragraph("5. Recent ping tests", styles["ReportSection"]))
        rows = [["Device", "Started", "Sent", "Received", "Loss", "Avg", "Min", "Max"]]
        for test in data["ping_tests"][:25]:
            device = data["device_lookup"].get(test.device_id)
            rows.append(
                [
                    device.ip_address if device else test.device_id,
                    test.started_at,
                    test.probes_sent,
                    test.probes_received,
                    _fmt(test.packet_loss_percent, " %"),
                    _fmt(test.avg_latency_ms, " ms"),
                    _fmt(test.min_latency_ms, " ms"),
                    _fmt(test.max_latency_ms, " ms"),
                ]
            )
        story.append(
            _build_table(rows, [24 * mm, 31 * mm, 12 * mm, 16 * mm, 18 * mm, 21 * mm, 21 * mm, 22 * mm], styles)
        )

    story.append(_paragraph("6. Security assessment observations", styles["ReportSection"]))
    findings = [
        (scan, finding)
        for scan in data["security_scans"]
        for finding in scan.findings
    ]
    if findings:
        rows = [["Device", "Port", "Service", "Observed state", "Severity", "Note"]]
        for scan, finding in findings[:60]:
            device = data["device_lookup"].get(scan.device_id)
            rows.append(
                [
                    device.ip_address if device else scan.device_id,
                    finding.port,
                    finding.service_name or "unknown",
                    finding.state,
                    finding.severity,
                    finding.recommendation or "N/A",
                ]
            )
        story.append(_build_table(rows, [22 * mm, 11 * mm, 17 * mm, 24 * mm, 16 * mm, 75 * mm], styles))
        story.append(
            _paragraph(
                "An open port is an observation, not proof of a vulnerability. Only the selected "
                "allowlisted ports were checked.",
                styles["ReportSmall"],
            )
        )
    else:
        story.append(
            _paragraph(
                "No TCP service assessment findings were recorded in this period. This does not "
                "mean devices are secure.",
                styles["BodyText"],
            )
        )

    story.append(_paragraph("7. Diagnostic recommendations", styles["ReportSection"]))
    if data["recommendations"]:
        rows = [["Rule", "Severity", "Observed condition", "Recommendation"]]
        for item in data["recommendations"][:40]:
            rows.append(
                [
                    item["rule_id"],
                    item["severity"],
                    item["observed_condition"],
                    item["recommendation"],
                ]
            )
        story.append(_build_table(rows, [30 * mm, 16 * mm, 57 * mm, 62 * mm], styles))
    else:
        story.append(_paragraph("No rule-based recommendations were triggered.", styles["BodyText"]))

    story.append(_paragraph("8. Limitations and methodology", styles["ReportSection"]))
    for limitation in _LIMITATIONS:
        story.append(_paragraph(f"• {limitation}", styles["BodyText"]))
    story.append(Spacer(1, 4 * mm))
    story.append(
        _paragraph(
            "Measurements are derived from persisted observations. Missing values are shown as N/A "
            "rather than zero. Jitter is the mean absolute difference between consecutive successful "
            "latency samples. Availability is the proportion of successful monitoring observations.",
            styles["ReportSmall"],
        )
    )
    return story


def _write_pdf(path: Path, report_id: int, window_from, window_to, data: dict, generated_at) -> None:
    styles = _report_styles()
    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"NetPulse Report {report_id}",
        author="NetPulse",
    )

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#5b6b7c"))
        canvas.drawString(18 * mm, 10 * mm, "NetPulse · Local-first network monitoring report")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(
        _pdf_story(report_id, window_from, window_to, data, generated_at),
        onFirstPage=footer,
        onLaterPages=footer,
    )


def _write_csv(path: Path, data: dict, window_from, window_to) -> None:
    headers = [
        "record_type",
        "device_ip",
        "hostname",
        "mac_address",
        "observed_at",
        "observation",
        "latency_ms",
        "packet_loss_percent",
        "port",
        "port_state",
        "service_name",
        "recommendation",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["NetPulse report period", _fmt(window_from), _fmt(window_to)])
        writer.writerow(headers)
        for device in data["devices"]:
            observation = data["latest_observations"].get(device.id, {})
            writer.writerow(
                [
                    "device",
                    device.ip_address,
                    device.hostname or "",
                    device.mac_address or "",
                    _fmt(device.last_seen),
                    observation.get("latest_observation", "not_tested"),
                    "" if observation.get("latest_latency_ms") is None else observation["latest_latency_ms"],
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
        for test in data["ping_tests"]:
            device = data["device_lookup"].get(test.device_id)
            writer.writerow(
                [
                    "ping_test",
                    device.ip_address if device else "",
                    "",
                    "",
                    _fmt(test.completed_at or test.started_at),
                    "responding" if test.probes_received else "no_icmp_response",
                    "" if test.avg_latency_ms is None else test.avg_latency_ms,
                    "" if test.packet_loss_percent is None else test.packet_loss_percent,
                    "",
                    "",
                    "",
                    "",
                ]
            )
        for scan in data["security_scans"]:
            device = data["device_lookup"].get(scan.device_id)
            for finding in scan.findings:
                writer.writerow(
                    [
                        "security_finding",
                        device.ip_address if device else "",
                        "",
                        "",
                        _fmt(scan.completed_at or scan.started_at),
                        "open" if finding.state == "open" else "not_open",
                        "",
                        "",
                        finding.port,
                        finding.state,
                        finding.service_name or "",
                        finding.recommendation or "",
                    ]
                )
        for item in data["recommendations"]:
            writer.writerow(
                [
                    "recommendation",
                    item.get("device_ip") or "",
                    "",
                    "",
                    _fmt(item.get("created_at")),
                    item.get("severity") or "",
                    "",
                    "",
                    "",
                    "",
                    item.get("rule_id") or "",
                    f"{item.get('observed_condition')} {item.get('recommendation')}",
                ]
            )


def generate_report(
    db: Session,
    report_format: str,
    from_dt: datetime | None,
    to_dt: datetime | None,
    device_ids: list[int],
) -> Report:
    if report_format not in {"pdf", "csv"}:
        raise NetPulseError("INVALID_REPORT_FORMAT", "Report format must be 'pdf' or 'csv'.")

    unique_ids = list(dict.fromkeys(device_ids))
    if unique_ids:
        devices = db.scalars(select(Device).where(Device.id.in_(unique_ids))).all()
        missing = [device_id for device_id in unique_ids if device_id not in {d.id for d in devices}]
        if missing:
            raise NetPulseError(
                "DEVICE_NOT_FOUND",
                f"Device(s) not found: {', '.join(str(value) for value in missing)}.",
                status_code=404,
            )

    window_to = analytics_service.to_naive_utc(to_dt) or utcnow()
    window_from = analytics_service.to_naive_utc(from_dt) or (window_to - timedelta(days=30))
    if window_from >= window_to:
        raise NetPulseError("INVALID_TIME_RANGE", "'from' must be earlier than 'to'.")

    report = Report(
        generated_at=utcnow(),
        report_type=report_format,
        status="generating",
        range_from=window_from,
        range_to=window_to,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    reports_dir = Path(settings.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = report.generated_at.strftime("%Y%m%d_%H%M%S")
    filename = f"netpulse_report_{report.id}_{timestamp}.{report_format}"
    path = reports_dir / filename

    try:
        data = _collect_data(db, window_from, window_to, unique_ids)
        if report_format == "pdf":
            _write_pdf(path, report.id, window_from, window_to, data, report.generated_at)
        else:
            _write_csv(path, data, window_from, window_to)
        report.file_name = filename
        report.file_path = filename
        report.status = "completed"
        db.commit()
        db.refresh(report)
        logger.info("Generated %s report %s", report_format, filename)
        return report
    except Exception as exc:
        logger.exception("Report generation failed")
        report.status = "failed"
        report.error_message = "Report generation failed. Review the backend log for details."
        db.commit()
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        raise NetPulseError(
            "REPORT_GENERATION_FAILED",
            "The report could not be generated. Review the backend log for details.",
            status_code=500,
        ) from exc


def resolve_report_file(report: Report) -> Path:
    """Resolve a report file by database ID and refuse path traversal."""
    if report.status != "completed" or not report.file_path:
        raise NetPulseError(
            "REPORT_NOT_READY", "This report is not available for download.", status_code=409
        )
    base = Path(settings.reports_dir).resolve()
    candidate = (base / report.file_path).resolve()
    if base not in candidate.parents and candidate != base:
        raise NetPulseError(
            "REPORT_PATH_INVALID", "The report path is invalid.", status_code=400
        )
    if not candidate.is_file():
        raise NetPulseError(
            "REPORT_FILE_MISSING", "The report file is no longer available.", status_code=404
        )
    return candidate
