"""Single import point Alembic's env.py uses for autogenerate: importing this
module registers every model on `Base.metadata` even though nothing in this
file references them directly."""

from app.db.base_class import Base  # noqa: F401
from app.models import (  # noqa: F401
    Dataset,
    DatasetVersion,
    Experiment,
    Job,
    ModelVersion,
    Plugin,
    User,
)
