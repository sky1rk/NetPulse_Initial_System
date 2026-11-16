import { useState } from "react";
import { Link } from "react-router-dom";

import {
  EmptyState,
  ErrorState,
  InlineSpinner,
  LoadingState,
  Notice,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import {
  datetimeLocalToIso,
  displayText,
  formatCount,
  formatDateTime,
  formatRange,
  toDateTimeLocalValue,
} from "../lib/format";
import { api, ApiError, reportDownloadUrl, toApiError } from "../services/api";

function defaultRange(): { from: string; to: string } {
  const to = new Date();
  const from = new Date(to.getTime() - 24 * 60 * 60 * 1000);
  return { from: toDateTimeLocalValue(from), to: toDateTimeLocalValue(to) };
}

export default function ReportsPage() {
  const reportsState = useAsync(() => api.reports(), []);
  const devicesState = useAsync(() => api.devices({ limit: 500 }), []);

  const [format, setFormat] = useState<"pdf" | "csv">("pdf");
  const [range, setRange] = useState(defaultRange);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<ApiError | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const toggleDevice = (deviceId: number) => {
    setSelectedIds((current) =>
      current.includes(deviceId) ? current.filter((id) => id !== deviceId) : [...current, deviceId],
    );
  };

  const generate = async () => {
    setGenerateError(null);
    setFeedback(null);
    const fromIso = range.from ? datetimeLocalToIso(range.from) : null;
    const toIso = range.to ? datetimeLocalToIso(range.to) : null;

    if ((range.from && !fromIso) || (range.to && !toIso)) {
      setGenerateError(new ApiError("INVALID_TIME_RANGE", "Enter valid start and end date/time values."));
      return;
    }
    if (fromIso && toIso && fromIso >= toIso) {
      setGenerateError(new ApiError("INVALID_TIME_RANGE", "The start of the range must be earlier than the end."));
      return;
    }

    setGenerating(true);
    try {
      const report = await api.generateReport({
        format,
        from: fromIso,
        to: toIso,
        device_ids: selectedIds,
      });
      setFeedback(`Report #${report.id} generated (${report.report_type.toUpperCase()}).`);
      reportsState.refetch();
    } catch (reason) {
      setGenerateError(toApiError(reason, "The report could not be generated."));
      reportsState.refetch();
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description="Generate local PDF or CSV reports from stored devices, connectivity results, security observations and diagnostic rules."
        actions={
          <button type="button" className="btn-secondary" onClick={reportsState.refetch} disabled={reportsState.loading}>
            {reportsState.loading ? "Refreshing…" : "Refresh history"}
          </button>
        }
      />

      <Notice tone="neutral" title="Local report storage">
        Report files are written to the backend reports directory and downloaded by report ID. The client cannot
        supply arbitrary file paths. Reports contain only recorded data; missing measurements are shown as N/A.
      </Notice>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <SectionCard title="Generate a report" description="Choose a range, optional device scope and file format.">
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="report-from" className="field-label">
                  From
                </label>
                <input
                  id="report-from"
                  type="datetime-local"
                  className="field"
                  value={range.from}
                  onChange={(event) => setRange((current) => ({ ...current, from: event.target.value }))}
                  disabled={generating}
                />
              </div>
              <div>
                <label htmlFor="report-to" className="field-label">
                  To
                </label>
                <input
                  id="report-to"
                  type="datetime-local"
                  className="field"
                  value={range.to}
                  onChange={(event) => setRange((current) => ({ ...current, to: event.target.value }))}
                  disabled={generating}
                />
              </div>
            </div>

            <div>
              <span className="field-label">Format</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className={format === "pdf" ? "btn-primary" : "btn-secondary"}
                  onClick={() => setFormat("pdf")}
                  disabled={generating}
                >
                  PDF report
                </button>
                <button
                  type="button"
                  className={format === "csv" ? "btn-primary" : "btn-secondary"}
                  onClick={() => setFormat("csv")}
                  disabled={generating}
                >
                  CSV export
                </button>
              </div>
            </div>

            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="field-label mb-0">Device scope</span>
                <div className="flex gap-2 text-xs">
                  <button
                    type="button"
                    className="text-slate-400 hover:text-white"
                    onClick={() => setSelectedIds((devicesState.data?.items ?? []).map((device) => device.id))}
                    disabled={generating || (devicesState.data?.items.length ?? 0) === 0}
                  >
                    Select all
                  </button>
                  <span className="text-slate-700">·</span>
                  <button
                    type="button"
                    className="text-slate-400 hover:text-white"
                    onClick={() => setSelectedIds([])}
                    disabled={generating || selectedIds.length === 0}
                  >
                    Clear
                  </button>
                </div>
              </div>
              <p className="mb-2 mt-1 text-[11px] text-slate-500">
                No selection means all stored devices. {formatCount(selectedIds.length)} selected.
              </p>
              <div className="max-h-52 space-y-1 overflow-y-auto rounded-lg border border-white/10 bg-ink-950/40 p-2">
                {devicesState.loading ? (
                  <div className="p-2 text-xs text-slate-500">Loading devices…</div>
                ) : devicesState.error ? (
                  <div className="p-2 text-xs text-rose-300">{devicesState.error.message}</div>
                ) : (devicesState.data?.items.length ?? 0) === 0 ? (
                  <div className="p-2 text-xs text-slate-500">
                    No devices recorded. The report will still describe the empty inventory and network context.
                  </div>
                ) : (
                  devicesState.data?.items.map((device) => (
                    <label
                      key={device.id}
                      className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm text-slate-300 hover:bg-white/[0.04]"
                    >
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-white/20 bg-ink-900 accent-blue-500"
                        checked={selectedIds.includes(device.id)}
                        onChange={() => toggleDevice(device.id)}
                        disabled={generating}
                      />
                      <span className="font-mono text-xs text-slate-200">{device.ip_address}</span>
                      <span className="truncate text-xs text-slate-500">{displayText(device.hostname)}</span>
                    </label>
                  ))
                )}
              </div>
            </div>

            {generateError ? (
              <Notice tone="danger" title="Report could not be generated">
                {generateError.message}
              </Notice>
            ) : null}
            {feedback ? <Notice tone="success">{feedback}</Notice> : null}

            <div className="flex flex-wrap items-center gap-3">
              <button type="button" className="btn-primary" onClick={generate} disabled={generating}>
                {generating ? <InlineSpinner label="Generating report…" /> : `Generate ${format.toUpperCase()}`}
              </button>
              <span className="text-xs text-slate-500">
                Generation runs synchronously and may take a moment with large histories.
              </span>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          title="Report contents"
          description="The same recorded dataset feeds both formats."
        >
          <ol className="list-inside list-decimal space-y-1.5 text-sm text-slate-400">
            <li>Report title, ID and generation time</li>
            <li>Selected time range and device scope</li>
            <li>Local network configuration</li>
            <li>Discovered device inventory</li>
            <li>Connectivity tests and performance metrics</li>
            <li>Security assessment observations</li>
            <li>Rule-based diagnostic recommendations</li>
            <li>Limitations and methodology</li>
          </ol>
          <div className="mt-4 space-y-2 rounded-lg border border-white/[0.07] bg-white/[0.02] p-3 text-xs leading-relaxed text-slate-500">
            <p>
              PDF files use ReportLab tables with a readable report layout. CSV files include device, ping test,
              security finding and recommendation rows with a UTF-8 BOM.
            </p>
            <p>
              Reports never claim physical topology certainty, never label an open port as a vulnerability, and
              never replace unavailable values with zero.
            </p>
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title="Report history"
        description={`${formatCount(reportsState.data?.total ?? null)} stored report${(reportsState.data?.total ?? 0) === 1 ? "" : "s"}`}
      >
        {reportsState.loading && !reportsState.data ? (
          <LoadingState label="Loading report history…" />
        ) : reportsState.error && !reportsState.data ? (
          <ErrorState
            title="Report history unavailable"
            error={{ message: reportsState.error.message, code: reportsState.error.code }}
            onRetry={reportsState.refetch}
          />
        ) : (reportsState.data?.items.length ?? 0) === 0 ? (
          <EmptyState
            title="No reports generated yet"
            description="Generate a PDF or CSV above. The history will list the actual file status and a download link for completed reports."
          />
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Report</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th>Generated</th>
                  <th>Selected range</th>
                  <th>File</th>
                  <th className="text-right">Download</th>
                </tr>
              </thead>
              <tbody>
                {reportsState.data?.items.map((report) => (
                  <tr key={report.id}>
                    <td className="font-mono text-xs text-slate-200">#{report.id}</td>
                    <td className="uppercase text-xs">{report.report_type}</td>
                    <td>
                      <StatusBadge value={report.status} />
                      {report.error_message ? (
                        <div className="mt-1 max-w-xs text-[11px] text-rose-300">{report.error_message}</div>
                      ) : null}
                    </td>
                    <td className="whitespace-nowrap text-xs text-slate-400">
                      {formatDateTime(report.generated_at)}
                    </td>
                    <td className="text-xs text-slate-400">{formatRange(report.range_from, report.range_to)}</td>
                    <td className="max-w-[14rem] truncate font-mono text-[11px] text-slate-500">
                      {displayText(report.file_name)}
                    </td>
                    <td className="text-right">
                      {report.download_url ? (
                        <a className="link whitespace-nowrap text-xs" href={reportDownloadUrl(report.download_url)}>
                          Download
                        </a>
                      ) : (
                        <span className="text-xs text-slate-600">Not available</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {reportsState.error && reportsState.data ? (
          <div className="mt-3">
            <Notice tone="danger" title="History may be stale">
              {reportsState.error.message}
            </Notice>
          </div>
        ) : null}
        <p className="mt-3 text-[11px] text-slate-500">
          Need device-level context first? <Link to="/devices" className="link">Open the device inventory</Link>.
        </p>
      </SectionCard>
    </div>
  );
}
