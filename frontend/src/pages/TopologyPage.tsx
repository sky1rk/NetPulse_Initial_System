import { useMemo, useState } from "react";
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
import { displayText, formatCount } from "../lib/format";
import { api } from "../services/api";
import type { TopologyNode } from "../types";

const WIDTH = 900;

interface Position {
  x: number;
  y: number;
}

function truncate(value: string, length = 22): string {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}

function nodeColor(node: TopologyNode): string {
  if (node.node_type === "local_host") return "#3b82f6";
  if (node.node_type === "gateway") return "#2dd4bf";
  if (node.observation === "responding") return "#34d399";
  if (node.observation === "no_icmp_response") return "#f59e0b";
  if (node.observation === "error") return "#fb7185";
  return "#64748b";
}

export default function TopologyPage() {
  const topology = useAsync(() => api.topology(), []);
  const [selectedId, setSelectedId] = useState<string>("");

  const layout = useMemo(() => {
    const nodes = topology.data?.nodes ?? [];
    const devices = nodes.filter((node) => node.node_type === "device");
    const gateway = nodes.find((node) => node.node_type === "gateway");
    const local = nodes.find((node) => node.node_type === "local_host");

    const positions = new Map<string, Position>();
    if (local) positions.set(local.id, { x: WIDTH / 2, y: 78 });
    if (gateway) positions.set(gateway.id, { x: WIDTH / 2, y: 188 });

    const columns =
      devices.length === 0 ? 1 : Math.min(6, Math.max(1, Math.ceil(Math.sqrt(devices.length))));
    const spacing = 148;
    const startX = WIDTH / 2 - ((columns - 1) * spacing) / 2;
    devices.forEach((node, index) => {
      const column = index % columns;
      const row = Math.floor(index / columns);
      positions.set(node.id, {
        x: startX + column * spacing,
        y: 312 + row * 98,
      });
    });

    const rows = devices.length === 0 ? 0 : Math.ceil(devices.length / columns);
    const height = Math.max(440, 312 + Math.max(0, rows - 1) * 98 + 100);
    return { positions, height };
  }, [topology.data]);

  const selectedNode =
    topology.data?.nodes.find((node) => node.id === selectedId) ??
    topology.data?.local_host ??
    topology.data?.nodes[0] ??
    null;

  const connectedEdges = useMemo(
    () =>
      (topology.data?.edges ?? []).filter(
        (edge) => edge.source === selectedNode?.id || edge.target === selectedNode?.id,
      ),
    [selectedNode?.id, topology.data],
  );

  const deviceIdFromNode = selectedNode?.node_type === "device"
    ? Number(selectedNode.id.replace("device-", ""))
    : null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Logical topology"
        description="A conceptual view of the monitoring host, default gateway and discovered devices. Relationships are grouped, not physically verified."
        actions={
          <button type="button" className="btn-secondary" onClick={topology.refetch} disabled={topology.loading}>
            {topology.loading ? "Refreshing…" : "Refresh topology"}
          </button>
        }
      />

      <Notice tone="info" title="Logical view, not a physical map">
        Logical view based on available network information; physical links are not verified. Dashed edges are
        inferred groupings or observations on the local subnet, not switch-level connections.
      </Notice>

      {topology.loading && !topology.data ? <LoadingState label="Building logical topology…" /> : null}

      {topology.error && !topology.data ? (
        <ErrorState
          title="Topology unavailable"
          error={{ message: topology.error.message, code: topology.error.code }}
          onRetry={topology.refetch}
        />
      ) : null}

      {topology.data ? (
        <>
          {topology.error ? (
            <Notice tone="danger" title="Topology may be stale">
              {topology.error.message}
            </Notice>
          ) : null}

          {topology.data.warnings.length > 0 ? (
            <Notice tone="warning" title="Topology warnings">
              <ul className="list-inside list-disc space-y-1">
                {topology.data.warnings.map((warning, index) => (
                  <li key={`${warning}-${index}`}>{warning}</li>
                ))}
              </ul>
            </Notice>
          ) : null}

          {topology.data.nodes.length === 0 ? (
            <EmptyState
              title="No topology data"
              description="No local host or device information is available. Run a discovery scan and refresh."
              action={
                <Link to="/discovery" className="btn-primary">
                  Open discovery
                </Link>
              }
            />
          ) : (
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
              <SectionCard
                title="Network map"
                description={`${formatCount(topology.data.nodes.length)} nodes · ${formatCount(topology.data.edges.length)} logical edges. Select a node for details.`}
                contentClassName="p-0 sm:p-0"
              >
                <div className="overflow-x-auto">
                  <svg
                    viewBox={`0 0 ${WIDTH} ${layout.height}`}
                    className="h-auto w-full min-w-[680px]"
                    role="img"
                    aria-label="Logical network topology"
                  >
                    <defs>
                      <marker id="topology-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                        <path d="M0,0 L8,4 L0,8 z" fill="rgba(148,163,184,0.5)" />
                      </marker>
                    </defs>

                    {topology.data.edges.map((edge, index) => {
                      const source = layout.positions.get(edge.source);
                      const target = layout.positions.get(edge.target);
                      if (!source || !target) return null;
                      return (
                        <line
                          key={`${edge.source}-${edge.target}-${index}`}
                          x1={source.x}
                          y1={source.y + 26}
                          x2={target.x}
                          y2={target.y - 26}
                          stroke={edge.inferred ? "rgba(148,163,184,0.35)" : "rgba(45,212,191,0.55)"}
                          strokeWidth={edge.inferred ? 1.25 : 1.75}
                          strokeDasharray={edge.inferred ? "5 5" : undefined}
                          markerEnd="url(#topology-arrow)"
                        />
                      );
                    })}

                    {topology.data.nodes.map((node) => {
                      const position = layout.positions.get(node.id);
                      if (!position) return null;
                      const isSelected = selectedNode?.id === node.id;
                      const color = nodeColor(node);
                      return (
                        <g
                          key={node.id}
                          transform={`translate(${position.x}, ${position.y})`}
                          className="cursor-pointer outline-none"
                          role="button"
                          tabIndex={0}
                          aria-label={`${node.label}, ${node.node_type}`}
                          onClick={() => setSelectedId(node.id)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              setSelectedId(node.id);
                            }
                          }}
                        >
                          <title>{`${node.label}${node.ip_address ? ` · ${node.ip_address}` : ""}`}</title>
                          {isSelected ? (
                            <circle r={31} fill="none" stroke="rgba(255,255,255,0.55)" strokeWidth={1.5} />
                          ) : null}
                          <circle r={23} fill={color} fillOpacity={0.2} stroke={color} strokeWidth={2} />
                          <circle r={6} fill={color} />
                          <text
                            y={40}
                            textAnchor="middle"
                            fill="#e2e8f0"
                            fontSize={11}
                            fontWeight={600}
                            fontFamily="inherit"
                          >
                            {truncate(node.label)}
                          </text>
                          {node.ip_address && node.ip_address !== node.label ? (
                            <text
                              y={54}
                              textAnchor="middle"
                              fill="#64748b"
                              fontSize={10}
                              fontFamily="ui-monospace, monospace"
                            >
                              {node.ip_address}
                            </text>
                          ) : null}
                        </g>
                      );
                    })}
                  </svg>
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-white/[0.07] px-4 py-3 text-[11px] text-slate-500">
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-pulse" /> Local host
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-pulse-teal" /> Default gateway
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-pulse-green" /> Responding device
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-pulse-amber" /> No ICMP response
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-slate-500" /> Not tested
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-px w-5 border-t border-dashed border-slate-400" /> Inferred grouping
                  </span>
                </div>
              </SectionCard>

              <SectionCard title="Selected node" description="Details come from detected network information and stored device records.">
                {selectedNode ? (
                  <div className="space-y-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-semibold text-white">{selectedNode.label}</h3>
                        <StatusBadge value={selectedNode.node_type} />
                      </div>
                      {selectedNode.inferred ? (
                        <p className="mt-1 text-xs text-amber-200/80">
                          Inferred grouping, not a verified physical connection.
                        </p>
                      ) : null}
                    </div>

                    <DataList
                      items={[
                        { label: "Node ID", value: <span className="font-mono text-xs">{selectedNode.id}</span> },
                        { label: "Type", value: displayText(selectedNode.node_type.replaceAll("_", " ")) },
                        { label: "IP address", value: <span className="font-mono">{displayText(selectedNode.ip_address)}</span> },
                        { label: "MAC address", value: <span className="font-mono">{displayText(selectedNode.mac_address)}</span> },
                        {
                          label: "Latest observation",
                          value: selectedNode.observation ? (
                            <StatusBadge value={selectedNode.observation} />
                          ) : (
                            "N/A"
                          ),
                        },
                        { label: "Conceptual node", value: selectedNode.inferred ? "Yes" : "No" },
                      ]}
                    />

                    {deviceIdFromNode && Number.isInteger(deviceIdFromNode) ? (
                      <Link to={`/devices/${deviceIdFromNode}`} className="btn-secondary w-full">
                        Open device details
                      </Link>
                    ) : null}

                    <div className="border-t border-white/[0.07] pt-3">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                        Connected logical edges
                      </h4>
                      {connectedEdges.length === 0 ? (
                        <p className="mt-1.5 text-xs text-slate-500">No edges reference this node.</p>
                      ) : (
                        <ul className="mt-2 space-y-1.5">
                          {connectedEdges.map((edge, index) => {
                            const otherId = edge.source === selectedNode.id ? edge.target : edge.source;
                            const other = topology.data?.nodes.find((node) => node.id === otherId);
                            return (
                              <li key={`${edge.source}-${edge.target}-${index}`} className="text-xs text-slate-400">
                                <span className="text-slate-500">{edge.source === selectedNode.id ? "→" : "←"}</span>{" "}
                                {other?.label ?? otherId}
                                {edge.label ? <span className="text-slate-600"> · {edge.label}</span> : null}
                                {edge.inferred ? <span className="text-amber-200/60"> · inferred</span> : null}
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">Select a node in the map.</p>
                )}
              </SectionCard>
            </div>
          )}

          <SectionCard title="About this view" description="How NetPulse constructs the logical topology.">
            <div className="space-y-2 text-sm leading-relaxed text-slate-400">
              <p>{topology.data.note}</p>
              <p>
                The monitoring host and default gateway come from local network detection. Device nodes come from
                stored discovery results. Edges only indicate a known or explicitly inferred relationship, not the
                physical cabling or switch topology.
              </p>
              <p className="text-xs text-slate-500">
                Missing gateways and missing device fields are shown as unavailable. NetPulse does not invent links
                or MAC addresses to make the diagram look complete.
              </p>
            </div>
          </SectionCard>
        </>
      ) : null}
    </div>
  );
}
