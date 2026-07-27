import enum


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    SUBMITTED = "submitted"  # sbatch accepted, waiting in Slurm's own queue
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModelStage(str, enum.Enum):
    NONE = "none"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"
