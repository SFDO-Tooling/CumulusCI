from pathlib import Path

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.tasks.bulkdata.snowfakery import Snowfakery
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class LoadSampleData(BaseSalesforceApiTask):
    """Loads contextual sample data based on repo."""

    task_options = {
        "dataset": {
            "description": "The name of the dataset. If none is provided, it will use the scratch org config name (e.g. 'dev', 'qa') or fall back to 'default'."
        },
        "ignore_row_errors": {
            "description": "If True, allow the load to continue even if individual rows fail to load."
        },
        "drop_missing_schema": {
            "description": "Set to True to skip any missing objects or fields instead of stopping with an error."
        },
        "set_recently_viewed": {
            "description": "By default, the first 1000 records inserted via the Bulk API will be set as recently viewed. If fewer than 1000 records are inserted, existing objects of the same type being inserted will also be set as recently viewed.",
        },
    }

    def _run_task(self):
        dataset_dir = self.find_dataset()
        self.return_values = self._load_sample_data(dataset_dir)
        return self.return_values

    def find_dataset(self):
        dataset_name = self.options.get("dataset")
        if dataset_name:
            named_dataset_dir = Path("datasets", dataset_name)
            if named_dataset_dir.exists():
                return named_dataset_dir
            else:
                raise TaskOptionsError(
                    f"Could not find dataset directory {named_dataset_dir}"
                )

        config_name = self.org_config.lookup("config_name")
        config_based_dataset_dir = Path("datasets", config_name)
        if config_based_dataset_dir.exists():
            return config_based_dataset_dir

        default_dataset_dir = Path("datasets", "default")
        if default_dataset_dir.exists():
            return default_dataset_dir
        # Don't throw exception in this case
        self.logger.info(
            f"No contextual sample data found. (looked in 'datasets/default' and 'datasets/{config_name}') Skipping step."
        )

    def _load_sample_data(self, path: Path):
        name = path.name
        snowfakery_path = path / f"{name}.recipe.yml"
        sql_path = path / f"{name}.dataset.sql"
        mapping_path = path / f"{name}.mapping.yml"
        if snowfakery_path.exists():
            if sql_path.exists():
                raise TaskOptionsError(
                    f"{path} includes both a Snowfakery recipe and a SQL file"
                )
            return self._snowfakery_dataload(snowfakery_path)
        elif sql_path.exists():
            if not mapping_path.exists():
                raise TaskOptionsError("Cannot load from SQL without a mapping file.")
            return self._sql_dataload(sql_path, mapping_path)
        else:
            raise TaskOptionsError(
                f"Cannot find either {snowfakery_path} or {sql_path}"
            )

    def _snowfakery_dataload(self, recipe: Path) -> dict:
        subtask_config = TaskConfig(
            {"options": {**self.options, "recipe": str(recipe)}}
        )
        subtask = Snowfakery(
            project_config=self.project_config,
            task_config=subtask_config,
            org_config=self.org_config,
            flow=self.flow,
            name=self.name,
            stepnum=self.stepnum,
            logger=self.logger,
        )
        subtask()
        return subtask.return_values

    def _sql_dataload(self, sql_path: Path, mapping_path: Path) -> dict:
        subtask_config = TaskConfig(
            {
                "options": {
                    **self.options,
                    "sql_path": str(sql_path),
                    "mapping": str(mapping_path),
                }
            }
        )
        subtask = LoadData(
            project_config=self.project_config,
            task_config=subtask_config,
            org_config=self.org_config,
            flow=self.flow,
            name=self.name,
            stepnum=self.stepnum,
            logger=self.logger,
        )
        subtask()
        return subtask.return_values
