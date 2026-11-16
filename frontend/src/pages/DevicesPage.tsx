import { useState } from "react";
import { Link } from "react-router-dom";

import {
  EmptyState,
  ErrorState,
  LoadingState,
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
} from "../lib/format";
import { api } from "../services/api";

const STATUS_OPTIONS = [
  { value: "", label: "All observations" },
  { value: "responding", label: "Responding" },
  { value: "no_icmp_response", label: "No ICMP response" },
  { value: "not_tested", label: "Not tested" },
  { value: "error", label: "Probe error" },
];

export default function DevicesPage() {
  const [status, setStatus] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const { data, loading, error, refetch } = useAsync(
    () =>
      api.devices({
        status: status || undefined,
        search: search || undefined,
        limit: 100,
      }),
    [status, search],
  );

  const hasFilters = Boolean(status || search);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Device inventory"
        description="Devices recorded by discovery, with their latest connectivity observation. A lack of ICMP response is not a definitive offline verdict."
        actions={
          <>
            <Link to="/discovery" className="btn-secondary">
              Run discovery
            </Link>
            <button type="button" className="btn-primary" onClick={refetch} disabled={loading}>
              {loading ? "Refreshing…" : "Refresh"}
            </button>
          </>
        }
      />

      <SectionCard
        title="Inventory filters"
        description="Filters apply to the stored device inventory, not to a new network scan."
      >
        <form
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            setSearch(searchInput.trim());
          }}
        >
          <div className="min-w-0 flex-1">
            <label htmlFor="device-search" className="field-label">
              Search
            </label>
            <input
              id="device-search"
              className="field"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="IP address, hostname, MAC address or vendor"
            />
          </div>
          <div className="sm:w-56">
            <label htmlFor="device-status" className="field-label">
              Latest observation
            </label>
            <select
              id="device-status"
              className="field"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary">
              Apply
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setSearchInput("");
                setSearch("");
                setStatus("");
              }}
              disabled={!hasFilters}
            >
              Clear
            </button>
          </div>
        </form>
      </SectionCard>

      {loading && !data ? <LoadingState label="Loading devices…" /> : null}

      {error && !data ? (
        <ErrorState
          title="Device inventory unavailable"
          error={{ message: error.message, code: error.code }}
          onRetry={refetch}
        />
      ) : null}

      {error && data ? (
        <ErrorState
          title="Could not refresh the inventory"
          error={{ message: error.message, code: error.code }}
          onRetry={refetch}
        />
      ) : null}

      {data ? (
        <SectionCard
          title="Stored devices"
          description={`${formatCount(data.total)} matching device${data.total === 1 ? "" : "s"}${
            data.total > data.items.length ? ` · showing the first ${data.items.length}` : ""
          }`}
        >
          {data.items.length === 0 ? (
            <EmptyState
              title={hasFilters ? "No devices match these filters" : "No devices recorded yet"}
              description={
                hasFilters
                  ? "Clear the filters to view the full inventory, or run a new discovery scan to look for hosts."
                  : "Device records are created by an authorized discovery scan. NetPulse does not seed sample devices or fabricate inventory data."
              }
              action={
                hasFilters ? (
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      setSearchInput("");
                      setSearch("");
                      setStatus("");
                    }}
                  >
                    Clear filters
                  </button>
                ) : (
                  <Link to="/discovery" className="btn-primary">
                    Open discovery
                  </Link>
                )
              }
            />
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>IP address</th>
                    <th>Hostname</th>
                    <th>MAC address</th>
                    <th>Latest observation</th>
                    <th>Latency</th>
                    <th>Packet loss</th>
                    <th>Last seen</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((device) => (
                    <tr key={device.id}>
                      <td>
                        <Link to={`/devices/${device.id}`} className="font-mono text-xs font-medium text-pulse-soft hover:text-white">
                          {device.ip_address}
                        </Link>
                      </td>
                      <td>{displayText(device.hostname)}</td>
                      <td className="font-mono text-xs">{displayText(device.mac_address)}</td>
                      <td>
                        <StatusBadge value={device.latest_observation} />
                        <div className="mt-1 text-[11px] text-slate-500">
                          {formatDateTime(device.latest_observation_at)}
                        </div>
                      </td>
                      <td className="whitespace-nowrap">{formatLatency(device.latest_latency_ms)}</td>
                      <td className="whitespace-nowrap">{formatLoss(device.latest_packet_loss_percent)}</td>
                      <td className="whitespace-nowrap text-xs text-slate-400">
                        {formatDateTime(device.last_seen)}
                      </td>
                      <td className="text-right">
                        <Link to={`/devices/${device.id}`} className="link whitespace-nowrap text-xs">
                          Open details
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
    </div>
  );
}
