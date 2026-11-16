import { Link } from "react-router-dom";

import {
  DataList,
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
import {
  displayText,
  formatCount,
  formatDateTime,
  formatLatency,
  formatLoss,
  formatNumber,
  healthTone,
} from "../lib/format";
import { api } from "../services/api";

function HealthBreakdown({
  score,
}: {
  score: {
    score: number;
    latency_score: number;
    packet_loss_score: number;
    availability_score: number;
    thresholds: { good_ms: number; fair_ms: number; poor_ms: number };
  };
}) {
  const rows = [
    { label: "Latency score", value: score.latency_score, weight: "40%" },
    { label: "Packet-loss score", value: score.packet_loss_score, weight: "35%" },
    { label: "Availability score", value: score.availability_score, weight: "25%" },
  ];
  return (
    <div className="space-y-2.5">
      {rows.map((row) => (
        <div key={row.label}>
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">
              {row.label} <span className="text-slate-600">· {row.weight}</span>
            </span>
            <span className="font-medium text-slate-200">{formatNumber(row.value, "", 0)}</span>
          </div>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-pulse to-pulse-teal"
              style={{ width: `${Math.max(0, Math.min(100, row.value))}%` }}
            />
          </div>
        </div>
      ))}
      <p className="pt-1 text-[11px] leading-relaxed text-slate-500">
        Latency thresholds: good ≤ {formatNumber(score.thresholds.good_ms, "ms", 0)}, fair ≤{" "}
        {formatNumber(score.thresholds.fair_ms, "ms", 0)}, poor ≤{" "}
        {formatNumber(score.thresholds.poor_ms, "ms", 0)}. The score is a NetPulse indicative value, not an
        industry standard.
      </p>
    </div>
  );
}

export default function OverviewPage() {
  const { data, loading, error, refetch } = useAsync(() => api.dashboard(), []);

  const header = (
    <PageHeader
      title="Overview"
      description="A live summary of recorded discovery, connectivity and assessment activity on this machine."
      actions={
        <button type="button" className="btn-secondary" onClick={refetch} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      }
    />
  );

  if (loading && !data) {
    return (
      <div className="space-y-6">
        {header}
        <LoadingState label="Loading dashboard summary…" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-6">
        {header}
        <ErrorState
          title="Dashboard unavailable"
          error={
            error
              ? { message: error.message, code: error.code }
              : { message: "The dashboard summary could not be loaded." }
          }
          onRetry={refetch}
        />
      </div>
    );
  }

  const score = data.health_score;
  const hasDevices = data.devices_total > 0;

  return (
    <div className="space-y-6">
      {header}

      {error ? (
        <Notice tone="danger" title="Showing the last successful summary">
          {error.message}
        </Notice>
      ) : null}

      {data.warnings.length > 0 ? (
        <Notice tone="warning" title="Operational warnings">
          <ul className="list-inside list-disc space-y-1">
            {data.warnings.map((warning, index) => (
              <li key={`${warning}-${index}`}>{warning}</li>
            ))}
          </ul>
        </Notice>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <MetricCard
          label="Discovered devices"
          value={formatCount(data.devices_total)}
          hint={`${formatCount(data.not_tested_hosts)} not yet tested`}
          tone="blue"
          footer={
            <Link to="/devices" className="link">
              Open device inventory →
            </Link>
          }
        />
        <MetricCard
          label="Responding hosts"
          value={formatCount(data.responding_hosts)}
          hint="Latest ICMP observation was successful"
          tone="green"
        />
        <MetricCard
          label="No ICMP response"
          value={formatCount(data.no_icmp_hosts)}
          hint="Not proof that a host is offline"
          tone="amber"
        />
        <MetricCard
          label="Average latency"
          value={formatLatency(data.avg_latency_ms)}
          hint="Successful samples in the recorded window"
          tone="teal"
        />
        <MetricCard
          label="Packet loss"
          value={formatLoss(data.packet_loss_percent)}
          hint="Derived from stored probe results"
          tone={
            data.packet_loss_percent === null
              ? "slate"
              : data.packet_loss_percent > 20
                ? "rose"
                : data.packet_loss_percent > 0
                  ? "amber"
                  : "green"
          }
        />
        <MetricCard
          label="Network health"
          value={score ? `${formatNumber(score.score, "", 0)}/100` : "N/A"}
          hint={score ? score.label : data.health_label}
          tone={healthTone(score?.score)}
          footer={
            score ? (
              <span className="text-slate-400">
                Latency {formatNumber(score.latency_score, "", 0)} · Loss{" "}
                {formatNumber(score.packet_loss_score, "", 0)} · Availability{" "}
                {formatNumber(score.availability_score, "", 0)}
              </span>
            ) : (
              <span className="text-slate-500">
                Requires both connectivity samples and monitoring availability.
              </span>
            )
          }
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <SectionCard
          title="Recent activity"
          description="Newest recorded discovery, connectivity, monitoring, assessment and report events."
          actions={
            <Link to="/reports" className="text-xs text-slate-400 hover:text-white">
              Reports →
            </Link>
          }
        >
          {data.recent_activity.length === 0 ? (
            <EmptyState
              title="No activity recorded yet"
              description="Run a network discovery scan or ping a discovered device. This area only shows events that actually exist in the local database."
              action={
                <Link to="/discovery" className="btn-primary">
                  Open discovery
                </Link>
              }
            />
          ) : (
            <ol className="space-y-1">
              {data.recent_activity.map((item, index) => (
                <li
                  key={`${item.activity_type}-${item.timestamp}-${index}`}
                  className="flex gap-3 rounded-lg px-2 py-2.5 transition hover:bg-white/[0.025]"
                >
                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-pulse/70" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-slate-100">{item.title}</span>
                      {item.status ? <StatusBadge value={item.status} /> : null}
                    </div>
                    <p className="mt-0.5 text-xs text-slate-400">{item.description}</p>
                  </div>
                  <time className="shrink-0 whitespace-nowrap text-[11px] text-slate-500">
                    {formatDateTime(item.timestamp)}
                  </time>
                </li>
              ))}
            </ol>
          )}
        </SectionCard>

        <div className="space-y-5">
          <SectionCard title="Current operating state" description="Values come from persisted records only.">
            <DataList
              items={[
                { label: "Last discovery scan", value: formatDateTime(data.last_scan_at) },
                { label: "Latest observation", value: formatDateTime(data.latest_observation_at) },
                { label: "Active monitoring sessions", value: formatCount(data.active_monitoring_sessions) },
                { label: "Open-port findings", value: formatCount(data.open_security_findings) },
                { label: "Generated reports", value: formatCount(data.reports_count) },
                { label: "Health label", value: displayText(data.health_label) },
              ]}
            />
            {!hasDevices ? (
              <div className="mt-4">
                <Notice tone="neutral">
                  No devices are stored yet. Discovery results depend on the local subnet, device firewalls,
                  client isolation and operating-system permissions.
                </Notice>
              </div>
            ) : null}
          </SectionCard>

          <SectionCard
            title="Network health calculation"
            description="Shown only when every required input exists."
          >
            {score ? (
              <HealthBreakdown score={score} />
            ) : (
              <p className="text-sm leading-relaxed text-slate-400">
                Health is unavailable because the required connectivity and availability inputs are
                incomplete. NetPulse does not substitute zero for missing measurements. Record successful
                probes and monitoring observations to populate the score.
              </p>
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
