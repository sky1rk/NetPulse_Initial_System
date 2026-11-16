"""Calculation tests from testing/TEST_PLAN.md section 4."""

from __future__ import annotations

import pytest

from app.services.metrics import (
    availability_percent,
    health_score,
    jitter_ms,
    latency_statistics,
    packet_loss_percent,
)


@pytest.mark.parametrize(
    ("sent", "received", "expected"),
    [(5, 5, 0.0), (5, 4, 20.0), (5, 0, 100.0), (0, 0, None)],
)
def test_packet_loss(sent, received, expected):
    assert packet_loss_percent(sent, received) == expected


def test_latency_statistics_known_samples():
    stats = latency_statistics([10, 20, 30])
    assert stats == {"avg_latency_ms": 20.0, "min_latency_ms": 10.0, "max_latency_ms": 30.0}


def test_latency_statistics_unavailable_when_no_success():
    assert latency_statistics([]) == {
        "avg_latency_ms": None,
        "min_latency_ms": None,
        "max_latency_ms": None,
    }


def test_jitter_known_sequence():
    assert jitter_ms([10, 20, 15]) == 7.5


def test_jitter_requires_two_samples():
    assert jitter_ms([10]) is None
    assert jitter_ms([]) is None


def test_availability_known_values():
    assert availability_percent(8, 10) == 80.0
    assert availability_percent(0, 0) is None


def test_health_score_documented_weighting():
    score = health_score(20.0, 10.0, 80.0, 50.0, 100.0, 200.0)
    assert score is not None
    assert score["latency_score"] == 100.0
    assert score["packet_loss_score"] == 90.0
    assert score["availability_score"] == 80.0
    assert score["score"] == pytest.approx(0.4 * 100 + 0.35 * 90 + 0.25 * 80, abs=0.05)


def test_health_score_insufficient_data():
    assert health_score(None, 10.0, 80.0, 50.0, 100.0, 200.0) is None
    assert health_score(20.0, None, 80.0, 50.0, 100.0, 200.0) is None
    assert health_score(20.0, 10.0, None, 50.0, 100.0, 200.0) is None
