import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  EmptyState,
  ErrorState,
  MetricCard,
  Notice,
  StatusBadge,
} from "../components/ui";

describe("shared UI components", () => {
  it("labels no-ICMP observations without claiming the device is offline", () => {
    render(<StatusBadge value="no_icmp_response" />);
    expect(screen.getByText("No ICMP response")).toBeInTheDocument();
    expect(screen.queryByText(/offline/i)).not.toBeInTheDocument();
  });

  it("renders N/A metric values when data is unavailable", () => {
    render(<MetricCard label="Average latency" value="N/A" hint="No successful samples" />);
    expect(screen.getByText("Average latency")).toBeInTheDocument();
    expect(screen.getByText("N/A")).toBeInTheDocument();
    expect(screen.queryByText("0 ms")).not.toBeInTheDocument();
  });

  it("shows an error message, code and retry action", () => {
    const onRetry = vi.fn();
    render(
      <ErrorState
        error={{ message: "Cannot reach the backend.", code: "BACKEND_UNAVAILABLE" }}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText("Cannot reach the backend.")).toBeInTheDocument();
    expect(screen.getByText("BACKEND_UNAVAILABLE")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders an actionable empty state", () => {
    render(
      <EmptyState
        title="No devices recorded yet"
        description="Run an authorized discovery scan."
        action={<a href="/discovery">Open discovery</a>}
      />,
    );
    expect(screen.getByText("No devices recorded yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open discovery" })).toBeInTheDocument();
  });

  it("renders warning notices", () => {
    render(
      <Notice tone="warning" title="Partial results">
        Some probes could not be executed.
      </Notice>,
    );
    expect(screen.getByText("Partial results")).toBeInTheDocument();
    expect(screen.getByText("Some probes could not be executed.")).toBeInTheDocument();
  });
});
