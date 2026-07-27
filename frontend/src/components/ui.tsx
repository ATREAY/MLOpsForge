import type { ReactNode } from "react";

import type { JobStatus, ModelStage } from "@/api/types";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-lg border border-slate-200 bg-white p-4 shadow-sm ${className}`}>{children}</div>;
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
    primary: "bg-slate-900 text-white hover:bg-slate-700",
    secondary: "bg-slate-100 text-slate-900 hover:bg-slate-200",
    danger: "bg-red-600 text-white hover:bg-red-700",
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

const JOB_STATUS_STYLES: Record<JobStatus, string> = {
  queued: "bg-slate-100 text-slate-700",
  submitted: "bg-blue-100 text-blue-700",
  running: "bg-amber-100 text-amber-800",
  finished: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  cancelled: "bg-slate-100 text-slate-500",
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${JOB_STATUS_STYLES[status]}`}>
      {status}
    </span>
  );
}

const MODEL_STAGE_STYLES: Record<ModelStage, string> = {
  none: "bg-slate-100 text-slate-600",
  staging: "bg-amber-100 text-amber-800",
  production: "bg-green-100 text-green-700",
  archived: "bg-slate-100 text-slate-400",
};

export function ModelStageBadge({ stage }: { stage: ModelStage }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${MODEL_STAGE_STYLES[stage]}`}>
      {stage}
    </span>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
    </div>
  );
}
