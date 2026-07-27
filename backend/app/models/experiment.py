from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin


class Experiment(UUIDPKMixin, TimestampMixin, Base):
    """A named grouping of Job runs (e.g. 'samamba-ethereum-hparam-sweep'), the
    unit MLflow calls an experiment. MLOpsForge stores the identity + ownership
    here and mirrors it 1:1 into MLflow via mlflow_experiment_id."""

    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    mlflow_experiment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="experiments")
    jobs: Mapped[list["Job"]] = relationship(back_populates="experiment")
