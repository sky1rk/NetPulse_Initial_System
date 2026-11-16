import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
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
import { useAsync } from "../hooks/useAsync";
import { displayText, formatCount, formatDateTime } from "../lib/format";
import { api, toApiError, type ApiError } from "../services/api";

const DISCLAIMER =
  "An open port is an observation, not proof of a vulnerability. This is a limited TCP service exposure check, not a full vulnerability assessment.";

export default function SecurityPage() {
  const [searchParams] = useSearchParams();
  const devicesState = useAsync(() => api.devices({ limit: 500 }), []);
  const profilesState = useAsync(() => api.securityProfiles(), []);

  const requestedDevice = Number(searchParams.get("device"));
  const [deviceId, setDeviceId] = useState<number | "">(
    Number.isInteger(requestedDevice) && requestedDevice > 0 ? requestedDevice : "",
  );
  const [profileName, setProfileName] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<Awaited<ReturnType<typeof api.securityScan>> | null>(null);
  const [historyScope, setHistoryScope] = useState<number | "">("");

  const findingsState = useAsync(
    () =>
      api.securityFindings({
        device_id: historyScope === "" ? undefined : historyScope,
        limit: 200,
      }),
    [historyScope],
  );

  useEffect(() => {
    const next = Number(searchParams.get("device"));
    if (Number.isInteger(next) && next > 0) {
      setDeviceId(next);
    }
  }, [searchParams]);

  useEffect(() => {
    if (!profileName && profilesState.data && profilesState.data.length > 0) {
      setProfileName(profilesState.data[0].name);
    }
  }, [profileName, profilesState.data]);

  useEffect(() => {
    setConfirmed(false);
  }, [deviceId, profileName]);

  const selectedProfile = useMemo(
    () => profilesState.data?.find((profile) => profile.name === profileName) ?? null,
    [profilesState.data, profileName],
  );

  const selectedDevice = useMemo(
    () => devicesState.data?.items.find((device) => device.id === deviceId) ?? null,
    [devicesState.data, deviceId],
  );

  const runScan = async () => {
    if (deviceId === "") return;
    setScanning(true);
    setScanError(null);
    setResult(null);
    try {
      const ports = selectedProfile ? selectedProfile.ports.map((port) => port.port) : null;
      const response = await api.securityScan(Number(deviceId), ports, confirmed, profileName || null);
      setResult(response);
      setHistoryScope(Number(deviceId));
      findingsState.refetch();
    } catch (reason) {
      setScanError(toApiError(reason, "The TCP service assessment could not be completed."));
    } finally {
      setScanning(false);
      setConfirmed(false);
    }
  };

  const openCount = result?.findings.filter((finding) => finding.state === "open").length ?? 0;
  const testedCount = result?.findings.length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Security assessment"
        description="A limited TCP connection check against a small allowlist of common service ports on devices you are authorized to assess."
        actions={
          <button type="button" className="btn-secondary" onClick={findingsState.refetch} disabled={findingsState.loading}>
            {findingsState.loading ? "Refreshing…" : "Refresh findings"}
          </button>
        }
      />

      <Notice tone="warning" title="Authorization and scope">
        Only assess devices that you own or have explicit permission to test. Ports are restricted to the
        backend allowlist, timeouts are short and concurrency is bounded. Exploitation, credential guessing,
        stealth and evasion are not implemented.
      </Notice>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <SectionCard
          title="Assessment target"
          description="Choose one stored device and a predefined port profile."
        >
          {devicesState.loading && !devicesState.data ? (
            <LoadingState label="Loading devices…" />
          ) : devicesState.error && !devicesState.data ? (
            <ErrorState
              title="Device list unavailable"
              error={{ message: devicesState.error.message, code: devicesState.error.code }}
              onRetry={devicesState.refetch}
            />
          ) : (
            <div className="space-y-4">
              <div>
                <label htmlFor="security-device" className="field-label">
                  Target device
                </label>
                <select
                  id="security-device"
                  className="field"
                  value={deviceId}
                  onChange={(event) => setDeviceId(event.target.value ? Number(event.target.value) : "")}
                  disabled={scanning}
                >
                  <option value="">Select a device…</option>
                  {(devicesState.data?.items ?? []).map((device) => (
                    <option key={device.id} value={device.id}>
                      {device.ip_address}
                      {device.hostname ? ` · ${device.hostname}` : ""}
                    </option>
                  ))}
                </select>
                {!devicesState.loading && (devicesState.data?.items.length ?? 0) === 0 ? (
                  <p className="mt-1.5 text-xs text-slate-500">
                    No devices are stored. Run a discovery scan first; testing arbitrary addresses is not
                    supported.
                  </p>
                ) : null}
              </div>

              <div>
                <label htmlFor="security-profile" className="field-label">
                  Port profile
                </label>
                <select
                  id="security-profile"
                  className="field"
                  value={profileName}
                  onChange={(event) => setProfileName(event.target.value)}
                  disabled={scanning || profilesState.loading}
                >
                  {(profilesState.data ?? []).map((profile) => (
                    <option key={profile.name} value={profile.name}>
                      {profile.name.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
                {profilesState.error ? (
                  <p className="mt-1.5 text-xs text-rose-300">
                    Port profiles unavailable: {profilesState.error.message}
                  </p>
                ) : null}
              </div>

              {selectedProfile ? (
                <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
                  <p className="text-sm text-slate-300">{selectedProfile.description}</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {selectedProfile.ports.map((port) => (
                      <span key={port.port} className="chip border-white/10 bg-white/[0.04] text-slate-300">
                        {port.port} · {port.service_name}
                      </span>
                    ))}
                  </div>
                  <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
                    Service names are conventional labels only. The actual application on an open port is not
                    verified.
                  </p>
                </div>
              ) : null}

              {selectedDevice ? (
                <div className="rounded-lg border border-white/[0.07] bg-ink-950/40 p-3 text-xs text-slate-400">
                  Target: <span className="font-mono text-slate-200">{selectedDevice.ip_address}</span>
                  {selectedDevice.hostname ? ` · ${selectedDevice.hostname}` : ""}
                </div>
              ) : null}

              <label className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.025] p-3 text-sm text-slate-300">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-white/20 bg-ink-900 accent-blue-500"
                  checked={confirmed}
                  onChange={(event) => setConfirmed(event.target.checked)}
                  disabled={scanning || deviceId === ""}
                />
                <span>
                  I confirm that I am authorized to perform a TCP service check against this device for this
                  assessment.
                </span>
              </label>

              {scanError ? (
                <Notice tone="danger" title="Assessment could not run">
                  {scanError.message}
                </Notice>
              ) : null}

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className="btn-primary"
                  onClick={runScan}
                  disabled={scanning || !confirmed || deviceId === "" || !selectedProfile}
                >
                  {scanning ? <InlineSpinner label="Checking selected ports…" /> : "Run authorized assessment"}
                </button>
                <span className="text-xs text-slate-500">
                  {deviceId === "" ? "Select a device first." : "Confirmation is required for each assessment."}
                </span>
              </div>
            </div>
          )}
        </SectionCard>

        <SectionCard title="Why this is limited" description="Scope boundaries you should communicate in the report or demonstration.">
          <ul className="space-y-3 text-sm leading-relaxed text-slate-400">
            <li>
              <span className="font-medium text-slate-200">TCP observations only.</span> The check records whether
              a connection succeeds, is refused, times out, or raises an execution error.
            </li>
            <li>
              <span className="font-medium text-slate-200">No vulnerability claim.</span> An open port means a
              service accepted a TCP connection. It does not establish a vulnerability, version, or exploit path.
            </li>
            <li>
              <span className="font-medium text-slate-200">No secure-device claim.</span> No open ports in the
              selected profile only means none were observed among those ports.
            </li>
            <li>
              <span className="font-medium text-slate-200">Allowlist enforced.</span> Only ports configured by the
              backend can be tested. Client input cannot expand the list.
            </li>
            <li>
              <span className="font-medium text-slate-200">Recommendations are rule-based.</span> They are derived
              from the observed port state and do not establish a root cause.
            </li>
          </ul>
        </SectionCard>
      </div>

      {result ? (
        <SectionCard
          title="Assessment result"
          description={`Scan #${result.scan_id} · profile: ${result.profile_name.replaceAll("_", " ")}`}
          actions={<StatusBadge value={result.status} />}
        >
          <div className="mb-4 grid gap-3 sm:grid-cols-3">
            <MetricCard label="Open ports observed" value={formatCount(openCount)} hint={`${formatCount(testedCount)} ports tested`} tone={openCount > 0 ? "amber" : "green"} />
            <MetricCard label="Started" value={formatDateTime(result.started_at)} tone="blue" />
            <MetricCard label="Completed" value={formatDateTime(result.completed_at)} tone="slate" />
          </div>

          <Notice tone="warning" title="Interpretation">
            {result.disclaimer || DISCLAIMER}
          </Notice>

          {result.warnings.length > 0 ? (
            <div className="mt-3">
              <Notice tone="neutral" title="Warnings">
                <ul className="list-inside list-disc space-y-1">
                  {result.warnings.map((warning, index) => (
                    <li key={`${warning}-${index}`}>{warning}</li>
                  ))}
                </ul>
              </Notice>
            </div>
          ) : null}

          {result.findings.length === 0 ? (
            <div className="mt-4">
              <EmptyState
                title="No findings were recorded"
                description="The assessment completed without stored findings. This does not establish that the device is secure."
              />
            </div>
          ) : (
            <div className="table-scroll mt-4">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Port</th>
                    <th>Protocol</th>
                    <th>Observed state</th>
                    <th>Common service label</th>
                    <th>Review priority</th>
                    <th>Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {result.findings.map((finding) => (
                    <tr key={`${finding.port}-${finding.protocol}`}>
                      <td className="font-mono text-xs text-slate-100">{finding.port}</td>
                      <td className="uppercase text-xs">{finding.protocol}</td>
                      <td>
                        <StatusBadge value={finding.state} />
                      </td>
                      <td>{displayText(finding.service_name)}</td>
                      <td>
                        <StatusBadge value={finding.severity} />
                      </td>
                      <td className="max-w-md text-xs leading-relaxed text-slate-400">
                        {displayText(finding.recommendation)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      ) : null}

      <SectionCard
        title="Recorded findings"
        description="Stored observations from completed and previous assessments. Timeouts are not labelled as definitively filtered."
        actions={
          <div className="flex items-center gap-2">
            <label htmlFor="history-scope" className="text-xs text-slate-500">
              Scope
            </label>
            <select
              id="history-scope"
              className="field w-auto py-1.5 text-xs"
              value={historyScope}
              onChange={(event) => setHistoryScope(event.target.value ? Number(event.target.value) : "")}
            >
              <option value="">All devices</option>
              {(devicesState.data?.items ?? []).map((device) => (
                <option key={device.id} value={device.id}>
                  {device.ip_address}
                </option>
              ))}
            </select>
          </div>
        }
      >
        {findingsState.loading && !findingsState.data ? (
          <LoadingState label="Loading stored findings…" />
        ) : findingsState.error && !findingsState.data ? (
          <ErrorState
            title="Findings unavailable"
            error={{ message: findingsState.error.message, code: findingsState.error.code }}
            onRetry={findingsState.refetch}
          />
        ) : (findingsState.data?.items.length ?? 0) === 0 ? (
          <EmptyState
            title="No stored findings"
            description="Run an authorized assessment, or clear the scope filter, to see stored TCP observations."
            action={
              (devicesState.data?.items.length ?? 0) > 0 ? (
                <button type="button" className="btn-secondary" onClick={() => setHistoryScope("")} disabled={historyScope === ""}>
                  Clear scope
                </button>
              ) : (
                <Link to="/discovery" className="btn-primary">
                  Discover devices
                </Link>
              )
            }
          />
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Device</th>
                  <th>Port</th>
                  <th>State</th>
                  <th>Service label</th>
                  <th>Priority</th>
                  <th>Scanned</th>
                  <th>Scan status</th>
                </tr>
              </thead>
              <tbody>
                {findingsState.data?.items.map((finding) => (
                  <tr key={finding.id}>
                    <td>
                      <Link to={`/devices/${finding.device_id}`} className="font-mono text-xs text-pulse-soft hover:text-white">
                        {finding.device_ip}
                      </Link>
                    </td>
                    <td className="font-mono text-xs">{finding.port}</td>
                    <td>
                      <StatusBadge value={finding.state} />
                    </td>
                    <td>{displayText(finding.service_name)}</td>
                    <td>
                      <StatusBadge value={finding.severity} />
                    </td>
                    <td className="whitespace-nowrap text-xs text-slate-400">{formatDateTime(finding.scanned_at)}</td>
                    <td>
                      <StatusBadge value={finding.scan_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-3 text-[11px] leading-relaxed text-slate-500">{DISCLAIMER}</p>
      </SectionCard>
    </div>
  );
}
