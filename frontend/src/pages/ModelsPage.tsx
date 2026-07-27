import { useState } from "react";

import { useJobs, useModelVersions, usePromoteJobToModel, useUpdateModelStage } from "@/api/hooks";
import type { ModelStage } from "@/api/types";
import { Button, Card, ModelStageBadge, PageHeader } from "@/components/ui";

const STAGES: ModelStage[] = ["none", "staging", "production", "archived"];

export default function ModelsPage() {
  const { data: models, isLoading } = useModelVersions();
  const { data: jobs } = useJobs();
  const promote = usePromoteJobToModel();
  const updateStage = useUpdateModelStage();

  const [jobId, setJobId] = useState("");
  const [modelName, setModelName] = useState("");

  const finishedJobs = jobs?.filter((j) => j.status === "finished");

  function handlePromote() {
    if (!jobId || !modelName.trim()) return;
    promote.mutate({ jobId, name: modelName }, { onSuccess: () => setModelName("") });
  }

  return (
    <div>
      <PageHeader title="Model registry" subtitle="Promote a finished job's checkpoint to a versioned model." />

      <Card className="mb-6">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Finished job</label>
            <select
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
            >
              <option value="">Select…</option>
              {finishedJobs?.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Model name</label>
            <input
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="samamba-ethereum-fraud-detector"
            />
          </div>
          <Button onClick={handlePromote} disabled={!jobId || !modelName.trim() || promote.isPending}>
            {promote.isPending ? "Promoting…" : "Promote to registry"}
          </Button>
        </div>
        {promote.isError && <p className="mt-2 text-sm text-red-600">{(promote.error as Error).message}</p>}
      </Card>

      <Card>
        {isLoading && <p className="text-sm text-slate-500">Loading…</p>}
        {models && models.length === 0 && <p className="text-sm text-slate-500">No models registered yet.</p>}
        {models && models.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="pb-2 font-medium">Name</th>
                <th className="pb-2 font-medium">Version</th>
                <th className="pb-2 font-medium">Metrics</th>
                <th className="pb-2 font-medium">Stage</th>
                <th className="pb-2 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.id} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 font-medium text-slate-900">{m.name}</td>
                  <td className="py-2 text-slate-600">v{m.version}</td>
                  <td className="py-2 text-slate-600">
                    {Object.entries(m.metrics)
                      .map(([k, v]) => `${k}=${v.toFixed(3)}`)
                      .join(", ") || "—"}
                  </td>
                  <td className="py-2">
                    <select
                      className="rounded-md border border-slate-300 px-1.5 py-1 text-xs"
                      value={m.stage}
                      onChange={(e) => updateStage.mutate({ modelVersionId: m.id, stage: e.target.value })}
                    >
                      {STAGES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>{" "}
                    <ModelStageBadge stage={m.stage} />
                  </td>
                  <td className="py-2 text-slate-500">{new Date(m.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
