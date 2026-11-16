import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  DataList,
  Dot,
  EmptyState,
  ErrorState,
  InlineSpinner,
  LoadingState,
  MetricCard,
  Notice,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "../components/ui";
import { useAsync, usePolling } from "../hooks/useAsync";
import {
  displayText,
  formatCount,
  formatDateTime,
  formatLatency,
  formatLoss,
  formatNumber,
} from "../lib/format";
import { api, ApiError, toApiError } from "../services/api";
import { useMonitoringSocket, type SocketStatus } from "../services/websocket";

function socketPresentation(status: SocketStatus): { label: string; tone: "blue" | "green" | "slate" } {
  if (status === "live") return { label: "Live WebSocket connected", tone: "green" };
  if (status === "connecting") return { label: "Connecting live updates…", tone: "blue" };
  return { label: "Live updates unavailable · polling fallback", tone: "slate" };
}

export default function DeviceDetailPage() {
  const params = useParams<{ deviceId: string }>();
  const deviceId = Number(params.deviceId);
  const validId = Number.isInteger(deviceId) && deviceId > 0;

  const deviceState = useAsync(
    () =>
      validId
        ? api.device(deviceId)
        : Promise.reject(new ApiError("INVALID_DEVICE_ID", "The device ID in the URL is not valid.")),
    [deviceId],
  );
  const sessionsState = useAsync(() => api.monitoringSessions(20), []);

  const [pingCount, setPingCount] = useState(5);
  const [pingTimeout, setPingTimeout] = useState(1000);
  const [pinging, setPinging] = useState(false);
  const [pingError, setPingError] = useState<ApiError | null>(null);
  const [pingResult, setPingResult] = useState<Awaited<ReturnType<typeof api.ping>> | null>(null);

  const [intervalSeconds, setIntervalSeconds] = useState(10);
  const [monitoringBusy, setMonitoringBusy] = useState(false);
  const [monitoringError, setMonitoringError] = useState<ApiError | null>(null);

  const socket = useMonitoringSocket((payload) => {
    if (payload.event === "monitoring.observation" && Number(payload.device_id) === deviceId) {
      deviceState.refetch();
      sessionsState.refetch();
    }
  });

  const currentSession =
    sessionsState.data?.find(
      (session) => session.status === "running" && session.device_ids.includes(deviceId),
    ) ?? null;

  usePolling(
    () => {
      deviceState.refetch();
      sessionsState.refetch();
    },
    5000,
    Boolean(currentSession),
  );

  const runPing = async () => {
    setPinging(true);
    setPingError(null);
    try {
      const response = await api.ping(deviceId, pingCount, pingTimeout);
      setPingResult(response);
      deviceState.refetch();
      sessionsState.refetch();
    } catch (reason) {
      setPingError(toApiError(reason, "The ping test could not be completed."));
    } finally {
      setPinging(false);
    }
  };

  const startMonitoring = async () => {
    setMonitoringBusy(true);
    setMonitoringError(null);
    try {
      await api.startMonitoring([deviceId], intervalSeconds);
      sessionsState.refetch();
      deviceState.refetch();
    } catch (reason) {
      setMonitoringError(toApiError(reason, "The monitoring session could not be started."));
    } finally {
      setMonitoringBusy(false);
    }
  };

  const stopMonitoring = async (sessionId: number) => {
    setMonitoringBusy(true);
    setMonitoringError(null);
    try {
      await api.stopMonitoring(sessionId);
      sessionsState.refetch();
      deviceState.refetch();
    } catch (reason) {
      setMonitoringError(toApiError(reason, "The monitoring session could not be stopped."));
    } finally {
      setMonitoringBusy(false);
    }
  };

  if (deviceState.loading && !deviceState.data) {
    return (
      <div className="space-y-6">
        <PageHeader title="Device details" description="Loading the stored device record and recent observations…" />
        <LoadingState label="Loading device details…" />
      </div>
    );
  }

  if (!deviceState.data) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Device details"
          description="The device could not be loaded."
          actions={
            <Link to="/devices" className="btn-secondary">
              Back to devices
            </Link>
          }
        />
        <ErrorState
          title="Device unavailable"
          error={
            deviceState.error
              ? { message: deviceState.error.message, code: deviceState.error.code }
              : { message: "The device record was not found." }
          }
          onRetry={deviceState.refetch}
        />
      </div>
    );
  }

  const device = deviceState.data;
  const socketView = socketPresentation(socket.status);

  return (
    <div className="space-y-6">
      <PageHeader
        title={device.hostname || device.ip_address}
        description={
          <>
            Device #{device.id} · <span className="font-mono">{device.ip_address}</span> · latest observation{" "}
            <StatusBadge value={device.latest_observation} />
          </>
        }
        actions={
          <>
            <Link to="/devices" className="btn-secondary">
              Back to devices
            </Link>
            <Link to={`/security?device=${device.id}`} className="btn-secondary">
              Security assessment
            </Link>
            <button type="button" className="btn-primary" onClick={deviceState.refetch} disabled={deviceState.loading}>
              {deviceState.loading ? "Refreshing…" : "Refresh"}
            </button>
          </>
        }
      />

      {deviceState.error ? (
        <Notice tone="danger" title="The displayed device record may be stale">
          {deviceState.error.message}
        </Notice>
      ) : null}

      <SectionCard
        title="Device record"
        description="Best-effort discovery fields. Unavailable values are shown as N/A, never zero."
        actions={<StatusBadge value={device.latest_observation} />}
      >
        <DataList
          items={[
            { label: "IP address", value: <span className="font-mono">{device.ip_address}</span> },
            { label: "Hostname", value: displayText(device.hostname) },
            { label: "MAC address", value: <span className="font-mono">{displayText(device.mac_address)}</span> },
            { label: "Vendor", value: displayText(device.vendor) },
            { label: "First seen", value: formatDateTime(device.first_seen) },
            { label: "Last seen", value: formatDateTime(device.last_seen) },
            { label: "Latest observation at", value: formatDateTime(device.latest_observation_at) },
            { label: "Latest latency", value: formatLatency(device.latest_latency_ms) },
            { label: "Latest packet loss", value: formatLoss(device.latest_packet_loss_percent) },
          ]}
        />
      </SectionCard>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <SectionCard
          title="ICMP connectivity test"
          description="A bounded batch of echo requests executed with the platform ping utility."
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="ping-count" className="field-label">
                Probes (1–20)
              </label>
              <input
                id="ping-count"
                type="number"
                min={1}
                max={20}
                className="field"
                value={pingCount}
                onChange={(event) => setPingCount(Number(event.target.value))}
                disabled={pinging}
              />
            </div>
            <div>
              <label htmlFor="ping-timeout" className="field-label">
                Timeout per probe (ms)
              </label>
              <input
                id="ping-timeout"
                type="number"
                min={100}
                max={5000}
                step={50}
                className="field"
                value={pingTimeout}
                onChange={(event) => setPingTimeout(Number(event.target.value))}
                disabled={pinging}
              />
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="btn-primary"
              onClick={runPing}
              disabled={pinging || pingCount < 1 || pingCount > 20 || pingTimeout < 100 || pingTimeout > 5000}
            >
              {pinging ? <InlineSpinner label="Running probes…" /> : "Run ping test"}
            </button>
            <span className="text-xs text-slate-500">Requests run sequentially with a subprocess timeout.</span>
          </div>

          {pingError ? (
            <div className="mt-3">
              <Notice tone="danger" title="Ping test failed">
                {pingError.message}
                {pingError.code === "PING_UTILITY_UNAVAILABLE" ? (
                  <div className="mt-1 opacity-80">
                    The platform ping utility is unavailable. Install or enable ping and try again.
                  </div>
                ) : null}
              </Notice>
            </div>
          ) : null}

          {pingResult ? (
            <div className="mt-4 space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <MetricCard
                  label="Packet loss"
                  value={formatLoss(pingResult.packet_loss_percent)}
                  hint={`${formatCount(pingResult.probes_received)} / ${formatCount(pingResult.probes_sent)} replies`}
                  tone={pingResult.probes_received === 0 ? "rose" : "green"}
                />
                <MetricCard
                  label="Average latency"
                  value={formatLatency(pingResult.avg_latency_ms)}
                  hint={`Min ${formatLatency(pingResult.min_latency_ms)} · Max ${formatLatency(pingResult.max_latency_ms)}`}
                  tone="teal"
                />
                <MetricCard
                  label="Jitter"
                  value={pingResult.jitter_ms === null ? "N/A" : formatNumber(pingResult.jitter_ms, "ms", 1)}
                  hint="Mean absolute difference between successful samples"
                  tone="blue"
                />
              </div>

              {pingResult.message ? (
                <Notice tone="warning" title="No ICMP replies observed">
                  {pingResult.message}
                </Notice>
              ) : null}

              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Result</th>
                      <th>Latency</th>
                      <th>Tested at</th>
                      <th>Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pingResult.probes.map((probe) => (
                      <tr key={probe.sequence_number}>
                        <td className="text-slate-500">{probe.sequence_number}</td>
                        <td>
                          <span className={probe.success ? "chip border-emerald-400/25 bg-emerald-400/10 text-emerald-200" : "chip border-amber-400/25 bg-amber-400/10 text-amber-200"}>
                            {probe.success ? "Reply" : "No reply"}
                          </span>
                        </td>
                        <td>{formatLatency(probe.latency_ms)}</td>
                        <td className="whitespace-nowrap text-xs text-slate-400">{formatDateTime(probe.tested_at)}</td>
                        <td className="text-xs text-slate-400">{displayText(probe.error_message)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          <p className="mt-4 text-xs leading-relaxed text-slate-500">
            A failed ICMP probe does not prove that the device is powered off or absent. Firewalls and network
            policy commonly block echo requests. Failed probes are stored with a null latency, not zero.
          </p>
        </SectionCard>

        <SectionCard
          title="Periodic monitoring"
          description="One bounded session per device, with timestamped ICMP observations."
          actions={
            <span className="chip border-white/10 bg-white/[0.04] text-slate-300">
              <Dot tone={socketView.tone} pulse={socket.status === "live"} />
              {socketView.label}
            </span>
          }
        >
          {sessionsState.error ? (
            <div className="mb-3">
              <Notice tone="danger" title="Monitoring sessions unavailable">
                {sessionsState.error.message}
              </Notice>
            </div>
          ) : null}

          {currentSession ? (
            <div className="space-y-3">
              <DataList
                items={[
                  { label: "Session", value: `#${currentSession.session_id}` },
                  { label: "Status", value: <StatusBadge value={currentSession.status} /> },
                  { label: "Interval", value: `${formatCount(currentSession.interval_seconds)} s` },
                  { label: "Started", value: formatDateTime(currentSession.started_at) },
                  { label: "Observations", value: formatCount(currentSession.observation_count) },
                  { label: "Availability", value: formatLoss(currentSession.availability_percent) },
                  { label: "Successful checks", value: formatCount(currentSession.success_count) },
                  { label: "Failed checks", value: formatCount(currentSession.failure_count) },
                ]}
              />
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => stopMonitoring(currentSession.session_id)}
                  disabled={monitoringBusy}
                >
                  {monitoringBusy ? <InlineSpinner label="Stopping…" /> : "Stop monitoring"}
                </button>
                <span className="text-xs text-slate-500">
                  Refreshing every 5 seconds while this session is running.
                </span>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label htmlFor="monitor-interval" className="field-label">
                  Observation interval (5–3600 seconds)
                </label>
                <input
                  id="monitor-interval"
                  type="number"
                  min={5}
                  max={3600}
                  className="field"
                  value={intervalSeconds}
                  onChange={(event) => setIntervalSeconds(Number(event.target.value))}
                  disabled={monitoringBusy}
                />
              </div>
              <button
                type="button"
                className="btn-primary"
                onClick={startMonitoring}
                disabled={monitoringBusy || intervalSeconds < 5 || intervalSeconds > 3600}
              >
                {monitoringBusy ? <InlineSpinner label="Starting…" /> : "Start monitoring"}
              </button>
              <p className="text-xs leading-relaxed text-slate-500">
                Starting a session records ICMP observations only. Availability is the proportion of successful
                monitoring checks in the session, not guaranteed end-to-end service uptime.
              </p>
            </div>
          )}

          {monitoringError ? (
            <div className="mt-3">
              <Notice tone="danger" title="Monitoring action failed">
                {monitoringError.message}
              </Notice>
            </div>
          ) : null}

          {sessionsState.data && sessionsState.data.length > 0 ? (
            <div className="mt-5 border-t border-white/[0.07] pt-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Recent sessions</h3>
              <div className="mt-2 space-y-2">
                {sessionsState.data.slice(0, 5).map((session) => (
                  <div
                    key={session.session_id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/[0.07] bg-white/[0.02] px-3 py-2 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-200">#{session.session_id}</span>
                      <StatusBadge value={session.status} />
                      <span className="text-slate-500">{formatCount(session.observation_count)} checks</span>
                    </div>
                    <div className="flex items-center gap-3 text-slate-500">
                      <span>{formatLoss(session.availability_percent)} availability</span>
                      <span>{formatDateTime(session.started_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </SectionCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="Recent ping tests" description="The five most recent tests persisted for this device.">
          {device.recent_ping_tests.length === 0 ? (
            <EmptyState title="No ping tests recorded" description="Run an ICMP test above to create the first stored measurement." />
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Started</th>
                    <th>Replies</th>
                    <th>Loss</th>
                    <th>Avg</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {device.recent_ping_tests.map((test) => (
                    <tr key={test.id}>
                      <td className="whitespace-nowrap text-xs text-slate-400">{formatDateTime(test.started_at)}</td>
                      <td>
                        {formatCount(test.probes_received)} / {formatCount(test.probes_sent)}
                      </td>
                      <td>{formatLoss(test.packet_loss_percent)}</td>
                      <td>{formatLatency(test.avg_latency_ms)}</td>
                      <td>
                        <StatusBadge value={test.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard title="Recent monitoring observations" description="The ten most recent observations for this device.">
          {device.recent_observations.length === 0 ? (
            <EmptyState title="No monitoring observations" description="Start a monitoring session to persist periodic observations." />
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Observed</th>
                    <th>Result</th>
                    <th>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {device.recent_observations.map((observation) => (
                    <tr key={observation.id}>
                      <td className="whitespace-nowrap text-xs text-slate-400">
                        {formatDateTime(observation.observed_at)}
                      </td>
                      <td>
                        <StatusBadge value={observation.observation} />
                      </td>
                      <td>{formatLatency(observation.latency_ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>

      <SectionCard title="Recent security assessments" description="TCP service exposure checks recorded for this device.">
        {device.recent_security_scans.length === 0 ? (
          <EmptyState
            title="No security assessments recorded"
            description="Open the security page to run an authorized, allowlisted TCP service check."
            action={
              <Link to={`/security?device=${device.id}`} className="btn-primary">
                Open security assessment
              </Link>
            }
          />
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Scan</th>
                  <th>Profile</th>
                  <th>Started</th>
                  <th>Completed</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {device.recent_security_scans.map((scan) => (
                  <tr key={scan.id}>
                    <td>#{scan.id}</td>
                    <td>{displayText(scan.profile_name)}</td>
                    <td className="whitespace-nowrap text-xs text-slate-400">{formatDateTime(scan.started_at)}</td>
                    <td className="whitespace-nowrap text-xs text-slate-400">{formatDateTime(scan.completed_at)}</td>
                    <td>
                      <StatusBadge value={scan.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  );
}
