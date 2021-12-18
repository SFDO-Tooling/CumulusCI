from pathlib import Path

from snowfakery.api import COUNT_REPS

from .snowfakery_run_until import RunUntilBase
from .snowfakery_working_directory import SnowfakeryWorkingDirectory


class SubtaskConfigurator:
    def __init__(
        self,
        recipe: Path,
        run_until: RunUntilBase,
        ignore_row_errors: bool,
    ):
        self.recipe = recipe
        self.run_until = run_until
        self.ignore_row_errors = ignore_row_errors

    # todo: move generate_and_load_initial_portion here

    def data_generator_opts(self, working_dir, recipe_options=None, *args, **kwargs):
        """Generate task options for a data generator"""
        wd = SnowfakeryWorkingDirectory(working_dir)
        name = Path(working_dir).name
        parts = name.rsplit("_", 1)
        batch_size = int(parts[-1])

        return {
            "generator_yaml": str(self.recipe),
            "database_url": wd.database_url,
            "num_records": batch_size,
            "reset_oids": False,
            "continuation_file": wd.continuation_file,
            "num_records_tablename": self.run_until.sobject_name or COUNT_REPS,
            "vars": recipe_options,
        }

    def data_loader_opts(self, working_dir: Path):
        wd = SnowfakeryWorkingDirectory(working_dir)

        options = {
            "mapping": wd.mapping_file,
            "reset_oids": False,
            "database_url": wd.database_url,
            "set_recently_viewed": False,
            "ignore_row_errors": self.ignore_row_errors,
            # don't need to pass loading_rules because they are merged into mapping
        }
        return options
