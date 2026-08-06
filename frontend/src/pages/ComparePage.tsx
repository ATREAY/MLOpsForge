import { useMemo, useState } from "react";

import { useJobsMetrics, useJobs, usePlugins } from "@/api/hooks";
import { Card, PageHeader } from "@/components/ui";

const MAX_SELECTION = 6;

function jobLabel(jobId: string, pluginName: string | undefined) {
  return `${jobId.slice(0, 8)} · ${pluginName ?? "?"}`;
}

export default function ComparePage() {
  const { data: jobs } = useJobs();
  const { data: plugins } = usePlugins();
  const [selected, setSelected] = useState<string[]>([]);
  const [metricKey, setMetricKey] = useState<string>("");

  const finishedJobs = useMemo(() => jobs?.filter((j) => j.status === "finished") ?? [], [jobs]);
  const pluginNameById = useMemo(
    () => Object.fromEntries((plugins ?? []).map((p) => [p.id, p.name])),
    [plugins],
  );

  const metricsResults = useJobsMetrics(selected);
  const metricsByJob = useMemo(() => {
    const map: Record<string, Record<string, number>> = {};
    selected.forEach((jobId, i) => {
      const data = metricsResults[i]?.data;
      if (data) map[jobId] = data;
    });
    return map;
  }, [selected, metricsResults]);

  const selectedJobs = selected.map((id) => finishedJobs.find((j) => j.id === id)).filter(Boolean) as NonNullable<
    ReturnType<typeof finishedJobs.find>
  >[];

  const configKeys = useMemo(() => {
    const keys = new Set<string>();
    selectedJobs.forEach((j) => Object.keys(j.config).forEach((k) => keys.add(k)));
    return Array.from(keys).sort();
  }, [selectedJobs]);

  const metricKeys = useMemo(() => {
    const keys = new Set<string>();
    Object.values(metricsByJob).forEach((m) => Object.keys(m).forEach((k) => keys.add(k)));
    return Array.from(keys).sort();
  }, [metricsByJob]);

  // Metric chosen for the bar chart: prefer "accuracy" if every selected job has it,
  // otherwise fall back to whatever's common, otherwise the first available key.
  const chartMetric = useMemo(() => {
    if (metricKey && metricKeys.includes(metricKey)) return metricKey;
    const commonKeys = metricKeys.filter((k) => selectedJobs.every((j) => metricsByJob[j.id]?.[k] !== undefined));
    return commonKeys.includes("accuracy") ? "accuracy" : (commonKeys[0] ?? metricKeys[0] ?? "");
  }, [metricKey, metricKeys, selectedJobs, metricsByJob]);

  const chartValues = selectedJobs
    .map((j) => ({ job: j, value: metricsByJob[j.id]?.[chartMetric] }))
    .filter((r): r is { job: (typeof selectedJobs)[number]; value: number } => r.value !== undefined);
  const maxChartValue = Math.max(...chartValues.map((r) => r.value), 0.0001);

  function toggle(jobId: string) {
    setSelected((prev) => {
      if (prev.includes(jobId)) return prev.filter((id) => id !== jobId);
      if (prev.length >= MAX_SELECTION) return prev;
      return [...prev, jobId];
    });
  }

  return (
    <div>
      <PageHeader
        title="Compare"
        subtitle="Compare config and live MLflow metrics across finished runs — works for any run, not just ones promoted to the registry."
      />

      <Card className="mb-6">
        <p className="mb-3 text-sm font-medium text-slate-700">
          Select up to {MAX_SELECTION} finished jobs ({selected.length} selected)
        </p>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
          {finishedJobs.map((job) => (
            <label
              key={job.id}
              className="flex cursor-pointer items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50"
            >
              <input
                type="checkbox"
                checked={selected.includes(job.id)}
                onChange={() => toggle(job.id)}
                disabled={!selected.includes(job.id) && selected.length >= MAX_SELECTION}
              />
              <span className="truncate">{jobLabel(job.id, pluginNameById[job.plugin_id])}</span>
            </label>
          ))}
          {finishedJobs.length === 0 && <p className="text-sm text-slate-500">No finished jobs yet.</p>}
        </div>
      </Card>

      {selectedJobs.length > 0 && (
        <>
          <Card className="mb-6 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="py-2 pr-4 font-medium">Field</th>
                  {selectedJobs.map((j) => (
                    <th key={j.id} className="py-2 pr-4 font-medium text-slate-900">
                      {jobLabel(j.id, pluginNameById[j.plugin_id])}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="bg-slate-50">
                  <td colSpan={selectedJobs.length + 1} className="px-1 py-1 text-xs font-semibold uppercase text-slate-400">
                    Config
                  </td>
                </tr>
                {configKeys.map((key) => (
                  <tr key={key} className="border-b border-slate-100">
                    <td className="py-1.5 pr-4 text-slate-500">{key}</td>
                    {selectedJobs.map((j) => (
                      <td key={j.id} className="py-1.5 pr-4 font-mono text-xs text-slate-700">
                        {j.config[key] === undefined ? "—" : String(j.config[key])}
                      </td>
                    ))}
                  </tr>
                ))}
                <tr className="bg-slate-50">
                  <td colSpan={selectedJobs.length + 1} className="px-1 py-1 text-xs font-semibold uppercase text-slate-400">
                    Metrics (live from MLflow)
                  </td>
                </tr>
                {metricKeys.map((key) => (
                  <tr key={key} className="border-b border-slate-100">
                    <td className="py-1.5 pr-4 text-slate-500">{key}</td>
                    {selectedJobs.map((j) => {
                      const value = metricsByJob[j.id]?.[key];
                      return (
                        <td key={j.id} className="py-1.5 pr-4 font-mono text-xs text-slate-700">
                          {value === undefined ? "—" : value.toFixed(4)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
                {metricKeys.length === 0 && (
                  <tr>
                    <td colSpan={selectedJobs.length + 1} className="py-2 text-slate-400">
                      Loading metrics…
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </Card>

          {chartValues.length > 0 && (
            <Card>
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm font-medium text-slate-700">{chartMetric}</p>
                <select
                  className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                  value={chartMetric}
                  onChange={(e) => setMetricKey(e.target.value)}
                >
                  {metricKeys.map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-2">
                {chartValues.map(({ job, value }) => (
                  <div key={job.id} className="flex items-center gap-3">
                    <span className="w-40 shrink-0 truncate text-xs text-slate-600" title={jobLabel(job.id, pluginNameById[job.plugin_id])}>
                      {jobLabel(job.id, pluginNameById[job.plugin_id])}
                    </span>
                    <div className="h-5 flex-1 rounded-sm bg-slate-100">
                      <div
                        className="h-5 rounded-r-[4px] bg-[#256abf]"
                        style={{ width: `${Math.max((value / maxChartValue) * 100, 2)}%` }}
                        title={value.toFixed(4)}
                      />
                    </div>
                    <span className="w-16 shrink-0 text-right font-mono text-xs text-slate-700">{value.toFixed(4)}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
