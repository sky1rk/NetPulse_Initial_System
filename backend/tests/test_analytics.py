"""Analytics calculations over persisted observations."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.database.base import utcnow
from app.models import MonitoringObservation, MonitoringSession, PingProbe, PingTest
from app.services import analytics_service


def _ping_test(db_session, device, samples: list[float | None]):
    now = utcnow()
    test = PingTest(
        device_id=device.id,
        started_at=now - timedelta(minutes=1),
        completed_at=now,
        probes_sent=len(samples),
        probes_received=len([value for value in samples if value is not None]),
        packet_loss_percent=(len(samples) - len([v for v in samples if v is not None])) / len(samples) * 100,
        status="completed",
    )
    db_session.add(test)
    db_session.flush()
    for index, value in enumerate(samples, start=1):
        db_session.add(
            PingProbe(
                ping_test_id=test.id,
                sequence_number=index,
                tested_at=now - timedelta(minutes=1) + timedelta(seconds=index),
                success=value is not None,
                latency_ms=value,
                error_message=None if value is not None else "timeout",
            )
        )
    db_session.commit()
    return test


def _monitoring(db_session, device, outcomes: list[bool]):
    now = utcnow()
    session = MonitoringSession(
        started_at=now - timedelta(minutes=10),
        interval_seconds=10,
        status="stopped",
        ended_at=now,
    )
    db_session.add(session)
    db_session.flush()
    for index, success in enumerate(outcomes):
        db_session.add(
            MonitoringObservation(
                session_id=session.id,
                device_id=device.id,
                observed_at=now - timedelta(minutes=9) + timedelta(seconds=index * 10),
                icmp_success=success,
                latency_ms=20.0 if success else None,
                observation="responding" if success else "no_icmp_response",
            )
        )
    db_session.commit()
    return session


def test_summary_ping_statistics(db_session, device):
    _ping_test(db_session, device, [10.0, 20.0, 30.0, 40.0, None])
    summary = analytics_service.get_summary(db_session, device_id=device.id)
    assert summary["sample_count"] == 5
    assert summary["successful_samples"] == 4
    assert summary["avg_latency_ms"] == 25.0
    assert summary["min_latency_ms"] == 10.0
    assert summary["max_latency_ms"] == 40.0
    assert summary["packet_loss_percent"] == 20.0
    assert summary["jitter_ms"] == 10.0
    assert summary["availability_percent"] is None
    assert summary["health_score"] is None


def test_availability_and_health_score(db_session, device):
    _monitoring(db_session, device, [True] * 8 + [False] * 2)
    summary = analytics_service.get_summary(db_session, device_id=device.id)
    assert summary["observation_count"] == 10
    assert summary["successful_observations"] == 8
    assert summary["availability_percent"] == 80.0
    assert summary["packet_loss_percent"] == 20.0
    assert summary["health_score"] is not None
    assert summary["health_score"]["availability_score"] == 80.0
    assert 0 <= summary["health_score"]["score"] <= 100


def test_empty_summary_is_null_not_zero(db_session, device):
    summary = analytics_service.get_summary(db_session, device_id=device.id)
    assert summary["sample_count"] == 0
    assert summary["avg_latency_ms"] is None
    assert summary["packet_loss_percent"] is None
    assert summary["availability_percent"] is None
    assert summary["health_score"] is None


def test_history_sorted_and_filtered(db_session, device):
    _ping_test(db_session, device, [10.0, 20.0])
    _monitoring(db_session, device, [True, False])
    history = analytics_service.get_history(db_session, device_id=device.id, limit=10)
    timestamps = [point["timestamp"] for point in history["points"]]
    assert timestamps == sorted(timestamps)
    assert history["sample_count"] == 4
    assert {point["source"] for point in history["points"]} == {"ping", "monitoring"}


def test_invalid_time_range_rejected(db_session, device):
    now = utcnow()
    with pytest.raises(Exception) as error:
        analytics_service.get_summary(
            db_session, device_id=device.id, from_dt=now, to_dt=now - timedelta(hours=1)
        )
    assert getattr(error.value, "code", "") == "INVALID_TIME_RANGE"


def test_history_respects_limit(db_session, device):
    _ping_test(db_session, device, [float(value) for value in range(1, 21)])
    history = analytics_service.get_history(db_session, device_id=device.id, limit=5)
    assert history["sample_count"] == 5
    assert len(history["points"]) == 5
    assert any("most recent 5" in note for note in history["notes"])
