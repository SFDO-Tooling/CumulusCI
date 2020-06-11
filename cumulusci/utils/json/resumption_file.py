from typing import Optional

from pydantic import validator

from ..yaml.model_parser import CCIModel
from cumulusci.utils.fileutils import FSResource

# TODO: redo this around fs and FSResource instead of pathlib


class ResumptionFile(CCIModel):
    task_class: str
    state_data: dict
    flow_step: Optional[str]
    task_config: dict
    org: str
    version: float
    _fs_resource: Optional[FSResource]
    _working_directory: Optional[FSResource] = None

    def __init__(self, task_state_fs_resource: FSResource, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__["_fs_resource"] = task_state_fs_resource

    @validator("version")
    def validate_version(v):
        assert 1 <= v < 2, v
        return v

    # TODO: file locking
    def save(self):
        with self._fs_resource.open("w") as f:
            f.write(
                self.json(
                    indent=2, exclude={"_fs_resource": ..., "_working_directory": ...},
                )
            )

    @property
    def filename(self):
        return self.__dict__["_fs_resource"].filename

    def get_working_directory(self):
        if not self._working_directory:
            dirname = FSResource(str(self.filename)[0 : -len(self.filename.suffix)])
            dirname.mkdir(parents=True, exist_ok=True)
            self.__dict__["_working_directory"] = dirname
        return self._working_directory

    def cleanup(self):
        if self._fs_resource and self._fs_resource.exists():
            self._fs_resource.remove()
        if self._working_directory and self._working_directory.exists():
            self._fs_resource.removedir(self._working_directory, ignore_errors=True)
