import { describe, expect, it } from "vitest";

import {
  NA,
  badgeMeta,
  datetimeLocalToIso,
  displayText,
  formatCount,
  formatLatency,
  formatLoss,
  formatNumber,
  healthTone,
  parseTimestamp,
  toDateTimeLocalValue,
} from "../lib/format";

describe("null-safe formatting", () => {
  it("renders unavailable values as N/A instead of zero", () => {
    expect(formatLatency(null)).toBe(NA);
    expect(formatLatency(undefined)).toBe(NA);
    expect(formatLoss(null)).toBe(NA);
    expect(formatCount(null)).toBe(NA);
    expect(formatNumber(Number.NaN)).toBe(NA);
    expect(displayText(null)).toBe(NA);
    expect(displayText("   ")).toBe(NA);
  });

  it("keeps genuine zero distinct from an unavailable value", () => {
    expect(formatLoss(0)).toBe("0 %");
    expect(formatLatency(0)).toBe("0 ms");
    expect(formatCount(0)).toBe("0");
    expect(displayText("0")).toBe("0");
  });
});

describe("timestamp parsing", () => {
  it("treats zone-less backend timestamps as UTC", () => {
    expect(parseTimestamp("2026-01-01T00:00:00")?.toISOString()).toBe("2026-01-01T00:00:00.000Z");
    expect(parseTimestamp("2026-01-01T00:00:00Z")?.toISOString()).toBe("2026-01-01T00:00:00.000Z");
  });

  it("returns null for invalid or missing values", () => {
    expect(parseTimestamp(null)).toBeNull();
    expect(parseTimestamp("not-a-date")).toBeNull();
  });

  it("round-trips datetime-local values through ISO", () => {
    const original = new Date("2026-05-04T12:34:00.000Z");
    const localValue = toDateTimeLocalValue(original);
    expect(datetimeLocalToIso(localValue)).toBe(original.toISOString());
  });
});

describe("presentation helpers", () => {
  it("maps observations to cautious labels", () => {
    expect(badgeMeta("no_icmp_response").label).toBe("No ICMP response");
    expect(badgeMeta("responding").tone).toBe("green");
    expect(badgeMeta("filtered_or_timeout").label).toBe("No response / timeout");
  });

  it("assigns health tones from the score", () => {
    expect(healthTone(null)).toBe("slate");
    expect(healthTone(90)).toBe("green");
    expect(healthTone(70)).toBe("amber");
    expect(healthTone(20)).toBe("rose");
  });
});
