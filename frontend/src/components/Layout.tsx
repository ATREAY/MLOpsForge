import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { logout, useCurrentUser } from "@/api/auth";
import { useJobsLiveUpdates } from "@/api/ws";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/datasets", label: "Datasets" },
  { to: "/experiments", label: "Experiments" },
  { to: "/training", label: "Training" },
  { to: "/models", label: "Models" },
];

export function Layout({ children }: { children: ReactNode }) {
  const { data: user } = useCurrentUser();
  useJobsLiveUpdates();

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-4">
          <span className="text-lg font-bold tracking-tight text-slate-900">MLOpsForge</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 p-3">
          <p className="truncate px-3 text-xs text-slate-500">{user?.email ?? "…"}</p>
          <button
            onClick={logout}
            className="mt-1 w-full rounded-md px-3 py-2 text-left text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-8">{children}</main>
    </div>
  );
}
