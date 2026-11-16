import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  EmptyState,
  ErrorState,
  LoadingState,
  MetricCard,
  Notice,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { buildLatencySeries, buildLossBuckets } from "../lib/analytics";
import {
  displayText,
  formatCount,
  formatDateTime,
  formatLatency,
  formatLoss,
  formatNumber,
  formatTime,
  healthTone,
} from "../lib/format";
import { api } from "../services/api";

const PRESETS = [
  { hours: 1, label: "1 hour" },
  { hours: 6, label: "6 hours" },
  { hours: 24, label: "24 hours" },
  { hours: 168, label: "7 days" },
];

function makeRange(hours: number): { from: string; to: string } {
  const to = new Date();
  const from = new Date(to.getTime() - hours * 60 * 60 * 1000);
  return { from: from.toISOString(), to: to.toISOString() };
}

const TOOLTIP_STYLE = {
  backgroundColor: "#0b1422",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: "0.5rem",
  color: "#e2e8f0",
  fontSize: "12px",
};

function HealthComponents({
  score,
}: {
  score: {
    latency_score: number;
    packet_loss_score: number;
    availability_score: number;
    thresholds: { good_ms: number; fair_ms: number; poor_ms: number };
  };
}) {
  const rows = [
    { label: "Latency", value: score.latency_score, weight: "40%" },
    { label: "Packet loss", value: score.packet_loss_score, weight: "35%" },
    { label: "Availability", value: score.availability_score, weight: "25%" },
  ];
  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div key={row.label}>
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">
              {row.label} · weight {row.weight}
            </span>
            <span className="font-medium text-slate-200">{formatNumber(row.value, "", 0)} / 100</span>
          </div>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-pulse to-pulse-teal"
              style={{ width: `${Math.max(0, Math.min(100, row.value))}%` }}
            />
          </div>
        </div>
      ))}
      <p className="text-[11px] leading-relaxed text-slate-500">
        Thresholds: good ≤ {formatNumber(score.thresholds.good_ms, "ms", 0)}, fair ≤{" "}
        {formatNumber(score.thresholds.fair_ms, "ms", 0)}, poor ≤ {formatNumber(score.thresholds.poor_ms, "ms", 0)}.
      </p>
    </div>
  );
}

