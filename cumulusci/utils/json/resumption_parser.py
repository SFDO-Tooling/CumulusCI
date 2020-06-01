from typing import Optional
from ..yaml.model_parser import CCIModel
from pydantic import validator


class TaskConfigData(CCIModel):
    options: dict


class ResumptionFile(CCIModel):
    task_class: str
    state_data: dict
    flow_step: Optional[str]
    task_config: TaskConfigData
    version: float

    @validator("version")
    def validate_version(v):
        assert 1 <= v < 2, v
        return v
