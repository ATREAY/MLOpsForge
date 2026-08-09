import { useState } from "react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { logout, useCurrentUser } from "@/api/auth";
import { getApiBaseUrl, setApiBaseUrl } from "@/api/client";
import { useJobsLiveUpdates } from "@/api/ws";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/datasets", label: "Datasets" },
  { to: "/experiments", label: "Experiments" },
  { to: "/training", label: "Training" },
  { to: "/models", label: "Models" },
  { to: "/compare", label: "Compare" },
  { to: "/inference", label: "Inference" },
];

function Wordmark() {
  return (
    <span className="flex items-center gap-2">
      <span className="h-2 w-2 rounded-sm bg-cyan-400" />
      <span className="text-lg font-bold tracking-tight text-slate-50">MLOpsForge</span>
    </span>
  );
}

// The backend only exists on an HPC login node behind a tunnel started
// per-demo — its public URL changes each time. Rather than requiring a
// rebuild/redeploy whenever that happens, the API endpoint is editable live
// from here (see api/client.ts's resolveApiBaseUrl for the full precedence:
// ?api= query param > this > build-time env var > relative path).
function ApiEndpointControl() {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(getApiBaseUrl());

  if (!editing) {
    return (
      <button
        onClick={() => {
          setDraft(getApiBaseUrl());
          setEditing(true);
        }}
        className="mt-1 block w-full truncate rounded-md px-3 py-1 text-left font-mono text-[11px] text-slate-500 hover:bg-slate-800 hover:text-slate-300"
        title={getApiBaseUrl()}
      >
        API: {getApiBaseUrl()}
      </button>
    );
  }

  return (
    <div className="mt-1 px-3">
      <input
        autoFocus
        className="w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1 font-mono text-xs text-slate-200 placeholder:text-slate-500"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && draft.trim()) setApiBaseUrl(draft.trim());
          if (e.key === "Escape") setEditing(false);
        }}
        placeholder="https://xxxx.devtunnels.ms/api/v1"
      />
      <div className="mt-1 flex gap-2">
        <button
          onClick={() => draft.trim() && setApiBaseUrl(draft.trim())}
          className="rounded-md bg-cyan-500 px-2 py-0.5 text-[11px] font-medium text-slate-950 hover:bg-cyan-400"
        >
          Save & reload
        </button>
        <button
          onClick={() => setEditing(false)}
          className="rounded-md px-2 py-0.5 text-[11px] font-medium text-slate-400 hover:bg-slate-800"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 5h14M3 10h14M3 15h14" strokeLinecap="round" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 3l10 10M13 3L3 13" strokeLinecap="round" />
    </svg>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const { data: user } = useCurrentUser();
  const [mobileOpen, setMobileOpen] = useState(false);
  useJobsLiveUpdates();

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Mobile-only top bar — the sidebar below is an off-canvas drawer under md, so
          there's otherwise no way to see the nav or reach it on a phone-width screen. */}
      <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900 px-4 py-3 md:hidden">
        <Wordmark />
        <button
          onClick={() => setMobileOpen(true)}
          className="rounded-md p-2 text-slate-400 hover:bg-slate-800 hover:text-slate-100"
          aria-label="Open menu"
        >
          <MenuIcon />
        </button>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-30 bg-black/60 md:hidden" onClick={() => setMobileOpen(false)} />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-900 transition-transform duration-200 md:static md:w-56 md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-4">
          <Wordmark />
          <button
            onClick={() => setMobileOpen(false)}
            className="rounded-md p-1 text-slate-500 hover:bg-slate-800 hover:text-slate-200 md:hidden"
            aria-label="Close menu"
          >
            <CloseIcon />
          </button>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "border-cyan-500/20 bg-cyan-500/10 text-cyan-300"
                    : "border-transparent text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 p-3">
          <p className="truncate px-3 text-xs text-slate-500">{user?.email ?? "…"}</p>
          <button
            onClick={logout}
            className="mt-1 w-full rounded-md px-3 py-2 text-left text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-100"
          >
            Sign out
          </button>
          <ApiEndpointControl />
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-8">{children}</main>
    </div>
  );
}
