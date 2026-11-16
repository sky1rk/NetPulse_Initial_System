import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  DataList,
  EmptyState,
  ErrorState,
  LoadingState,
  Notice,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { displayText, formatCount, formatDateTime } from "../lib/format";
import { api, toApiError, type ApiError } from "../services/api";

export default function DiscoveryPage() {
  const info = useAsync(() => api.networkInfo(), []);
  const [range, setRange] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<Awaited<ReturnType<typeof api.scanNetwork>> | null>(null);

  useEffect(() => {
    if (info.data?.network_cidr) {
      setRange(info.data.network_cidr);
    }
  }, [info.data?.network_cidr]);

  const runScan = async () => {
    setScanning(true);
    setScanError(null);
    setResult(null);
    try {
      const response = await api.scanNetwork(range.trim() || null, confirmed);
      setResult(response);
    } catch (reason) {
      setScanError(toApiError(reason, "The discovery scan could not be started."));
    } finally {
      setScanning(false);
    }
  };

  const warnings = info.data?.warnings ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Network discovery"
        description="Identify reachable hosts on the detected local subnet using a bounded ping sweep and the operating-system ARP/neighbour table."
        actions={
          <button type="button" className="btn-secondary" onClick={info.refetch} disabled={info.loading}>
            {info.loading ? "Refreshing…" : "Refresh network information"}
          </button>
        }
      />

      {info.loading && !info.data ? <LoadingState label="Detecting local network interfaces…" /> : null}

      {info.error && !info.data ? (
        <ErrorState
          title="Network information unavailable"
          error={{ message: info.error.message, code: info.error.code }}
          onRetry={info.refetch}
        />
      ) : null}

      {info.error && info.data ? (
        <Notice tone="danger" title="Network information may be stale">
          {info.error.message}
        </Notice>
      ) : null}

      {info.data ? (
        <>
          {warnings.length > 0 ? (
            <Notice tone="warning" title="Interface selection warnings">
              <ul className="list-inside list-disc space-y-1">
                {warnings.map((warning, index) => (
                  <li key={`${warning}-${index}`}>{warning}</li>
                ))}
              </ul>
            </Notice>
          ) : null}

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
            <SectionCard
              title="Detected local network"
              description="Read-only values reported by the operating system. Unavailable fields are shown as N/A."
            >
              <DataList
                items={[
                  { label: "Interface", value: displayText(info.data.interface_name) },
                  { label: "Local IPv4", value: displayText(info.data.local_ipv4) },
                  { label: "Subnet mask", value: displayText(info.data.subnet_mask) },
                  { label: "Network CIDR", value: displayText(info.data.network_cidr) },
                  { label: "Default gateway", value: displayText(info.data.default_gateway) },
                ]}
              />
              {info.data.candidates.length > 1 ? (
                <div className="mt-5 border-t border-white/[0.07] pt-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Interface candidates
                  </h3>
                  <div className="table-scroll mt-2">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Interface</th>
                          <th>IPv4</th>
                          <th>CIDR</th>
                          <th>State</th>
                        </tr>
                      </thead>
                      <tbody>
                        {info.data.candidates.map((candidate, index) => (
                          <tr key={`${candidate.interface_name ?? "interface"}-${index}`}>
                            <td>{displayText(candidate.interface_name)}</td>
                            <td className="font-mono text-xs">{displayText(candidate.local_ipv4)}</td>
                            <td className="font-mono text-xs">{displayText(candidate.network_cidr)}</td>
                            <td>
                              <StatusBadge
                                value={candidate.is_up === null ? null : candidate.is_up ? "ok" : "stopped"}
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}
            </SectionCard>

            <SectionCard
              title="Run a discovery scan"
              description="The scan is bounded by the backend's host limit, concurrency limit and per-host timeout."
            >
              <div className="space-y-4">
                <div>
                  <label htmlFor="scan-range" className="field-label">
                    Proposed scan range (CIDR)
                  </label>
                  <input
                    id="scan-range"
                    className="field font-mono"
                    value={range}
                    onChange={(event) => setRange(event.target.value)}
                    placeholder={info.data.network_cidr ?? "192.168.1.0/24"}
                    spellCheck={false}
                    disabled={scanning}
                  />
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
                    Defaults to the detected local subnet. The backend rejects public ranges and, unless custom
                    scan mode is enabled, ranges outside the detected local subnet.
                  </p>
                </div>

                <label className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.025] p-3 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 rounded border-white/20 bg-ink-900 accent-blue-500"
                    checked={confirmed}
                    onChange={(event) => setConfirmed(event.target.checked)}
                    disabled={scanning}
                  />
                  <span>
                    I confirm that I own this network or have explicit authorization to assess it. I understand
                    that hostname and MAC values are best-effort and that unobserved hosts are not necessarily
                    absent.
                  </span>
                </label>

                {scanError ? (
                  <Notice tone="danger" title="Scan could not run">
                    {scanError.message}
                  </Notice>
                ) : null}

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={runScan}
                    disabled={scanning || !confirmed}
                  >
                    {scanning ? "Scanning local subnet…" : "Start authorized scan"}
                  </button>
                  <span className="text-xs text-slate-500">
                    {confirmed ? "Authorization confirmed." : "Confirmation is required before scanning."}
                  </span>
                </div>

                <div className="rounded-lg border border-white/[0.07] bg-ink-950/40 p-3 text-xs leading-relaxed text-slate-400">
                  Discovery may be limited by host firewalls, ICMP filtering, Wi-Fi client isolation, VLAN
                  boundaries and operating-system permissions. MAC addresses are only available from local-link
                  neighbour data.
                </div>
              </div>
            </SectionCard>
          </div>
        </>
      ) : null}

      {result ? (
        <SectionCard
          title="Scan results"
          description={`Scan #${result.scan_id} · ${result.network_cidr}`}
          actions={<StatusBadge value={result.status} />}
        >
          <div className="mb-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
              <div className="text-[11px] uppercase tracking-wider text-slate-500">Discovered</div>
              <div className="mt-1 text-xl font-semibold text-white">{formatCount(result.discovered_count)}</div>
            </div>
            <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
              <div className="text-[11px] uppercase tracking-wider text-slate-500">Started</div>
              <div className="mt-1 text-sm text-slate-200">{formatDateTime(result.started_at)}</div>
            </div>
            <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
              <div className="text-[11px] uppercase tracking-wider text-slate-500">Completed</div>
              <div className="mt-1 text-sm text-slate-200">{formatDateTime(result.completed_at)}</div>
            </div>
          </div>

          {result.warnings.length > 0 ? (
            <div className="mb-4">
              <Notice tone="warning" title="Partial results and warnings">
                <ul className="list-inside list-disc space-y-1">
                  {result.warnings.map((warning, index) => (
                    <li key={`${warning}-${index}`}>{warning}</li>
                  ))}
                </ul>
              </Notice>
            </div>
          ) : null}

          {result.devices.length === 0 ? (
            <EmptyState
              title="No hosts were observed"
              description="That does not prove the subnet is empty. ICMP may be blocked, clients may be isolated, or the operating system may restrict neighbour-table access. Check the warnings above before drawing conclusions."
            />
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>IP address</th>
                    <th>Hostname</th>
                    <th>MAC address</th>
                    <th>Observation</th>
                    <th>Last seen</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {result.devices.map((device) => (
                    <tr key={device.id}>
                      <td className="font-mono text-xs text-slate-100">{device.ip_address}</td>
                      <td>{displayText(device.hostname)}</td>
                      <td className="font-mono text-xs">{displayText(device.mac_address)}</td>
                      <td>
                        <StatusBadge value={device.observation} />
                      </td>
                      <td className="whitespace-nowrap text-xs text-slate-400">
                        {formatDateTime(device.last_seen)}
                      </td>
                      <td className="text-right">
                        <Link className="link whitespace-nowrap text-xs" to={`/devices/${device.id}`}>
                          Device details
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      ) : null}

      {!result && !scanning ? (
        <Notice tone="neutral" title="A scan has not been run in this session">
          Results from earlier scans remain available in the device inventory. A missing host on a future scan is
          an observation, not proof that it is offline.
        </Notice>
      ) : null}
    </div>
  );
}
