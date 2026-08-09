import type { FormEvent } from "react";
import { useState } from "react";

import { useCreateExperiment, useExperiments } from "@/api/hooks";
import { Button, Card, PageHeader } from "@/components/ui";

export default function ExperimentsPage() {
  const { data: experiments, isLoading } = useExperiments();
  const createExperiment = useCreateExperiment();
  const [name, setName] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    createExperiment.mutate({ name }, { onSuccess: () => setName("") });
  }

  return (
    <div>
      <PageHeader
        title="Experiments"
        subtitle="Named groupings of training runs. Each maps 1:1 to an MLflow experiment."
      />

      <Card className="mb-6">
        <form onSubmit={handleSubmit} className="flex items-end gap-3">
          <div className="flex-1">
            <label className="mb-1 block text-xs font-medium text-slate-400">Name</label>
            <input
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="samamba-ethereum-baseline"
            />
          </div>
          <Button type="submit" disabled={createExperiment.isPending}>
            {createExperiment.isPending ? "Creating…" : "Create experiment"}
          </Button>
        </form>
      </Card>

      <Card>
        {isLoading && <p className="text-sm text-slate-400">Loading…</p>}
        {experiments && experiments.length === 0 && (
          <p className="text-sm text-slate-400">No experiments yet — create one above before submitting a job.</p>
        )}
        {experiments && experiments.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left text-slate-500">
                  <th className="pb-2 font-medium">Name</th>
                  <th className="pb-2 font-medium">MLflow experiment</th>
                  <th className="pb-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((exp) => (
                  <tr key={exp.id} className="border-b border-slate-800/60 last:border-0">
                    <td className="py-2 font-medium text-slate-100">{exp.name}</td>
                    <td className="py-2 text-slate-500">{exp.mlflow_experiment_id ?? "not linked"}</td>
                    <td className="py-2 text-slate-500">{new Date(exp.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
