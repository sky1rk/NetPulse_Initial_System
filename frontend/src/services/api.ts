/** Typed API client for the local NetPulse backend. */

import type {
  AnalyticsSummary,
  DashboardSummary,
  DeviceDetail,
  DeviceList,
  HealthResponse,
  HistoryResponse,
  MonitoringSession,
  NetworkInfo,
  PingTestResponse,
  RecommendationsResponse,
  ReportList,
  ReportRecord,
  ScanResponse,
  SecurityFindingsList,
  SecurityProfile,
  SecurityScanResponse,
  TopologyResponse,
} from "../types";

export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

export const WS_BASE = API_BASE.replace(/^http/i, "ws");

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;

  constructor(code: string, message: string, status = 0, details: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

function buildQuery(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

/** Convert any thrown value into a displayable ApiError. */
export function toApiError(reason: unknown, fallback = "An unexpected client error occurred."): ApiError {
  if (reason instanceof ApiError) return reason;
  return new ApiError("UNEXPECTED_ERROR", fallback);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
    });
  } catch {
    throw new ApiError(
      "BACKEND_UNAVAILABLE",
      `Cannot reach the NetPulse backend at ${API_BASE}. Confirm that the FastAPI server is running.`,
    );
  }

  if (!response.ok) {
    let payload: { detail?: { code?: string; message?: string; details?: unknown } } | null = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    const detail = payload?.detail;
    throw new ApiError(
      detail?.code || `HTTP_${response.status}`,
      detail?.message || `The request failed with status ${response.status}.`,
      response.status,
      detail?.details ?? null,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function reportDownloadUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),

  dashboard: () => request<DashboardSummary>("/api/dashboard/summary"),

  networkInfo: () => request<NetworkInfo>("/api/network/info"),

  scanNetwork: (networkCidr: string | null, confirmAuthorized: boolean) =>
    request<ScanResponse>("/api/network/scan", {
      method: "POST",
      body: JSON.stringify({ network_cidr: networkCidr, confirm_authorized: confirmAuthorized }),
    }),

  topology: () => request<TopologyResponse>("/api/network/topology"),

  devices: (params: {
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  } = {}) => request<DeviceList>(`/api/devices${buildQuery(params)}`),

  device: (deviceId: number) => request<DeviceDetail>(`/api/devices/${deviceId}`),

  ping: (deviceId: number, count: number, timeoutMs: number) =>
    request<PingTestResponse>(`/api/devices/${deviceId}/ping`, {
      method: "POST",
      body: JSON.stringify({ count, timeout_ms: timeoutMs }),
    }),

  startMonitoring: (deviceIds: number[], intervalSeconds: number) =>
    request<MonitoringSession>("/api/monitoring/start", {
      method: "POST",
      body: JSON.stringify({ device_ids: deviceIds, interval_seconds: intervalSeconds }),
    }),

  stopMonitoring: (sessionId: number) =>
    request<{ session_id: number; status: string }>(`/api/monitoring/${sessionId}/stop`, {
      method: "POST",
    }),

  monitoringSession: (sessionId: number) =>
    request<MonitoringSession>(`/api/monitoring/${sessionId}`),

  monitoringSessions: (limit = 20) =>
    request<MonitoringSession[]>(`/api/monitoring${buildQuery({ limit })}`),

  analyticsSummary: (params: { device_id?: number | null; from?: string; to?: string } = {}) =>
    request<AnalyticsSummary>(`/api/analytics/summary${buildQuery(params)}`),

  analyticsHistory: (
    params: { device_id?: number | null; from?: string; to?: string; limit?: number } = {},
  ) => request<HistoryResponse>(`/api/analytics/history${buildQuery(params)}`),

  securityProfiles: () => request<SecurityProfile[]>("/api/security/profiles"),

  securityScan: (
    deviceId: number,
    ports: number[] | null,
    confirmAuthorized: boolean,
    profileName?: string | null,
  ) =>
    request<SecurityScanResponse>("/api/security/scan", {
      method: "POST",
      body: JSON.stringify({
        device_id: deviceId,
        ports,
        profile_name: profileName ?? null,
        confirm_authorized: confirmAuthorized,
      }),
    }),

  securityFindings: (params: { device_id?: number; state?: string; limit?: number } = {}) =>
    request<SecurityFindingsList>(`/api/security/findings${buildQuery(params)}`),

  recommendations: (deviceId?: number | null) =>
    request<RecommendationsResponse>(
      `/api/diagnostics/recommendations${buildQuery({ device_id: deviceId })}`,
    ),

  reports: () => request<ReportList>("/api/reports"),

  generateReport: (payload: {
    format: "pdf" | "csv";
    from: string | null;
    to: string | null;
    device_ids: number[];
  }) =>
    request<ReportRecord>("/api/reports/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
