/** Client-side transforms for analytics charts. All values derive from API data. */

import type { HistoryPoint } from "../types";
import { formatTime, parseTimestamp } from "./format";

export interface LatencySeriesPoint {
  timestamp: number;
  timeLabel: string;
  latency_ms: number | null;
  success: boolean;
  observation: string;
}

export function buildLatencySeries(points: HistoryPoint[]): LatencySeriesPoint[] {
  return points
    .map((point) => {
      const parsed = parseTimestamp(point.timestamp);
      if (!parsed) return null;
      return {
        timestamp: parsed.getTime(),
        timeLabel: formatTime(point.timestamp),
        latency_ms: point.latency_ms,
        success: point.success,
        observation: point.observation,
      };
    })
    .filter((point): point is LatencySeriesPoint => point !== null)
    .sort((a, b) => a.timestamp - b.timestamp);
}

export interface LossBucket {
  key: string;
  timeLabel: string;
  start: number;
  total: number;
  failed: number;
  loss_percent: number;
}

/**
 * Group ICMP observations into equal time buckets and calculate loss per bucket.
 * Empty buckets are omitted so the chart never implies an observation occurred.
 */
export function buildLossBuckets(points: HistoryPoint[], maximumBuckets = 24): LossBucket[] {
  const timed = points
    .map((point) => {
      const parsed = parseTimestamp(point.timestamp);
      return parsed ? { at: parsed.getTime(), success: point.success } : null;
    })
    .filter((point): point is { at: number; success: boolean } => point !== null)
    .sort((a, b) => a.at - b.at);

  if (timed.length === 0) return [];

  const first = timed[0].at;
  const last = timed[timed.length - 1].at;
  const bucketCount = Math.max(1, Math.min(maximumBuckets, timed.length));
  const width = last > first ? (last - first + 1) / bucketCount : 1;

  const buckets = new Map<number, { total: number; failed: number; at: number }>();
  timed.forEach((point) => {
    const index = Math.min(bucketCount - 1, Math.max(0, Math.floor((point.at - first) / width)));
    const current = buckets.get(index) ?? { total: 0, failed: 0, at: first + index * width };
    current.total += 1;
    if (!point.success) current.failed += 1;
    buckets.set(index, current);
  });

  return [...buckets.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([index, bucket]) => ({
      key: `bucket-${index}`,
      timeLabel: formatTime(new Date(bucket.at).toISOString()),
      start: bucket.at,
      total: bucket.total,
      failed: bucket.failed,
      loss_percent: Math.round((bucket.failed / bucket.total) * 1000) / 10,
    }));
}
