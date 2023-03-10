import shutil
from pathlib import Path

from cumulusci.tasks.sfdx import SFDXBaseTask


class DxConvertFrom(SFDXBaseTask):
    """Call the sfdx cli to convert sfdx source format to mdapi format"""

    task_options = {
        "extra": {"description": "Append additional options to the command"},
        "resolve_sfdx_package_dirs": {
            "description": "If True, will resolve package directory paths in sfdx-project.json and append them to the source:convert command via --sourcepath. If you need to use --sourcepath, use the extra option to pass the --sourcepath argument instead of this option",
        },
        "src_dir": {
            "description": "The path to the src directory where converted contents will be stored. Defaults to src/",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        # append command  -d option to sfdx force:source:convert
        self.options["command"] = f"force:source:convert -d {self.options['src_dir']}"

        if self.options["resolve_sfdx_package_dirs"]:
            package_directories = self._resolve_sfdx_package_dirs()
            if package_directories:
                self.options["command"] += f" --sourcepath {package_directories}"

    def _run_task(self):
        src_dir = Path(self.options["src_dir"])
        if src_dir.exists():
            shutil.rmtree(src_dir)
        super()._run_task()

    def _resolve_sfdx_package_dirs(self):
        return ",".join(
            [
                node["path"]
                for node in self.project_config.sfdx_project_config.get(
                    "packageDirectories", []
                )
            ]
        )
