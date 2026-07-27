from pydantic import BaseModel


class SubmitRequest(BaseModel):
    job_id: str
    plugin_entrypoint: str
    dataset_uri: str
    config: dict
    resources: dict = {}
    callback_url: str


class SubmitResponse(BaseModel):
    slurm_job_id: str
