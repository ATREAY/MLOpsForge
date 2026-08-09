import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import type {
  Dataset,
  DatasetVersion,
  DatasetWithVersions,
  Experiment,
  Job,
  ModelVersion,
  Plugin,
  PredictResponse,
} from "@/api/types";

// -- Datasets ---------------------------------------------------------------

export function useDatasets() {
  return useQuery({ queryKey: ["datasets"], queryFn: () => api.get<Dataset[]>("/datasets") });
}

export function useDataset(id: string | undefined) {
  return useQuery({
    queryKey: ["datasets", id],
    queryFn: () => api.get<DatasetWithVersions>(`/datasets/${id}`),
    enabled: !!id,
  });
}

export function useCreateDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; description?: string; task_type: string }) =>
      api.post<Dataset>("/datasets", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }),
  });
}

export function useDeleteDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datasetId: string) => api.del<void>(`/datasets/${datasetId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }),
  });
}

// -- Plugins ------------------------------------------------------------------

export function usePlugins() {
  return useQuery({ queryKey: ["plugins"], queryFn: () => api.get<Plugin[]>("/plugins") });
}

// -- Experiments --------------------------------------------------------------

export function useExperiments() {
  return useQuery({ queryKey: ["experiments"], queryFn: () => api.get<Experiment[]>("/experiments") });
}

export function useCreateExperiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; description?: string }) => api.post<Experiment>("/experiments", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["experiments"] }),
  });
}

// -- Jobs -----------------------------------------------------------------

// WebSocket push (see api/ws.ts, mounted in Layout) keeps this cache live;
// the interval here is just a fallback in case the socket is down.
export function useJobs(refetchIntervalMs = 30000) {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.get<Job[]>("/jobs"),
    refetchInterval: refetchIntervalMs,
  });
}

// Live from MLflow (see backend's GET /jobs/{id}/metrics) — works for any
// finished job, not just ones promoted to the model registry.
export function useJobMetrics(jobId: string | undefined) {
  return useQuery({
    queryKey: ["jobs", jobId, "metrics"],
    queryFn: () => api.get<Record<string, number>>(`/jobs/${jobId}/metrics`),
    enabled: !!jobId,
    staleTime: 60000, // finished jobs' metrics never change; no need to refetch aggressively
  });
}

// Same data source as useJobMetrics, but for an arbitrary set of jobs at once
// (the Compare page's multi-select) — useQueries rather than N calls to
// useJobMetrics, since hooks can't be called in a loop.
export function useJobsMetrics(jobIds: string[]) {
  return useQueries({
    queries: jobIds.map((jobId) => ({
      queryKey: ["jobs", jobId, "metrics"],
      queryFn: () => api.get<Record<string, number>>(`/jobs/${jobId}/metrics`),
      staleTime: 60000,
    })),
  });
}

export interface CreateJobPayload {
  experiment_id: string;
  plugin_name: string;
  dataset_version_id: string;
  config: Record<string, unknown>;
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateJobPayload) => api.post<Job>("/jobs", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useCancelJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => api.post<Job>(`/jobs/${jobId}/cancel`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

// -- Model registry ---------------------------------------------------------

export function useModelVersions(name?: string) {
  return useQuery({
    queryKey: ["models", name ?? "all"],
    queryFn: () => api.get<ModelVersion[]>(name ? `/models?name=${encodeURIComponent(name)}` : "/models"),
  });
}

export function useModelVersion(id: string | undefined) {
  return useQuery({
    queryKey: ["models", id],
    queryFn: () => api.get<ModelVersion>(`/models/${id}`),
    enabled: !!id,
  });
}

export function usePromoteJobToModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId, name }: { jobId: string; name: string }) =>
      api.post<ModelVersion>(`/models/from-job/${jobId}?name=${encodeURIComponent(name)}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["models"] }),
  });
}

export function useUpdateModelStage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ modelVersionId, stage }: { modelVersionId: string; stage: string }) =>
      api.patch<ModelVersion>(`/models/${modelVersionId}/stage`, { stage }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["models"] }),
  });
}

// -- Inference ----------------------------------------------------------------

export function usePredict() {
  return useMutation({
    mutationFn: ({ modelVersionId, inputs }: { modelVersionId: string; inputs: unknown }) =>
      api.post<PredictResponse>(`/inference/predict/${modelVersionId}`, { inputs }),
  });
}

// Re-exported for pages that need a raw DatasetVersion type without pulling
// in the whole api/types module.
export type { DatasetVersion };
