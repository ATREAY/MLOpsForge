from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    task_type: str


class DatasetVersionCreate(BaseModel):
    storage_uri: str
    file_hash: str
    size_bytes: int
    stats: dict = {}


class DatasetVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    version: int
    storage_uri: str
    file_hash: str
    size_bytes: int
    stats: dict
    created_at: datetime


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    task_type: str
    created_at: datetime


class DatasetWithVersions(DatasetRead):
    versions: list[DatasetVersionRead] = []
