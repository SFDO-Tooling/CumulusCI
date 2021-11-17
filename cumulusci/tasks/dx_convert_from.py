from pathlib import Path

from cumulusci.tasks.sfdx import SFDXBaseTask


class DxConvertFrom(SFDXBaseTask):
    task_options = {
        "command": {
            "description": "The full command to run with the sfdx cli.",
            "required": True,
        },
        "extra": {"description": "Append additional options to the command"},
        "src_dir": {
            "description": "The path to the src directory where converted contents will be stored. Defaults to src/"
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        if "src_dir" not in self.options:
            self.options["src_dir"] = "src"

        # append the -d option to sfdx force:source:convert
        self.options[
            "command"
        ] = f"{self.options['command']} -d {self.options['src_dir']}"

    def _run_task(self):
        src_dir = Path(self.options["src_dir"])
        if src_dir.exists():
            self._clear_directory(src_dir)
        super()._run_task()

    def _clear_directory(self, root_dir: Path):
        """Recursively remove all contents in given directory"""
        for item in root_dir.iterdir():
            if item.is_dir():
                self._clear_directory(item)
                item.rmdir()
            else:
                item.unlink()
