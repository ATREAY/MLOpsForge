import type { ReactNode } from "react";

import type { JobStatus, ModelStage } from "@/api/types";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-lg border border-slate-800 bg-slate-900 p-4 ${className}`}>{children}</div>;
}

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  const variants = {
    primary: "bg-cyan-500 text-slate-950 hover:bg-cyan-400",
    secondary: "border border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700",
    danger: "bg-red-600 text-white hover:bg-red-500",
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]}`}
    >
      {children}
    </button>
  );
}

// Chip style — tinted-translucent background + colored text + a thin
// same-hue border — reads as "system status" (Grafana/Linear-ish) rather
// than the solid-pastel badges that work on a light background but go
// muddy on dark.
const JOB_STATUS_STYLES: Record<JobStatus, string> = {
  queued: "border-slate-600/40 bg-slate-500/10 text-slate-300",
  submitted: "border-cyan-500/30 bg-cyan-500/10 text-cyan-300",
  running: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  finished: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  failed: "border-red-500/30 bg-red-500/10 text-red-300",
  cancelled: "border-slate-600/40 bg-slate-500/10 text-slate-400",
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${JOB_STATUS_STYLES[status]}`}
    >
      {status === "running" && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />}
      {status}
    </span>
  );
}

const MODEL_STAGE_STYLES: Record<ModelStage, string> = {
  none: "border-slate-600/40 bg-slate-500/10 text-slate-400",
  staging: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  production: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  archived: "border-slate-700/40 bg-slate-500/5 text-slate-500",
};

export function ModelStageBadge({ stage }: { stage: ModelStage }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${MODEL_STAGE_STYLES[stage]}`}
    >
      {stage === "production" && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />}
      {stage}
    </span>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-semibold tracking-tight text-slate-50">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
    </div>
  );
}
