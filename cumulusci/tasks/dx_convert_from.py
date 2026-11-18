import shutil
from pathlib import Path

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.sfdx import shell_quote
from cumulusci.tasks.sfdx import SFDXBaseTask


class DxConvertFrom(SFDXBaseTask):
    task_options = {
        "extra": {"description": "Append additional options to the command"},
        "src_dir": {
            "description": "The output directory for converted Metadata API contents. Defaults to the project's Metadata API package directory.",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        output = shell_quote(self.options["src_dir"])
        self.options["command"] = f"project convert source -d {output}"

    def _run_task(self):
        src_dir = Path(self.options["src_dir"])
        output = src_dir.resolve()
        if (
            self.project_config.project__source_format != "sfdx"
            and self.project_config.project__package__directory is not None
            and output == Path(self.project_config.mdapi_package_path).resolve()
            and output.exists()
        ):
            raise TaskOptionsError(
                f"Conversion output {src_dir} is the project's Metadata API source directory."
            )
        for package in self.project_config.sfdx_package_directories:
            source = Path(package["path"]).resolve()
            if output.is_relative_to(source) or source.is_relative_to(output):
                raise TaskOptionsError(
                    f"Conversion output {src_dir} overlaps Salesforce DX source {package['path']}."
                )
        unpackaged = Path(self.project_config.unpackaged_path).resolve()
        if output.is_relative_to(unpackaged) or unpackaged.is_relative_to(output):
            raise TaskOptionsError(
                f"Conversion output {src_dir} overlaps unpackaged metadata "
                f"at {self.project_config.unpackaged_path}."
            )
        if src_dir.exists():
            shutil.rmtree(src_dir)
        super()._run_task()
