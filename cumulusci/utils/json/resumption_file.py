from typing import Optional
import shutil
from pathlib import Path

from pydantic import validator, root_validator


from ..yaml.model_parser import CCIModel
from cumulusci.core.utils import import_global


class ResumptionFile(CCIModel):
    task_class: str
    state_data: dict
    flow_step: Optional[str]
    task_config: dict
    org: str
    version: float
    _filename: Optional[Path]
    _working_directory: Optional[Path] = None

    def __init__(self, task_state_filename, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__["_filename"] = task_state_filename
        self.state_data.__dict__["_parent"] = self

    @validator("version")
    def validate_version(v):
        assert 1 <= v < 2, v
        return v

    @root_validator
    def uplift_state_data(cls, v):
        class_path = v["task_class"]
        task_class = import_global(class_path)
        task_state_class = task_class.StateData
        state_data = v["state_data"]
        v["state_data"] = task_state_class(**dict(state_data))
        return v

    # TODO: file locking
    def save(self):
        with open(self._filename, "w") as f:
            f.write(
                self.json(
                    indent=2,
                    exclude={
                        "_filename": ...,
                        "_working_directory": ...,
                        "state_data": {"_parent"},
                    },
                )
            )

    @property
    def filename(self):
        return self.__dict__["_filename"]

    def get_working_directory(self):
        if not self._working_directory:
            dirname = Path(str(self.filename)[0 : -len(self.filename.suffix)])
            dirname.mkdir(parents=True, exist_ok=True)
            self.__dict__["_working_directory"] = dirname
        return self._working_directory

    def cleanup(self):
        self._filename.unlink()
        if self._working_directory:
            shutil.rmtree(self._working_directory, ignore_errors=True)
