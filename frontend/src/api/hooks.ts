import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import type {
  Dataset,
  DatasetVersion,
  DatasetWithVersions,
  Experiment,
  Job,
  ModelVersion,
  Plugin,
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

export function useJobs(refetchIntervalMs = 5000) {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.get<Job[]>("/jobs"),
    refetchInterval: refetchIntervalMs,
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

// Re-exported for pages that need a raw DatasetVersion type without pulling
// in the whole api/types module.
export type { DatasetVersion };
