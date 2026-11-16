"""Pure metric calculations shared by connectivity, analytics and reports.

Formulas follow SRS section 6 exactly:
* packet loss = ((N - R) / N) * 100
* latency statistics use successful replies only
* jitter = mean(abs(t[i] - t[i-1])) over consecutive successful samples
* availability = successful observations / total observations * 100
"""

from __future__ import annotations

from collections.abc import Sequence


def round_optional(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def packet_loss_percent(probes_sent: int, probes_received: int) -> float | None:
    """Return packet loss, or ``None`` when no probes were sent."""
    if probes_sent <= 0:
        return None
    if probes_received < 0:
        probes_received = 0
    if probes_received > probes_sent:
        probes_received = probes_sent
    return round(((probes_sent - probes_received) / probes_sent) * 100, 2)


def latency_statistics(samples: Sequence[float]) -> dict[str, float | None]:
    """Average/minimum/maximum latency from successful samples only."""
    values = [float(value) for value in samples if value is not None]
    if not values:
        return {"avg_latency_ms": None, "min_latency_ms": None, "max_latency_ms": None}
    return {
        "avg_latency_ms": round(sum(values) / len(values), 2),
        "min_latency_ms": round(min(values), 2),
        "max_latency_ms": round(max(values), 2),
    }


def jitter_ms(samples: Sequence[float]) -> float | None:
    """Mean absolute difference between consecutive successful samples."""
    values = [float(value) for value in samples if value is not None]
    if len(values) < 2:
        return None
    differences = [abs(values[index] - values[index - 1]) for index in range(1, len(values))]
    return round(sum(differences) / len(differences), 2)


def availability_percent(successful: int, total: int) -> float | None:
    """Successful observations divided by total observations."""
    if total <= 0:
        return None
    return round((successful / total) * 100, 2)


def latency_score(avg_latency_ms: float, good_ms: float, fair_ms: float, poor_ms: float) -> float:
    """Step-based indicative latency score (documented in the UI and reports)."""
    if avg_latency_ms <= good_ms:
        return 100.0
    if avg_latency_ms <= fair_ms:
        return 80.0
    if avg_latency_ms <= poor_ms:
        return 60.0
    return 30.0


def health_score(
    avg_latency_ms: float | None,
    loss_percent: float | None,
    availability: float | None,
    good_ms: float,
    fair_ms: float,
    poor_ms: float,
) -> dict | None:
    """Calculate the optional NetPulse indicative health score.

    Returns ``None`` when any required input is unavailable, so the UI can
    display ``Insufficient data`` instead of a fabricated score.
    """
    if avg_latency_ms is None or loss_percent is None or availability is None:
        return None
    lat_score = latency_score(avg_latency_ms, good_ms, fair_ms, poor_ms)
    loss_score = max(0.0, min(100.0, 100.0 - loss_percent))
    avail_score = max(0.0, min(100.0, availability))
    score = 0.40 * lat_score + 0.35 * loss_score + 0.25 * avail_score
    score = max(0.0, min(100.0, score))
    return {
        "score": round(score, 1),
        "latency_score": round(lat_score, 1),
        "packet_loss_score": round(loss_score, 1),
        "availability_score": round(avail_score, 1),
        "thresholds": {"good_ms": good_ms, "fair_ms": fair_ms, "poor_ms": poor_ms},
        "label": "NetPulse indicative score (not an industry standard)",
    }
