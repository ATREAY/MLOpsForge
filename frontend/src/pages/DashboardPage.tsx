import { useDatasets, useExperiments, useJobs, useModelVersions } from "@/api/hooks";
import { Card, PageHeader } from "@/components/ui";

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <Card>
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-slate-900">{value}</p>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: datasets } = useDatasets();
  const { data: experiments } = useExperiments();
  const { data: jobs } = useJobs();
  const { data: models } = useModelVersions();

  const activeJobs = jobs?.filter((j) => j.status === "running" || j.status === "submitted" || j.status === "queued");

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Model-agnostic ML infrastructure: train, track, and serve any plugin on the Slurm compute plane."
      />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Datasets" value={datasets?.length ?? "—"} />
        <StatCard label="Experiments" value={experiments?.length ?? "—"} />
        <StatCard label="Active jobs" value={activeJobs?.length ?? "—"} />
        <StatCard label="Registered models" value={models?.length ?? "—"} />
      </div>
    </div>
  );
}
