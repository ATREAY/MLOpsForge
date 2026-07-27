from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin

# JSONB on Postgres, plain JSON on SQLite (dev fallback) — same column, dialect picks the type.
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Dataset(UUIDPKMixin, TimestampMixin, Base):
    """A logical dataset (e.g. 'ethereum-transactions'). Immutable identity; the
    actual data lives in one or more DatasetVersion rows."""

    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "graph-classification"
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="datasets")
    versions: Mapped[list["DatasetVersion"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", order_by="DatasetVersion.version"
    )


class DatasetVersion(UUIDPKMixin, TimestampMixin, Base):
    """One immutable snapshot of a dataset. `storage_uri` points into MinIO;
    Postgres only ever holds metadata about the blob, never the blob itself."""

    __tablename__ = "dataset_versions"

    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stats: Mapped[dict] = mapped_column(JSONType, default=dict)  # num_nodes, num_edges, num_samples, ...

    dataset: Mapped["Dataset"] = relationship(back_populates="versions")
