from typing import Optional

from cumulusci.core.config import OrgConfig
from cumulusci.core.datasets import Dataset
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.org_schema import Filters, get_org_schema
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask


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
    org_config: OrgConfig

    def _run_task(self):
        name = self._find_dataset()
        if not name:
            return
        with get_org_schema(
            self.sf,
            self.org_config,
            include_counts=True,
            filters=[Filters.extractable, Filters.createable],
        ) as schema, Dataset(
            name,
            self.project_config,
            self.sf,
            self.org_config,
            schema,
        ) as dataset:
            self.return_values = dataset.load(self.options, self.logger) or {}
        return self.return_values

    def _find_dataset(self) -> Optional[str]:
        def dataset_for_name(name: str):
            return Dataset(name, self.project_config, self.sf, self.org_config)

        checked_folders = []
        dataset_name = self.options.get("dataset")
        if dataset_name:
            dsf = dataset_for_name(dataset_name)
            if dsf.exists():
                return dataset_name
            else:
                raise TaskOptionsError(f"Could not find dataset directory {dsf.path}")

        config_name = self.org_config.lookup("config_name")
        if config_name:
            config_dsf = dataset_for_name(config_name)
            if config_dsf.exists() and (
                config_dsf.data_file.exists() or config_dsf.snowfakery_recipe.exists()
            ):
                return config_name
            else:
                checked_folders.append(config_dsf.path)

        default_dsf = dataset_for_name("default")
        if default_dsf.exists():
            return "default"
        else:
            checked_folders.append(default_dsf.path)

        checked_folders = " and ".join(
            str(f.relative_to(self.project_config.repo_root)) for f in checked_folders
        )
        # Don't throw exception in this case
        self.logger.info(
            f"No contextual sample data found. (looked in '{checked_folders}') Skipping step."
        )

        return None
