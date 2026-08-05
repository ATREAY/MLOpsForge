import type { FormEvent } from "react";
import { useState } from "react";

import { ApiError } from "@/api/client";
import { useCreateDataset, useDatasets, useDeleteDataset } from "@/api/hooks";
import { Button, Card, PageHeader } from "@/components/ui";

export default function DatasetsPage() {
  const { data: datasets, isLoading } = useDatasets();
  const createDataset = useCreateDataset();
  const deleteDataset = useDeleteDataset();

  function handleDelete(id: string, name: string) {
    if (!window.confirm(`Delete dataset "${name}"? This also deletes all its versions.`)) return;
    deleteDataset.mutate(id, {
      onError: (err) => {
        const message = err instanceof ApiError ? err.message : "Failed to delete dataset.";
        window.alert(message);
      },
    });
  }

  const [name, setName] = useState("");
  const [taskType, setTaskType] = useState("graph-classification");
  const [description, setDescription] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    createDataset.mutate(
      { name, task_type: taskType, description: description || undefined },
      { onSuccess: () => setName("") },
    );
  }

  return (
    <div>
      <PageHeader title="Datasets" subtitle="Register and version datasets used to train plugins." />

      <Card className="mb-6">
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Name</label>
            <input
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="ethereum-fraud-transactions"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Task type</label>
            <input
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              value={taskType}
              onChange={(e) => setTaskType(e.target.value)}
            />
          </div>
          <div className="flex-1">
            <label className="mb-1 block text-xs font-medium text-slate-600">Description</label>
            <input
              className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={createDataset.isPending}>
            {createDataset.isPending ? "Creating…" : "Register dataset"}
          </Button>
        </form>
        <p className="mt-2 text-xs text-slate-400">
          To register a version's file, use <code>scripts/register_dataset.py</code> after creating the dataset here.
        </p>
      </Card>

      <Card>
        {isLoading && <p className="text-sm text-slate-500">Loading…</p>}
        {datasets && datasets.length === 0 && <p className="text-sm text-slate-500">No datasets registered yet.</p>}
        {datasets && datasets.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="pb-2 font-medium">Name</th>
                <th className="pb-2 font-medium">Task type</th>
                <th className="pb-2 font-medium">Description</th>
                <th className="pb-2 font-medium">Created</th>
                <th className="pb-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 font-medium text-slate-900">{d.name}</td>
                  <td className="py-2 text-slate-600">{d.task_type}</td>
                  <td className="py-2 text-slate-500">{d.description ?? "—"}</td>
                  <td className="py-2 text-slate-500">{new Date(d.created_at).toLocaleString()}</td>
                  <td className="py-2">
                    <Button variant="danger" onClick={() => handleDelete(d.id, d.name)}>
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
