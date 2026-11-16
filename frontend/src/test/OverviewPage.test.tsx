import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import OverviewPage from "../pages/OverviewPage";
import { ApiError, api } from "../services/api";
import type { DashboardSummary } from "../types";

vi.mock("../services/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      dashboard: vi.fn(),
    },
  };
});

const emptySummary: DashboardSummary = {
  devices_total: 0,
  responding_hosts: 0,
  no_icmp_hosts: 0,
  not_tested_hosts: 0,
  avg_latency_ms: null,
  packet_loss_percent: null,
  health_score: null,
  health_label: "Insufficient data",
  last_scan_at: null,
  latest_observation_at: null,
  active_monitoring_sessions: 0,
  open_security_findings: 0,
  reports_count: 0,
  recent_activity: [],
  warnings: [],
};

function renderPage() {
  return render(
    <MemoryRouter>
      <OverviewPage />
    </MemoryRouter>,
  );
}

describe("Overview page", () => {
  const dashboard = vi.mocked(api.dashboard);

  beforeEach(() => {
    dashboard.mockReset();
  });

  it("renders accurate empty states and null metrics", async () => {
    dashboard.mockResolvedValue(emptySummary);
    renderPage();

    expect(await screen.findByText("No activity recorded yet")).toBeInTheDocument();
    expect(screen.getByText("No devices are stored yet. Discovery results depend on the local subnet, device firewalls, client isolation and operating-system permissions.")).toBeInTheDocument();
    expect(screen.getByText("Health is unavailable because the required connectivity and availability inputs are incomplete. NetPulse does not substitute zero for missing measurements. Record successful probes and monitoring observations to populate the score.")).toBeInTheDocument();
    expect(screen.getAllByText("N/A").length).toBeGreaterThanOrEqual(2);
  });

  it("shows a visible backend error instead of crashing", async () => {
    dashboard.mockRejectedValue(
      new ApiError("BACKEND_UNAVAILABLE", "Cannot reach the NetPulse backend."),
    );
    renderPage();

    expect(await screen.findByText("Dashboard unavailable")).toBeInTheDocument();
    expect(screen.getByText("Cannot reach the NetPulse backend.")).toBeInTheDocument();
    expect(screen.getByText("BACKEND_UNAVAILABLE")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });
});
