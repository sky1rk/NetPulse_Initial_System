/** Formatting and presentation helpers with null-safe behaviour. */

export const NA = "N/A";

export function parseTimestamp(value?: string | null): Date | null {
  if (!value) return null;
  const hasZone = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(value);
  const date = new Date(hasZone ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTime(value?: string | null): string {
  const date = parseTimestamp(value);
  if (!date) return NA;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}

export function formatTime(value?: string | null): string {
  const date = parseTimestamp(value);
  if (!date) return NA;
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export function formatNumber(
  value: number | null | undefined,
  unit = "",
  digits = 1,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return NA;
  const formatted = new Intl.NumberFormat(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value);
  return unit ? `${formatted} ${unit}` : formatted;
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return NA;
  return new Intl.NumberFormat().format(value);
}

export function formatLatency(value: number | null | undefined): string {
  return formatNumber(value, "ms", 1);
}

export function formatLoss(value: number | null | undefined): string {
  return formatNumber(value, "%", 1);
}

export function displayText(value: string | null | undefined): string {
  return value && value.trim() ? value : NA;
}

export interface BadgeMeta {
  label: string;
  tone: "green" | "amber" | "rose" | "slate" | "blue" | "teal";
}

const OBSERVATIONS: Record<string, BadgeMeta> = {
  responding: { label: "Responding", tone: "green" },
  no_icmp_response: { label: "No ICMP response", tone: "amber" },
  not_tested: { label: "Not tested", tone: "slate" },
  error: { label: "Error", tone: "rose" },
};

const GENERIC: Record<string, BadgeMeta> = {
  running: { label: "Running", tone: "blue" },
  completed: { label: "Completed", tone: "green" },
  stopped: { label: "Stopped", tone: "slate" },
  interrupted: { label: "Interrupted", tone: "amber" },
  failed: { label: "Failed", tone: "rose" },
  generating: { label: "Generating", tone: "blue" },
  open: { label: "Open", tone: "amber" },
  closed_or_refused: { label: "Closed / refused", tone: "green" },
  filtered_or_timeout: { label: "No response / timeout", tone: "slate" },
  review: { label: "Review", tone: "amber" },
  warning: { label: "Warning", tone: "rose" },
  info: { label: "Info", tone: "blue" },
  idle: { label: "Idle", tone: "slate" },
  ok: { label: "Connected", tone: "green" },
  degraded: { label: "Degraded", tone: "amber" },
};

export function badgeMeta(value?: string | null): BadgeMeta {
  if (!value) return { label: NA, tone: "slate" };
  return OBSERVATIONS[value] ?? GENERIC[value] ?? { label: value.replaceAll("_", " "), tone: "slate" };
}

export function healthTone(score: number | null | undefined): BadgeMeta["tone"] {
  if (score === null || score === undefined) return "slate";
  if (score >= 85) return "green";
  if (score >= 65) return "amber";
  return "rose";
}

export function isoOrNull(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

export function rangeStart(hours: number): string {
  return new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
}

export function todayInputValue(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  const local = new Date(now.getTime() - offset * 60 * 1000);
  return local.toISOString().slice(0, 10);
}

/** Convert a Date to the value format used by <input type="datetime-local">. */
export function toDateTimeLocalValue(date: Date): string {
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60 * 1000);
  return local.toISOString().slice(0, 16);
}

/** Convert a datetime-local input value into the ISO UTC string expected by the API. */
export function datetimeLocalToIso(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

export function formatRange(from?: string | null, to?: string | null): string {
  if (!from && !to) return "All recorded time";
  return `${formatDateTime(from)} → ${formatDateTime(to)}`;
}
