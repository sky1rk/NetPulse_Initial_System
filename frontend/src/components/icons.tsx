/** Small inline icon set used by the shell and action buttons. */

export type IconName =
  | "overview"
  | "discovery"
  | "devices"
  | "analytics"
  | "security"
  | "diagnostics"
  | "reports"
  | "topology"
  | "settings"
  | "menu"
  | "close"
  | "refresh"
  | "chevron"
  | "pulse"
  | "warning"
  | "check";

const PATHS: Record<IconName, string> = {
  overview:
    "M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm10 0h6v-9h-6v9Zm0-16v5h6V4h-6Z",
  discovery:
    "M12 3a9 9 0 1 0 9 9M12 3a9 9 0 0 1 8.5 6M12 3v9h9m-4 7.5 4 4m-1.5-5.5a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
  devices:
    "M4 5h16v10H4V5Zm-1 14h18M9 19v-4m6 4v-4M9 9h6M9 12h4",
  analytics: "M4 20V9m5 11V4m5 16v-7m5 7V7M2 20h20",
  security:
    "M12 3 5 6v5c0 4.4 2.9 8.2 7 9.5 4.1-1.3 7-5.1 7-9.5V6l-7-3Zm-2.5 8.5 2 2 3.5-4",
  diagnostics:
    "M9 3h6l1 4h3v5l-3 2v7H8v-7l-3-2V7h3l1-4Zm-1 11h8M12 7v4m-2 2h4",
  reports:
    "M7 3h7l4 4v14H7V3Zm7 0v5h4M10 12h5m-5 4h5m-5-8h2",
  topology:
    "M12 4a3 3 0 1 1 0 6 3 3 0 0 1 0-6ZM5 15a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm14 0a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm-5-5v4m0 0-4 2m4-2 4 2",
  settings:
    "M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Zm8 3.5-2.2-.6a6 6 0 0 0-.6-1.5l1.2-2-1.8-1.8-2 1.2a6 6 0 0 0-1.5-.6L12.5 4h-1l-.6 2.2a6 6 0 0 0-1.5.6l-2-1.2-1.8 1.8 1.2 2a6 6 0 0 0-.6 1.5L4 11v1l2.2.6a6 6 0 0 0 .6 1.5l-1.2 2 1.8 1.8 2-1.2a6 6 0 0 0 1.5.6l.6 2.2h1l.6-2.2a6 6 0 0 0 1.5-.6l2 1.2 1.8-1.8-1.2-2a6 6 0 0 0 .6-1.5L20 12v-1Z",
  menu: "M4 7h16M4 12h16M4 17h16",
  close: "M6 6l12 12M18 6 6 18",
  refresh:
    "M20 11a8 8 0 1 0-2.3 6.7M20 4v7h-7",
  chevron: "m9 6 6 6-6 6",
  pulse: "M3 12h4l2-6 4 12 2-6h6",
  warning:
    "M12 3 2.5 20h19L12 3Zm0 6v5m0 3h.01",
  check: "m5 12 4 4L19 6",
};

export function Icon({
  name,
  className = "h-5 w-5",
  strokeWidth = 1.8,
}: {
  name: IconName;
  className?: string;
  strokeWidth?: number;
}) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
