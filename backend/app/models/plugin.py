from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Plugin(UUIDPKMixin, TimestampMixin, Base):
    """Mirrors a plugin directory under plugins/<name>/plugin.yaml. Synced into
    the DB on backend startup (see app.services.plugin_registry) so the frontend
    can list/filter plugins without touching the filesystem, and so Job/Experiment
    rows can foreign-key to a stable plugin id."""

    __tablename__ = "plugins"

    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    config_schema: Mapped[dict] = mapped_column(JSONType, default=dict)
    default_resources: Mapped[dict] = mapped_column(JSONType, default=dict)  # gpus, partition, time_limit
    entrypoint: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "plugins.samamba.plugin:SAMambaPlugin"
