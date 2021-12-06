import shutil
from pathlib import Path

from cumulusci.tasks.sfdx import SFDXBaseTask


class DxConvertFrom(SFDXBaseTask):
    task_options = {
        "extra": {"description": "Append additional options to the command"},
        "src_dir": {
            "description": "The path to the src directory where converted contents will be stored. Defaults to src/",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        # append command  -d option to sfdx} force:source:convert
        self.options["command"] = f"force:source:convert -d {self.options['src_dir']}"

    def _run_task(self):
        src_dir = Path(self.options["src_dir"])
        if src_dir.exists():
            shutil.rmtree(src_dir)
        super()._run_task()
