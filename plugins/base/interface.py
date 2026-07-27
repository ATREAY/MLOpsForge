from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrainResult:
    """What a plugin hands back after a training run. `checkpoint_path` must be a
    file training-service can SFTP off the compute node; `metrics` are logged
    straight into MLflow as-is, so keys should be flat and values scalar."""

    checkpoint_path: str
    metrics: dict[str, float]
    artifacts: dict[str, str] = field(default_factory=dict)  # label -> local file path (plots, configs, ...)


class BaseModelPlugin(ABC):
    """The entire integration surface between MLOpsForge and a model. The backend
    and training-service only ever interact with a plugin through this interface
    — see plugins/README.md."""

    name: str
    version: str
    task_type: str

    @abstractmethod
    def get_config_schema(self) -> dict:
        """JSON Schema describing this plugin's hyperparameters. The frontend
        renders a form from this; the backend validates job configs against it."""
        raise NotImplementedError

    @abstractmethod
    def train(self, dataset_path: str, config: dict, output_dir: str) -> TrainResult:
        """Runs inside the Slurm job. `dataset_path` is a local path
        (training-service has already pulled the dataset version down);
        `output_dir` is where checkpoints/artifacts should be written."""
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, model_path: str, dataset_path: str, config: dict) -> dict[str, float]:
        raise NotImplementedError

    @abstractmethod
    def predict(self, model_path: str, inputs: Any) -> Any:
        """Used by the inference service. Implementations are expected to load
        and cache the model themselves (e.g. on first call) rather than assume
        the caller keeps a plugin instance warm."""
        raise NotImplementedError
