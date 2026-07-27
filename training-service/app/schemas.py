from pydantic import BaseModel


class SubmitRequest(BaseModel):
    job_id: str
    plugin_entrypoint: str
    dataset_uri: str
    config: dict
    resources: dict = {}
    callback_url: str
    mlflow_experiment_id: str | None = None
    mlflow_tracking_uri: str | None = None


class SubmitResponse(BaseModel):
    slurm_job_id: str