export default function AnalyticsPage() {
  const devicesState = useAsync(() => api.devices({ limit: 500 }), []);
  const [deviceId, setDeviceId] = useState<number | "">("");
  const [rangeHours, setRangeHours] = useState(24);
  const [range, setRange] = useState(() => makeRange(24));

  const summaryState = useAsync(
    () =>
      api.analyticsSummary({
        device_id: deviceId === "" ? null : deviceId,
        from: range.from,
        to: range.to,
      }),
    [deviceId, range.from, range.to],
  );
  const historyState = useAsync(
    () =>
      api.analyticsHistory({
        device_id: deviceId === "" ? null : deviceId,
        from: range.from,
        to: range.to,
        limit: 2000,
      }),
    [deviceId, range.from, range.to],
  );

  const latencySeries = useMemo(
    () => buildLatencySeries(historyState.data?.points ?? []),
    [historyState.data],
  );
  const lossBuckets = useMemo(
    () => buildLossBuckets(historyState.data?.points ?? []),
    [historyState.data],
  );

  const selectPreset = (hours: number) => {
    setRangeHours(hours);
    setRange(makeRange(hours));
  };

  const refresh = () => setRange(makeRange(rangeHours));
  const loading = summaryState.loading || historyState.loading;
  const summary = summaryState.data;
  const hasMeasurements = Boolean(
    summary && (summary.sample_count > 0 || summary.observation_count > 0),
  );
  const successfulLatencyPoints = latencySeries.filter((point) => point.latency_ms !== null).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Performance analytics"
        description="Latency, packet loss, jitter and availability calculated from stored ping probes and monitoring observations."
        actions={
          <button type="button" className="btn-secondary" onClick={refresh} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh window"}
          </button>
        }
      />

      <SectionCard
        title="Analysis window"
        description="All metrics and charts use the same selected time range and optional device scope."
      >
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
          <div>
            <label htmlFor="analytics-device" className="field-label">
              Device scope
            </label>
            <select
              id="analytics-device"
              className="field"
              value={deviceId}
              onChange={(event) => setDeviceId(event.target.value ? Number(event.target.value) : "")}
              disabled={devicesState.loading}
            >
              <option value="">All devices</option>
              {(devicesState.data?.items ?? []).map((device) => (
                <option key={device.id} value={device.id}>
                  {device.ip_address}
                  {device.hostname ? ` · ${device.hostname}` : ""}
                </option>
              ))}
            </select>
            {devicesState.error ? (
              <p className="mt-1.5 text-xs text-rose-300">
                Device list unavailable: {devicesState.error.message}
              </p>
            ) : null}
            <p className="mt-1.5 text-[11px] text-slate-500">
              Window: {formatDateTime(range.from)} → {formatDateTime(range.to)}
            </p>
          </div>
          <div>
            <span className="field-label">Time range</span>
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((preset) => (
                <button
                  key={preset.hours}
                  type="button"
                  className={rangeHours === preset.hours ? "btn-primary" : "btn-secondary"}
                  onClick={() => selectPreset(preset.hours)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </SectionCard>

      {loading && !summary ? <LoadingState label="Calculating performance metrics…" /> : null}

      {summaryState.error && !summary ? (
        <ErrorState
          title="Analytics unavailable"
          error={{ message: summaryState.error.message, code: summaryState.error.code }}
          onRetry={summaryState.refetch}
        />
      ) : null}

      {summary ? (
        <>
          {summaryState.error ? (
            <Notice tone="danger" title="Metrics may be stale">
              {summaryState.error.message}
            </Notice>
          ) : null}

          {!hasMeasurements ? (
            <EmptyState
              title="No measurements in this window"
              description="Run a ping test or a monitoring session for the selected scope, or widen the time range. NetPulse does not plot estimated or sample values."
              action={
                <Link to="/devices" className="btn-primary">
                  Open devices
                </Link>
              }
            />
          ) : (
            <>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="Average latency"
                  value={formatLatency(summary.avg_latency_ms)}
                  hint={`Min ${formatLatency(summary.min_latency_ms)} · Max ${formatLatency(summary.max_latency_ms)}`}
                  tone="teal"
                />
                <MetricCard
                  label="Packet loss"
                  value={formatLoss(summary.packet_loss_percent)}
                  hint={`${formatCount(summary.successful_samples)} / ${formatCount(summary.sample_count)} probe replies`}
                  tone={
                    summary.packet_loss_percent === null
                      ? "slate"
                      : summary.packet_loss_percent > 20
                        ? "rose"
                        : summary.packet_loss_percent > 0
                          ? "amber"
                          : "green"
                  }
                />
                <MetricCard
                  label="Jitter"
                  value={summary.jitter_ms === null ? "N/A" : formatNumber(summary.jitter_ms, "ms", 1)}
                  hint="Mean absolute difference between consecutive successful samples"
                  tone="blue"
                />
                <MetricCard
                  label="Availability"
                  value={formatLoss(summary.availability_percent)}
                  hint={`${formatCount(summary.successful_observations)} / ${formatCount(summary.observation_count)} monitoring checks`}
                  tone={
                    summary.availability_percent === null
                      ? "slate"
                      : summary.availability_percent >= 99
                        ? "green"
                        : summary.availability_percent >= 90
                          ? "amber"
                          : "rose"
                  }
                />
              </div>

              <div className="grid gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
                <SectionCard
                  title="Latency history"
                  description="Successful ICMP samples only. Gaps indicate probes with no reply or no observation."
                >
                  {latencySeries.length === 0 ? (
                    <EmptyState
                      title="No plottable history"
                      description="The summary window contains measurements, but no timestamped history points were returned."
                    />
                  ) : (
                    <>
                      {successfulLatencyPoints === 0 ? (
                        <Notice tone="warning" className="mb-3">
                          No successful latency samples exist in this window. Failed probes are stored as null,
                          so the chart has no plotted latency values.
                        </Notice>
                      ) : null}
                      <div className="h-72 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={latencySeries} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
                            <CartesianGrid stroke="rgba(148,163,184,0.12)" strokeDasharray="3 3" />
                            <XAxis
                              dataKey="timestamp"
                              type="number"
                              scale="time"
                              domain={["dataMin", "dataMax"]}
                              tickFormatter={(value) => formatTime(new Date(Number(value)).toISOString())}
                              stroke="#64748b"
                              tick={{ fontSize: 11 }}
                              minTickGap={40}
                            />
                            <YAxis
                              stroke="#64748b"
                              tick={{ fontSize: 11 }}
                              width={58}
                              domain={[0, "auto"]}
                              tickFormatter={(value) => `${value}`}
                              label={{
                                value: "Latency (ms)",
                                angle: -90,
                                position: "insideLeft",
                                fill: "#64748b",
                                fontSize: 11,
                              }}
                            />
                            <Tooltip
                              contentStyle={TOOLTIP_STYLE}
                              labelFormatter={(value) => formatTime(new Date(Number(value)).toISOString())}
                              formatter={(value) => [
                                value === null || value === undefined
                                  ? "No successful sample"
                                  : formatNumber(Number(value), "ms", 1),
                                "Latency",
                              ]}
                            />
                            <Line
                              type="monotone"
                              dataKey="latency_ms"
                              name="Latency"
                              stroke="#60a5fa"
                              strokeWidth={2}
                              dot={false}
                              activeDot={{ r: 3 }}
                              connectNulls={false}
                              isAnimationActive={false}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                      <p className="mt-2 text-[11px] text-slate-500">
                        {formatCount(successfulLatencyPoints)} successful latency sample
                        {successfulLatencyPoints === 1 ? "" : "s"} plotted across {formatCount(latencySeries.length)}{" "}
                        observations.
                      </p>
                    </>
                  )}
                </SectionCard>

                <SectionCard
                  title="Network health indicator"
                  description="NetPulse indicative score, not a recognized industry standard."
                  actions={
                    summary.health_score ? (
                      <StatusBadge
                        value={null}
                        label={`${formatNumber(summary.health_score.score, "", 0)}/100 · ${healthTone(summary.health_score.score)}`}
                      />
                    ) : null
                  }
                >
                  {summary.health_score ? (
                    <div className="space-y-4">
                      <div className="text-3xl font-semibold text-white">
                        {formatNumber(summary.health_score.score, "", 0)}
                        <span className="ml-1 text-sm font-normal text-slate-500">/ 100</span>
                      </div>
                      <HealthComponents score={summary.health_score} />
                    </div>
                  ) : (
                    <div className="space-y-2 text-sm leading-relaxed text-slate-400">
                      <p>
                        Health is unavailable because a required input is missing. The formula needs latency
                        samples, packet loss and monitoring availability.
                      </p>
                      <p className="text-xs text-slate-500">
                        Missing values remain null instead of being treated as zero.
                      </p>
                    </div>
                  )}
                </SectionCard>
              </div>

              <div className="grid gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
                <SectionCard
                  title="Packet loss by interval"
                  description="Derived by grouping the stored observations into equal time buckets."
                >
                  {lossBuckets.length === 0 ? (
                    <EmptyState
                      title="No observations to group"
                      description="There are no timestamped monitoring observations in this window."
                    />
                  ) : (
                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={lossBuckets} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
                          <CartesianGrid stroke="rgba(148,163,184,0.12)" strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="timeLabel" stroke="#64748b" tick={{ fontSize: 11 }} minTickGap={28} />
                          <YAxis
                            stroke="#64748b"
                            tick={{ fontSize: 11 }}
                            width={48}
                            domain={[0, 100]}
                            tickFormatter={(value) => `${value}%`}
                          />
                          <Tooltip
                            contentStyle={TOOLTIP_STYLE}
                            formatter={(value, _name, item) => {
                              const payload = item?.payload as { total?: number; failed?: number } | undefined;
                              return [
                                `${formatNumber(Number(value), "%", 1)} (${formatCount(payload?.failed ?? null)} of ${formatCount(payload?.total ?? null)})`,
                                "Packet loss",
                              ];
                            }}
                          />
                          <Bar
                            dataKey="loss_percent"
                            name="Packet loss"
                            fill="#fb7185"
                            radius={[3, 3, 0, 0]}
                            maxBarSize={30}
                            isAnimationActive={false}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                  <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
                    Packet loss = failed observations ÷ total observations in each interval. Buckets without
                    observations are omitted; the chart is not an uptime guarantee.
                  </p>
                </SectionCard>

                <SectionCard title="Calculation details" description="Sample counts, window and explanatory notes from the backend.">
                  <div className="space-y-3 text-sm">
                    <div className="flex items-center justify-between gap-3 border-b border-white/[0.06] pb-2">
                      <span className="text-slate-500">Window</span>
                      <span className="text-right text-xs text-slate-300">
                        {formatDateTime(summary.window_from)} → {formatDateTime(summary.window_to)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-3 border-b border-white/[0.06] pb-2">
                      <span className="text-slate-500">Probe samples</span>
                      <span className="text-slate-200">
                        {formatCount(summary.successful_samples)} / {formatCount(summary.sample_count)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-3 border-b border-white/[0.06] pb-2">
                      <span className="text-slate-500">Monitoring checks</span>
                      <span className="text-slate-200">
                        {formatCount(summary.successful_observations)} / {formatCount(summary.observation_count)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-3 border-b border-white/[0.06] pb-2">
                      <span className="text-slate-500">Scope</span>
                      <span className="text-slate-200">
                        {summary.device_id === null ? "All devices" : `Device #${summary.device_id}`}
                      </span>
                    </div>
                    {summary.notes.length > 0 ? (
                      <ul className="space-y-1.5 text-xs text-slate-400">
                        {summary.notes.map((note, index) => (
                          <li key={`${note}-${index}`}>• {note}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-500">The backend returned no additional notes.</p>
                    )}
                    <p className="text-xs text-slate-500">
                      Jitter = mean absolute difference between consecutive successful latency samples. If fewer
                      than two successful samples exist, jitter is N/A.
                    </p>
                    <p className="text-xs text-slate-500">
                      Availability = successful monitoring checks ÷ total monitoring checks. It does not prove
                      end-to-end service uptime.
                    </p>
                    <p className="text-xs text-slate-500">
                      Scope label: {displayText(summary.device_id === null ? "All devices" : String(summary.device_id))}
                    </p>
                  </div>
                </SectionCard>
              </div>
            </>
          )}
        </>
      ) : null}
    </div>
  );
}
