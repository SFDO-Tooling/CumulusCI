import typing as T
from pathlib import Path

from snowfakery.api import COUNT_REPS

from .snowfakery_run_until import RunUntilBase
from .snowfakery_working_directory import SnowfakeryWorkingDirectory


class SubtaskConfigurator:
    def __init__(
        self,
        recipe: Path,
        run_until: RunUntilBase,
        bulk_mode: T.Literal["Serial", "Parallel"],
        load_options: dict,
    ):
        self.recipe = recipe
        self.run_until = run_until
        self.bulk_mode = bulk_mode
        self.load_options = load_options

    # todo: move generate_and_load_initial_portion here

    def data_generator_opts(self, working_dir, recipe_options=None, *args, **kwargs):
        """Generate task options for a data generator"""
        wd = SnowfakeryWorkingDirectory(working_dir)
        name = Path(working_dir).name
        parts = name.rsplit("_", 1)
        batch_size = int(parts[-1])

        # The pid is the tool that ensures that every uniqueid is
        # unique even across different processes.
        #
        # big_ids ensures that the pid is incorporated into the ids.
        plugin_options = {
            "pid": str(wd.index),
            "big_ids": "True",
        }

        return {
            "generator_yaml": str(self.recipe),
            "database_url": wd.database_url,
            "num_records": batch_size,
            "reset_oids": False,
            "continuation_file": wd.continuation_file,
            "num_records_tablename": self.run_until.sobject_name or COUNT_REPS,
            "vars": recipe_options,
            "plugin_options": plugin_options,
        }

    def data_loader_opts(self, working_dir: Path):
        wd = SnowfakeryWorkingDirectory(working_dir)

        options = {
            "mapping": wd.mapping_file,
            "reset_oids": False,
            "database_url": wd.database_url,
            "set_recently_viewed": False,
            "bulk_mode": self.bulk_mode,
            **self.load_options,
            # don't need to pass loading_rules because they are merged into mapping
        }
        return options
