from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ModelStage

JSONType = JSON().with_variant(JSONB(), "postgresql")


class ModelVersion(UUIDPKMixin, TimestampMixin, Base):
    """A registered, promotable model checkpoint produced by a Job. `name` groups
    versions the way MLflow's registry does (e.g. all "samamba-fraud-detector"
    versions), `version` is a monotonically increasing int per name."""

    __tablename__ = "model_versions"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    plugin_id: Mapped[str] = mapped_column(ForeignKey("plugins.id"), nullable=False)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)

    artifact_uri: Mapped[str] = mapped_column(String(1024), nullable=False)  # MinIO path to checkpoint
    metrics: Mapped[dict] = mapped_column(JSONType, default=dict)  # snapshot copy; MLflow remains source of truth
    stage: Mapped[ModelStage] = mapped_column(Enum(ModelStage), default=ModelStage.NONE, nullable=False)

    job: Mapped["Job"] = relationship(back_populates="model_versions")
