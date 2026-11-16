import { describe, expect, it } from "vitest";

import { buildLatencySeries, buildLossBuckets } from "../lib/analytics";
import type { HistoryPoint } from "../types";

function point(overrides: Partial<HistoryPoint>): HistoryPoint {
  return {
    timestamp: "2026-01-01T00:00:00Z",
    device_id: 1,
    latency_ms: 10,
    success: true,
    observation: "responding",
    source: "monitoring",
    ...overrides,
  };
}

describe("latency series", () => {
  it("preserves null latency for failed probes", () => {
    const series = buildLatencySeries([
      point({ timestamp: "2026-01-01T00:00:00Z", latency_ms: null, success: false, observation: "no_icmp_response" }),
    ]);
    expect(series).toHaveLength(1);
    expect(series[0].latency_ms).toBeNull();
    expect(series[0].success).toBe(false);
  });

  it("sorts points chronologically and skips invalid timestamps", () => {
    const series = buildLatencySeries([
      point({ timestamp: "2026-01-01T00:02:00Z", latency_ms: 20 }),
      point({ timestamp: "bad", latency_ms: 99 }),
      point({ timestamp: "2026-01-01T00:01:00Z", latency_ms: 10 }),
    ]);
    expect(series.map((entry) => entry.latency_ms)).toEqual([10, 20]);
  });
});

describe("packet-loss buckets", () => {
  it("returns no buckets for an empty history", () => {
    expect(buildLossBuckets([])).toEqual([]);
  });

  it("calculates failure proportions from observations", () => {
    const buckets = buildLossBuckets(
      [
        point({ timestamp: "2026-01-01T00:00:00Z", success: true }),
        point({ timestamp: "2026-01-01T00:00:00Z", success: false, latency_ms: null }),
        point({ timestamp: "2026-01-01T00:00:10Z", success: true, latency_ms: 12 }),
        point({ timestamp: "2026-01-01T00:00:10Z", success: true, latency_ms: 14 }),
      ],
      2,
    );
    expect(buckets).toHaveLength(2);
    expect(buckets[0].total).toBe(2);
    expect(buckets[0].failed).toBe(1);
    expect(buckets[0].loss_percent).toBe(50);
    expect(buckets[1].loss_percent).toBe(0);
  });
});
