import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAsync, usePolling } from "../hooks/useAsync";
import { cx } from "../lib/cx";
import { api } from "../services/api";
import { Icon, type IconName } from "./icons";
import { Dot, StatusBadge } from "./ui";

interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  end?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Overview", icon: "overview", end: true },
  { to: "/discovery", label: "Discovery", icon: "discovery" },
  { to: "/devices", label: "Devices", icon: "devices" },
  { to: "/analytics", label: "Analytics", icon: "analytics" },
  { to: "/security", label: "Security", icon: "security" },
  { to: "/diagnostics", label: "Diagnostics", icon: "diagnostics" },
  { to: "/reports", label: "Reports", icon: "reports" },
  { to: "/topology", label: "Topology", icon: "topology" },
  { to: "/settings", label: "Settings", icon: "settings" },
];

function routeTitle(pathname: string): string {
  if (pathname === "/") return "Overview";
  if (pathname.startsWith("/devices/")) return "Device details";
  const match = NAV_ITEMS.find((item) => item.to !== "/" && pathname.startsWith(item.to));
  return match?.label ?? "Not found";
}

function Sidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <>
      <div
        className={cx(
          "fixed inset-0 z-30 bg-black/60 backdrop-blur-sm transition-opacity lg:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        aria-hidden="true"
        onClick={onClose}
      />
      <aside
        className={cx(
          "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-white/10 bg-ink-950/95 transition-transform duration-200 lg:sticky lg:top-0 lg:z-0 lg:h-screen lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <NavLink to="/" className="group flex items-center gap-3" onClick={onClose}>
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-pulse to-pulse-teal text-ink-950 shadow-lg shadow-pulse/20">
              <Icon name="pulse" className="h-5 w-5" strokeWidth={2.2} />
            </span>
            <span>
              <span className="block text-base font-semibold tracking-tight text-white">NetPulse</span>
              <span className="block text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500">
                Local network observatory
              </span>
            </span>
          </NavLink>
          <button
            type="button"
            className="rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white lg:hidden"
            onClick={onClose}
            aria-label="Close navigation"
          >
            <Icon name="close" className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onClose}
              className={({ isActive }) =>
                cx(
                  "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
                  isActive
                    ? "bg-pulse/15 text-white ring-1 ring-inset ring-pulse/25"
                    : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-100",
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    name={item.icon}
                    className={cx("h-[18px] w-[18px]", isActive ? "text-pulse-soft" : "text-slate-500 group-hover:text-slate-300")}
                  />
                  <span className="flex-1">{item.label}</span>
                  {isActive ? <span className="h-1.5 w-1.5 rounded-full bg-pulse-teal" /> : null}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 p-3">
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
              <Dot tone="teal" />
              Local-first deployment
            </div>
            <p className="mt-1.5 text-[11px] leading-relaxed text-slate-500">
              No accounts, cloud services, or telemetry. Data stays in this machine&apos;s SQLite database.
            </p>
          </div>
          <p className="mt-3 px-1 text-[10px] text-slate-600">NetPulse v1.0.0 · CCS 234 project</p>
        </div>
      </aside>
    </>
  );
}

export default function AppShell() {
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const health = useAsync(() => api.health(), []);
  usePolling(health.refetch, 20000, true);

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  const title = useMemo(() => routeTitle(location.pathname), [location.pathname]);

  const online = Boolean(health.data && !health.error && health.data.status === "ok");
  const degraded = Boolean(health.data && !health.error && health.data.status !== "ok");
  const checking = health.loading && !health.data && !health.error;

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[18rem_minmax(0,1fr)]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-ink-950"
      >
        Skip to content
      </a>
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />

      <div className="flex min-h-screen min-w-0 flex-col">
        <header className="sticky top-0 z-20 border-b border-white/10 bg-ink-950/80 backdrop-blur-md">
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
            <button
              type="button"
              className="rounded-lg border border-white/10 p-2 text-slate-300 hover:bg-white/5 lg:hidden"
              onClick={() => setNavOpen(true)}
              aria-label="Open navigation"
            >
              <Icon name="menu" className="h-5 w-5" />
            </button>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                <span>NetPulse</span>
                <Icon name="chevron" className="h-3 w-3" />
                <span className="truncate text-slate-400">{title}</span>
              </div>
              <h2 className="truncate text-sm font-semibold text-white">{title}</h2>
            </div>
            <div className="hidden items-center gap-2 sm:flex">
              {checking ? (
                <StatusBadge value={null} label="Checking backend…" />
              ) : online ? (
                <span className="chip border-emerald-400/25 bg-emerald-400/10 text-emerald-200">
                  <Dot tone="green" pulse />
                  Backend online
                </span>
              ) : degraded ? (
                <span className="chip border-amber-400/25 bg-amber-400/10 text-amber-200">
                  <Dot tone="amber" />
                  Backend degraded
                </span>
              ) : (
                <span
                  className="chip border-rose-400/25 bg-rose-400/10 text-rose-200"
                  title={health.error?.message || "The backend health check failed."}
                >
                  <Dot tone="rose" />
                  Backend offline
                </span>
              )}
            </div>
            <div className="hidden text-right md:block">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">API</div>
              <div className="max-w-[13rem] truncate font-mono text-[11px] text-slate-400">
                {health.data?.version ? `v${health.data.version}` : "unavailable"}
              </div>
            </div>
          </div>
        </header>

        <main id="main-content" className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>

        <footer className="border-t border-white/[0.06] px-4 py-4 text-center text-[11px] text-slate-600 sm:px-6 lg:px-8">
          Only monitor networks and devices you own or are explicitly authorized to assess.
        </footer>
      </div>
    </div>
  );
}
