from pydantic import BaseModel, ConfigDict


class PluginRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    description: str | None
    task_type: str
    config_schema: dict
    default_resources: dict
