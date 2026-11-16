/** Shared presentational components: cards, badges, empty/loading/error states. */

import type { ReactNode } from "react";

import { cx } from "../lib/cx";
import { badgeMeta, type BadgeMeta } from "../lib/format";
import { Icon } from "./icons";

const TONE_CLASSES: Record<BadgeMeta["tone"], string> = {
  green: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
  amber: "border-amber-400/25 bg-amber-400/10 text-amber-200",
  rose: "border-rose-400/25 bg-rose-400/10 text-rose-200",
  slate: "border-white/10 bg-white/5 text-slate-300",
  blue: "border-blue-400/25 bg-blue-400/10 text-blue-200",
  teal: "border-teal-400/25 bg-teal-400/10 text-teal-200",
};

const DOT_CLASSES: Record<BadgeMeta["tone"], string> = {
  green: "bg-emerald-400",
  amber: "bg-amber-400",
  rose: "bg-rose-400",
  slate: "bg-slate-400",
  blue: "bg-blue-400",
  teal: "bg-teal-400",
};

export function StatusBadge({
  value,
  label,
}: {
  value?: string | null;
  label?: string;
}) {
  const meta = badgeMeta(value);
  return (
    <span className={cx("chip", TONE_CLASSES[meta.tone])}>
      <span className={cx("h-1.5 w-1.5 rounded-full", DOT_CLASSES[meta.tone])} aria-hidden="true" />
      {label ?? meta.label}
    </span>
  );
}

export function Dot({ tone = "slate", pulse = false }: { tone?: BadgeMeta["tone"]; pulse?: boolean }) {
  return (
    <span className="relative flex h-2.5 w-2.5" aria-hidden="true">
      {pulse ? (
        <span className={cx("absolute inline-flex h-full w-full animate-ping rounded-full opacity-40", DOT_CLASSES[tone])} />
      ) : null}
      <span className={cx("relative inline-flex h-2.5 w-2.5 rounded-full", DOT_CLASSES[tone])} />
    </span>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-[1.7rem]">{title}</h1>
        {description ? <div className="mt-1.5 max-w-3xl text-sm text-slate-400">{description}</div> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function SectionCard({
  title,
  description,
  actions,
  children,
  className,
  contentClassName,
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  return (
    <section
      className={cx(
        "rounded-xl border border-white/10 bg-ink-900/70 shadow-card backdrop-blur-sm",
        className,
      )}
    >
      {title || description || actions ? (
        <div className="flex flex-col gap-3 border-b border-white/[0.07] px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div className="min-w-0">
            {title ? <h2 className="text-sm font-semibold text-white">{title}</h2> : null}
            {description ? <div className="mt-0.5 text-xs text-slate-400">{description}</div> : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </div>
      ) : null}
      <div className={cx("p-4 sm:p-5", contentClassName)}>{children}</div>
    </section>
  );
}

export function MetricCard({
  label,
  value,
  hint,
  tone = "blue",
  footer,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: BadgeMeta["tone"];
  footer?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-ink-900/70 p-4 shadow-card">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</span>
        <Dot tone={tone} />
      </div>
      <div className="mt-2.5 text-2xl font-semibold tracking-tight text-white">{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-400">{hint}</div> : null}
      {footer ? <div className="mt-3 border-t border-white/[0.06] pt-2.5 text-xs">{footer}</div> : null}
    </div>
  );
}

export type NoticeTone = "info" | "warning" | "danger" | "success" | "neutral";

const NOTICE_CLASSES: Record<NoticeTone, string> = {
  info: "border-blue-400/20 bg-blue-400/[0.07] text-blue-100",
  warning: "border-amber-400/25 bg-amber-400/[0.07] text-amber-100",
  danger: "border-rose-400/25 bg-rose-400/[0.07] text-rose-100",
  success: "border-emerald-400/25 bg-emerald-400/[0.07] text-emerald-100",
  neutral: "border-white/10 bg-white/[0.03] text-slate-300",
};

export function Notice({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: NoticeTone;
  title?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const iconName = tone === "success" ? "check" : tone === "info" || tone === "neutral" ? "pulse" : "warning";
  return (
    <div className={cx("rounded-lg border px-3.5 py-3 text-sm", NOTICE_CLASSES[tone], className)}>
      <div className="flex gap-2.5">
        <Icon name={iconName} className="mt-0.5 h-4 w-4 shrink-0" />
        <div className="min-w-0">
          {title ? <div className="font-semibold">{title}</div> : null}
          <div className={cx(title ? "mt-0.5 opacity-90" : "")}>{children}</div>
        </div>
      </div>
    </div>
  );
}

export function LoadingState({ label = "Loading data…" }: { label?: string }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 rounded-xl border border-white/10 bg-ink-900/50 px-6 py-12 text-sm text-slate-400"
      role="status"
      aria-live="polite"
    >
      <span className="h-6 w-6 animate-spin rounded-full border-2 border-white/15 border-t-pulse" aria-hidden="true" />
      {label}
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
  title = "Something went wrong",
}: {
  error: { message: string; code?: string } | null;
  onRetry?: () => void;
  title?: string;
}) {
  return (
    <div className="rounded-xl border border-rose-400/25 bg-rose-400/[0.06] px-5 py-6" role="alert">
      <div className="flex items-start gap-3">
        <Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0 text-rose-300" />
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-rose-100">{title}</h3>
          <p className="mt-1 text-sm text-rose-100/80">{error?.message || "The request could not be completed."}</p>
          {error?.code ? (
            <p className="mt-1.5 font-mono text-[11px] uppercase tracking-wide text-rose-200/60">{error.code}</p>
          ) : null}
          {onRetry ? (
            <button type="button" className="btn-secondary mt-3" onClick={onRetry}>
              <Icon name="refresh" className="h-4 w-4" />
              Try again
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-dashed border-white/15 bg-ink-900/40 px-6 py-10 text-center">
      <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-slate-400">
        <Icon name="pulse" className="h-5 w-5" />
      </div>
      <h3 className="mt-3 text-sm font-semibold text-white">{title}</h3>
      <div className="mx-auto mt-1 max-w-xl text-sm text-slate-400">{description}</div>
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}

export function DataList({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return (
    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{item.label}</dt>
          <dd className="mt-0.5 break-words text-sm text-slate-200">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function InlineSpinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/20 border-t-white" aria-hidden="true" />
      {label}
    </span>
  );
}
