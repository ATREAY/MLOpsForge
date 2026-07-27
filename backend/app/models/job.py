from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import JobStatus

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Job(UUIDPKMixin, TimestampMixin, Base):
    """One training run submitted to the compute plane. Tracks both MLOpsForge's
    own lifecycle (status) and the underlying Slurm job id, so `training-service`
    can reconcile state via `sacct` even after a backend restart."""

    __tablename__ = "jobs"

    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    plugin_id: Mapped[str] = mapped_column(ForeignKey("plugins.id"), nullable=False)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)

    config: Mapped[dict] = mapped_column(JSONType, default=dict)  # resolved hyperparams, validated against plugin schema
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)

    slurm_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    logs_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    checkpoint_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    experiment: Mapped["Experiment"] = relationship(back_populates="jobs")
    model_versions: Mapped[list["ModelVersion"]] = relationship(back_populates="job")
