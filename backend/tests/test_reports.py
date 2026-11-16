"""Report generation and download safety tests."""

from __future__ import annotations

import pytest

from app.database.base import utcnow
from app.models import Report
from app.services import report_service
from app.services.errors import NetPulseError


@pytest.fixture
def reports_dir(tmp_path, monkeypatch):
    directory = tmp_path / "reports"
    directory.mkdir()
    monkeypatch.setattr(report_service.settings, "reports_dir", directory)
    return directory


def test_csv_report_contains_device_rows(db_session, device, reports_dir):
    report = report_service.generate_report(db_session, "csv", None, None, [device.id])
    assert report.status == "completed"
    path = reports_dir / report.file_name
    assert path.is_file()
    text = path.read_text(encoding="utf-8-sig")
    assert "192.168.1.10" in text
    assert "record_type" in text
    assert "demo-device" in text


def test_pdf_report_is_created(db_session, device, reports_dir):
    report = report_service.generate_report(db_session, "pdf", None, None, [device.id])
    assert report.status == "completed"
    path = reports_dir / report.file_name
    assert path.is_file()
    assert path.read_bytes()[:4] == b"%PDF"
    assert path.stat().st_size > 1000


def test_report_with_no_data(db_session, reports_dir):
    report = report_service.generate_report(db_session, "pdf", None, None, [])
    assert report.status == "completed"
    assert (reports_dir / report.file_name).is_file()


def test_invalid_format_rejected(db_session):
    with pytest.raises(NetPulseError) as error:
        report_service.generate_report(db_session, "docx", None, None, [])
    assert error.value.code == "INVALID_REPORT_FORMAT"


def test_invalid_device_rejected(db_session):
    with pytest.raises(NetPulseError) as error:
        report_service.generate_report(db_session, "pdf", None, None, [999])
    assert error.value.code == "DEVICE_NOT_FOUND"


def test_download_path_traversal_rejected(db_session, reports_dir, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("do not expose", encoding="utf-8")
    report = Report(
        generated_at=utcnow(),
        report_type="pdf",
        file_name="evil.pdf",
        file_path="../secret.txt",
        status="completed",
    )
    db_session.add(report)
    db_session.commit()
    with pytest.raises(NetPulseError) as error:
        report_service.resolve_report_file(report)
    assert error.value.code == "REPORT_PATH_INVALID"


def test_download_requires_completed_report(db_session, reports_dir):
    report = Report(
        generated_at=utcnow(), report_type="pdf", status="failed", file_path="missing.pdf"
    )
    db_session.add(report)
    db_session.commit()
    with pytest.raises(NetPulseError) as error:
        report_service.resolve_report_file(report)
    assert error.value.code == "REPORT_NOT_READY"


def test_api_report_generation_and_download(client, db_session, device, reports_dir):
    response = client.post("/api/reports/generate", json={"format": "csv", "device_ids": [device.id]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["download_url"] == f"/api/reports/{payload['id']}/download"

    listing = client.get("/api/reports").json()
    assert listing["total"] == 1

    download = client.get(payload["download_url"])
    assert download.status_code == 200
    assert "192.168.1.10" in download.text


def test_unknown_report_download(client):
    response = client.get("/api/reports/999/download")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "REPORT_NOT_FOUND"
