import { useState } from "react";
import { Link } from "react-router-dom";

import {
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
import { api } from "../services/api";

export default function DiagnosticsPage() {
  const devicesState = useAsync(() => api.devices({ limit: 500 }), []);
  const [deviceId, setDeviceId] = useState<number | "">("");
  const recommendationsState = useAsync(
    () => api.recommendations(deviceId === "" ? null : deviceId),
    [deviceId],
  );

  const data = recommendationsState.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Diagnostics"
        description="Deterministic, rule-based guidance derived from recorded latency, loss, availability and security observations."
        actions={
          <button
            type="button"
            className="btn-secondary"
            onClick={recommendationsState.refetch}
            disabled={recommendationsState.loading}
          >
            {recommendationsState.loading ? "Re-evaluating…" : "Re-evaluate rules"}
          </button>
        }
      />

      <SectionCard
        title="Diagnostic scope"
        description="Rules use configurable thresholds. A triggered rule describes an observed condition, not a root cause."
        actions={
          <div className="flex items-center gap-2">
            <label htmlFor="diagnostics-device" className="text-xs text-slate-500">
              Device
            </label>
            <select
              id="diagnostics-device"
              className="field w-auto py-1.5 text-xs"
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
          </div>
        }
      >
        <Notice tone="neutral" title="How to read this page">
          Recommendations are generated from stored measurements only. NetPulse does not infer a root cause from a
          single metric, does not fabricate observations, and does not make changes to devices.
        </Notice>
      </SectionCard>

      {recommendationsState.loading && !data ? <LoadingState label="Evaluating diagnostic rules…" /> : null}

      {recommendationsState.error && !data ? (
        <ErrorState
          title="Recommendations unavailable"
          error={{
            message: recommendationsState.error.message,
            code: recommendationsState.error.code,
          }}
          onRetry={recommendationsState.refetch}
        />
      ) : null}

      {data ? (
        <>
          {recommendationsState.error ? (
            <Notice tone="danger" title="Recommendations may be stale">
              {recommendationsState.error.message}
            </Notice>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-400">
            <span>
              {formatCount(data.items.length)} recommendation{data.items.length === 1 ? "" : "s"} triggered
            </span>
            <span className="text-xs text-slate-500">Evaluated {formatDateTime(data.generated_at)}</span>
          </div>

          {data.items.length === 0 ? (
            <EmptyState
              title="No diagnostic rules were triggered"
              description="This means the configured rules did not match the currently stored observations. It does not prove that the network is healthy or that no issue exists."
              action={
                <Link to="/devices" className="btn-secondary">
                  Review device observations
                </Link>
              }
            />
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              {data.items.map((item, index) => (
                <article
                  key={`${item.rule_id}-${item.device_id ?? "network"}-${index}`}
                  className="rounded-xl border border-white/10 bg-ink-900/70 p-4 shadow-card"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge value={item.severity} />
                        <span className="font-mono text-[11px] uppercase tracking-wide text-slate-500">
                          {item.rule_id}
                        </span>
                      </div>
                      <h2 className="mt-2 text-sm font-semibold text-white">{item.title}</h2>
                    </div>
                    {item.device_id !== null ? (
                      <Link to={`/devices/${item.device_id}`} className="link text-xs">
                        {displayText(item.device_ip)}
                      </Link>
                    ) : (
                      <span className="text-xs text-slate-500">Network-wide</span>
                    )}
                  </div>

                  <div className="mt-3 space-y-3 text-sm">
                    <div>
                      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                        Observed condition
                      </h3>
                      <p className="mt-1 leading-relaxed text-slate-300">{item.observed_condition}</p>
                    </div>
                    <div>
                      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                        Recommendation
                      </h3>
                      <p className="mt-1 leading-relaxed text-slate-300">{item.recommendation}</p>
                    </div>
                  </div>

                  {item.evidence ? (
                    <details className="mt-3 rounded-lg border border-white/[0.07] bg-ink-950/40 p-2.5">
                      <summary className="cursor-pointer text-xs font-medium text-slate-400">
                        Evidence recorded with this rule
                      </summary>
                      <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-[11px] leading-relaxed text-slate-500">
                        {JSON.stringify(item.evidence, null, 2)}
                      </pre>
                    </details>
                  ) : null}

                  <p className="mt-3 border-t border-white/[0.06] pt-2 text-[11px] text-slate-500">
                    Evaluated {formatDateTime(item.created_at)}. This is guidance, not an automated fix or a
                    confirmed cause.
                  </p>
                </article>
              ))}
            </div>
          )}

          <SectionCard title="Rule engine note">
            <p className="text-sm leading-relaxed text-slate-400">{data.note}</p>
          </SectionCard>
        </>
      ) : null}
    </div>
  );
}
