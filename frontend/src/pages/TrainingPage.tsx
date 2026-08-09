import { useEffect, useMemo, useState } from "react";

import { useCancelJob, useCreateJob, useDataset, useDatasets, useExperiments, useJobs, usePlugins } from "@/api/hooks";
import { Button, Card, JobStatusBadge, PageHeader } from "@/components/ui";

interface ConfigSchemaProperty {
  type: "number" | "integer" | "string";
  default?: number | string;
  minimum?: number;
}

function ConfigForm({
  schema,
  config,
  onChange,
}: {
  schema: Record<string, unknown>;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}) {
  const properties = (schema.properties ?? {}) as Record<string, ConfigSchemaProperty>;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
      {Object.entries(properties).map(([key, prop]) => (
        <div key={key}>
          <label className="mb-1 block font-mono text-xs font-medium text-slate-400">{key}</label>
          <input
            type={prop.type === "string" ? "text" : "number"}
            step={prop.type === "integer" ? 1 : "any"}
            min={prop.minimum}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100"
            value={(config[key] as string | number | undefined) ?? ""}
            onChange={(e) => {
              const raw = e.target.value;
              const value = prop.type === "string" ? raw : raw === "" ? "" : Number(raw);
              onChange({ ...config, [key]: value });
            }}
          />
        </div>
      ))}
    </div>
  );
}

export default function TrainingPage() {
  const { data: experiments } = useExperiments();
  const { data: plugins } = usePlugins();
  const { data: datasets } = useDatasets();
  const { data: jobs } = useJobs();
  const createJob = useCreateJob();
  const cancelJob = useCancelJob();

  const [experimentId, setExperimentId] = useState("");
  const [pluginName, setPluginName] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [datasetVersionId, setDatasetVersionId] = useState("");
  const [config, setConfig] = useState<Record<string, unknown>>({});

  const { data: dataset } = useDataset(datasetId || undefined);
  const selectedPlugin = plugins?.find((p) => p.name === pluginName);

  // Reset the config form to the plugin's defaults whenever the plugin changes.
  useEffect(() => {
    if (!selectedPlugin) return;
    const properties = (selectedPlugin.config_schema.properties ?? {}) as Record<string, ConfigSchemaProperty>;
    const defaults = Object.fromEntries(Object.entries(properties).map(([k, v]) => [k, v.default ?? ""]));
    setConfig(defaults);
  }, [selectedPlugin]);

  const canSubmit = useMemo(
    () => !!experimentId && !!pluginName && !!datasetVersionId,
    [experimentId, pluginName, datasetVersionId],
  );

  function handleSubmit() {
    if (!canSubmit) return;
    createJob.mutate(
      { experiment_id: experimentId, plugin_name: pluginName, dataset_version_id: datasetVersionId, config },
      { onSuccess: () => setDatasetVersionId("") },
    );
  }

  return (
    <div>
      <PageHeader title="Training" subtitle="Submit a job to the Slurm compute plane and watch the queue." />

      <Card className="mb-6">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Experiment</label>
            <select
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100"
              value={experimentId}
              onChange={(e) => setExperimentId(e.target.value)}
            >
              <option value="">Select…</option>
              {experiments?.map((exp) => (
                <option key={exp.id} value={exp.id}>
                  {exp.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Plugin</label>
            <select
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100"
              value={pluginName}
              onChange={(e) => setPluginName(e.target.value)}
            >
              <option value="">Select…</option>
              {plugins?.map((p) => (
                <option key={p.id} value={p.name}>
                  {p.name} ({p.task_type})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Dataset</label>
            <select
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100"
              value={datasetId}
              onChange={(e) => {
                setDatasetId(e.target.value);
                setDatasetVersionId("");
              }}
            >
              <option value="">Select…</option>
              {datasets?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          {dataset && (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400">Dataset version</label>
              <select
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100"
                value={datasetVersionId}
                onChange={(e) => setDatasetVersionId(e.target.value)}
              >
                <option value="">Select…</option>
                {dataset.versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {selectedPlugin && (
          <div className="mt-4 border-t border-slate-800 pt-4">
            <p className="mb-2 text-xs font-medium text-slate-400">Hyperparameters</p>
            <ConfigForm schema={selectedPlugin.config_schema} config={config} onChange={setConfig} />
          </div>
        )}

        <div className="mt-4">
          <Button onClick={handleSubmit} disabled={!canSubmit || createJob.isPending}>
            {createJob.isPending ? "Submitting…" : "Submit training job"}
          </Button>
          {createJob.isError && <p className="mt-2 text-sm text-red-400">{(createJob.error as Error).message}</p>}
        </div>
      </Card>

      <Card>
        <p className="mb-3 text-sm font-medium text-slate-300">Job queue</p>
        {jobs && jobs.length === 0 && <p className="text-sm text-slate-400">No jobs submitted yet.</p>}
        {jobs && jobs.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left text-slate-500">
                  <th className="pb-2 font-medium">Job</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Slurm job id</th>
                  <th className="pb-2 font-medium">Submitted</th>
                  <th className="pb-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} className="border-b border-slate-800/60 last:border-0">
                    <td className="py-2 font-mono text-xs text-slate-400">{job.id.slice(0, 8)}</td>
                    <td className="py-2">
                      <JobStatusBadge status={job.status} />
                    </td>
                    <td className="py-2 font-mono text-slate-400">{job.slurm_job_id ?? "—"}</td>
                    <td className="py-2 text-slate-500">
                      {job.submitted_at ? new Date(job.submitted_at).toLocaleString() : "—"}
                    </td>
                    <td className="py-2">
                      {(job.status === "queued" || job.status === "submitted" || job.status === "running") && (
                        <Button variant="danger" onClick={() => cancelJob.mutate(job.id)}>
                          Cancel
                        </Button>
                      )}
                    </td>
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
