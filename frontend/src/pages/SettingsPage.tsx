import { useMemo } from "react";

import {
  DataList,
  ErrorState,
  LoadingState,
  Notice,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { displayText, formatCount, formatDateTime } from "../lib/format";
import { API_BASE, WS_BASE, api } from "../services/api";

const DEFAULT_LIMITS = [
  ["Discovery range", "Detected local subnet only (custom range mode disabled by default)"],
  ["Maximum scan hosts", "256 addresses"],
  ["Scan concurrency / timeout", "32 workers · 600 ms per host"],
  ["Ping probes", "Default 5 · maximum 20"],
  ["Ping timeout", "100–5000 ms"],
  ["Monitoring interval", "5–3600 seconds · maximum 25 devices per session"],
  ["Security assessment", "800 ms connection timeout · concurrency 4 · allowlisted ports only"],
  ["Health score weights", "40% latency · 35% packet loss · 25% availability"],
];

export default function SettingsPage() {
  const health = useAsync(() => api.health(), []);
  const network = useAsync(() => api.networkInfo(), []);
  const profiles = useAsync(() => api.securityProfiles(), []);

  const allowedPorts = useMemo(() => {
    const ports = new Set<number>();
    (profiles.data ?? []).forEach((profile) => profile.ports.forEach((port) => ports.add(port.port)));
    return [...ports].sort((a, b) => a - b);
  }, [profiles.data]);

  const refreshAll = () => {
    health.refetch();
    network.refetch();
    profiles.refetch();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings & runtime"
        description="Read-only visibility into the local NetPulse deployment. Operational settings come from backend environment variables."
        actions={
          <button
            type="button"
            className="btn-secondary"
            onClick={refreshAll}
            disabled={health.loading || network.loading || profiles.loading}
          >
            {health.loading || network.loading || profiles.loading ? "Refreshing…" : "Refresh runtime"}
          </button>
        }
      />

      <Notice tone="warning" title="The UI does not edit backend configuration">
        Settings are controlled through <span className="font-mono">NETPULSE_*</span> environment variables in the
        repository or backend <span className="font-mono">.env</span> file. Change them there and restart the
        backend. This page never pretends to apply changes it cannot make.
      </Notice>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="Backend connection" description="Live values from the health endpoint and frontend build configuration.">
          {health.loading && !health.data ? <LoadingState label="Checking backend…" /> : null}
          {health.error && !health.data ? (
            <ErrorState
              title="Backend health check failed"
              error={{ message: health.error.message, code: health.error.code }}
              onRetry={health.refetch}
            />
          ) : null}
          {health.data ? (
            <DataList
              items={[
                { label: "Status", value: <StatusBadge value={health.data.status} /> },
                { label: "Service", value: health.data.service },
                { label: "Version", value: health.data.version },
                { label: "Database", value: <StatusBadge value={health.data.database} /> },
                { label: "Health timestamp", value: formatDateTime(health.data.timestamp) },
                { label: "API base URL", value: <span className="break-all font-mono text-xs">{API_BASE}</span> },
                { label: "WebSocket base URL", value: <span className="break-all font-mono text-xs">{WS_BASE}</span> },
                {
                  label: "API documentation",
                  value: (
                    <a className="link text-xs" href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">
                      Open local FastAPI docs ↗
                    </a>
                  ),
                },
              ]}
            />
          ) : null}
          {health.error && health.data ? (
            <div className="mt-3">
              <Notice tone="danger" title="Health check failed; values may be stale">
                {health.error.message}
              </Notice>
            </div>
          ) : null}
        </SectionCard>

        <SectionCard title="Detected network context" description="The interface and subnet used for default discovery scope.">
          {network.loading && !network.data ? <LoadingState label="Reading network information…" /> : null}
          {network.error && !network.data ? (
            <ErrorState
              title="Network information unavailable"
              error={{ message: network.error.message, code: network.error.code }}
              onRetry={network.refetch}
            />
          ) : null}
          {network.data ? (
            <DataList
              items={[
                { label: "Interface", value: displayText(network.data.interface_name) },
                { label: "Local IPv4", value: <span className="font-mono">{displayText(network.data.local_ipv4)}</span> },
                { label: "Subnet mask", value: displayText(network.data.subnet_mask) },
                { label: "Network CIDR", value: <span className="font-mono">{displayText(network.data.network_cidr)}</span> },
                { label: "Default gateway", value: <span className="font-mono">{displayText(network.data.default_gateway)}</span> },
                { label: "Interface candidates", value: formatCount(network.data.candidates.length) },
              ]}
            />
          ) : null}
          {network.data?.warnings.length ? (
            <div className="mt-3">
              <Notice tone="warning" title="Detection warnings">
                <ul className="list-inside list-disc space-y-1">
                  {network.data.warnings.map((warning, index) => (
                    <li key={`${warning}-${index}`}>{warning}</li>
                  ))}
                </ul>
              </Notice>
            </div>
          ) : null}
        </SectionCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard
          title="Documented bounded defaults"
          description="These are the project defaults. The running backend may be configured differently through environment variables."
        >
          <dl className="divide-y divide-white/[0.06]">
            {DEFAULT_LIMITS.map(([label, value]) => (
              <div key={label} className="flex flex-col gap-0.5 py-2.5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-4">
                <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</dt>
                <dd className="text-sm text-slate-300 sm:text-right">{value}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-3 space-y-1.5 rounded-lg border border-white/[0.07] bg-white/[0.02] p-3 text-[11px] text-slate-500">
            <p>Common variables: NETPULSE_DATABASE_URL, NETPULSE_MAX_SCAN_HOSTS, NETPULSE_SCAN_CONCURRENCY, NETPULSE_PING_MAX_COUNT, NETPULSE_MONITORING_MIN_INTERVAL_SECONDS, NETPULSE_ALLOWED_PORTS, NETPULSE_LOG_LEVEL.</p>
            <p>Frontend API target: VITE_API_BASE_URL (set in frontend/.env).</p>
          </div>
        </SectionCard>

        <SectionCard title="Local data and safety boundaries" description="What this deployment does and does not do.">
          <div className="space-y-3 text-sm leading-relaxed text-slate-400">
            <p>
              <span className="font-medium text-slate-200">Persistence.</span> SQLite by default at{" "}
              <span className="font-mono text-xs">backend/data/netpulse.db</span>; generated reports at{" "}
              <span className="font-mono text-xs">backend/data/reports/</span>. Paths can be overridden by backend
              environment variables.
            </p>
            <p>
              <span className="font-medium text-slate-200">No accounts or cloud services.</span> There is no
              authentication layer, cloud sync, external telemetry, machine learning, or AI diagnosis. The app is
              intended for a trusted local deployment.
            </p>
            <p>
              <span className="font-medium text-slate-200">No exploitation.</span> Security assessment is a limited
              TCP connection check. It does not attempt exploits, credential testing, brute force, stealth or
              evasion.
            </p>
            <p>
              <span className="font-medium text-slate-200">No invented data.</span> Missing MAC addresses,
              hostnames, latencies and loss values remain unavailable. A failed ping is not recorded as zero
              latency and is not proof that a device is offline.
            </p>
            <p>
              <span className="font-medium text-slate-200">Authorization required.</span> Discovery and security
              checks require explicit confirmation. Discovery is restricted to private local ranges, and custom
              ranges are disabled unless the backend operator deliberately enables them.
            </p>
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title="Current security port allowlist"
        description="Union of ports exposed by the configured profiles. The backend still enforces its own allowlist."
      >
        {profiles.loading && !profiles.data ? <LoadingState label="Loading port profiles…" /> : null}
        {profiles.error && !profiles.data ? (
          <ErrorState
            title="Port profiles unavailable"
            error={{ message: profiles.error.message, code: profiles.error.code }}
            onRetry={profiles.refetch}
          />
        ) : null}
        {profiles.data ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-1.5">
              {allowedPorts.length > 0 ? (
                allowedPorts.map((port) => (
                  <span key={port} className="chip border-white/10 bg-white/[0.04] text-slate-300">
                    {port}
                  </span>
                ))
              ) : (
                <span className="text-sm text-slate-500">No ports are currently allowed by the profiles.</span>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {profiles.data.map((profile) => (
                <div key={profile.name} className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
                  <div className="text-sm font-medium text-slate-200">{profile.name.replaceAll("_", " ")}</div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">{profile.description}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {profile.ports.map((port) => (
                      <span key={port.port} className="rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
                        {port.port}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs leading-relaxed text-slate-500">
              Service labels are conventional mappings. An accepted TCP connection does not verify the
              application or indicate a vulnerability.
            </p>
          </div>
        ) : null}
      </SectionCard>
    </div>
  );
}
