// Mirrors backend/app/schemas/*.py — keep in sync by hand for now; if the
// surface grows much more, generate this from the OpenAPI schema instead.

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  task_type: string;
  created_at: string;
}

export interface DatasetVersion {
  id: string;
  dataset_id: string;
  version: number;
  storage_uri: string;
  file_hash: string;
  size_bytes: number;
  stats: Record<string, unknown>;
  created_at: string;
}

export interface DatasetWithVersions extends Dataset {
  versions: DatasetVersion[];
}

export interface Plugin {
  id: string;
  name: string;
  version: string;
  description: string | null;
  task_type: string;
  config_schema: Record<string, unknown>;
  default_resources: Record<string, unknown>;
}

export interface Experiment {
  id: string;
  name: string;
  description: string | null;
  mlflow_experiment_id: string | null;
  created_at: string;
}

export type JobStatus = "queued" | "submitted" | "running" | "finished" | "failed" | "cancelled";

export interface Job {
  id: string;
  experiment_id: string;
  plugin_id: string;
  dataset_version_id: string;
  config: Record<string, unknown>;
  status: JobStatus;
  slurm_job_id: string | null;
  mlflow_run_id: string | null;
  logs_uri: string | null;
  checkpoint_uri: string | null;
  error_message: string | null;
  submitted_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export type ModelStage = "none" | "staging" | "production" | "archived";

export interface ModelVersion {
  id: string;
  name: string;
  version: number;
  job_id: string;
  plugin_id: string;
  dataset_version_id: string;
  artifact_uri: string;
  metrics: Record<string, number>;
  stage: ModelStage;
  created_at: string;
}
