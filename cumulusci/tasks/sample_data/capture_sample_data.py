from pathlib import Path

from cumulusci.core.config.org_config import OrgConfig
from cumulusci.core.datasets import Dataset
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.filterable_objects import OPT_IN_ONLY
from cumulusci.salesforce_api.org_schema import Filters, get_org_schema
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask


class CaptureSampleData(BaseSalesforceApiTask):
    """Capture contextual sample data based on repo."""

    task_options = {
        "dataset": {
            "description": (
                "The name of the dataset. If none is provided, it will use 'default'. "
                "Names that match scratch org config names (such as 'dev', 'qa') will be loaded "
                "into those orgs by the CumulusCI default org setup flows."
            )
        },
        "extraction_definition": {
            "description": "A file describing what to be extracted. "
            "Defaults to `datasets/{datasetname}/{datasetname}.extract.yml` if it exists."
        },
        "loading_rules": {
            "description": (
                "Path to .load.yml file containing rules to use when loading the mapping. "
                "Defaults to`datasets/{datasetname}/{datasetname}.load.yml` if it exists. "
                "Multiple files can be comma separated."
            )
        },
    }

    org_config: OrgConfig

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options.setdefault("dataset", "default")

    def _run_task(self):
        name = self.options["dataset"]
        if extraction_definition := self.options.get("extraction_definition"):
            extraction_definition = Path(extraction_definition)
            if not extraction_definition.exists():
                raise TaskOptionsError(f"Cannot find {extraction_definition}")

        if loading_rules := self.options.get("loading_rules"):
            loading_rules = Path(loading_rules)
            if not loading_rules.exists():
                raise TaskOptionsError(f"Cannot find {loading_rules}")

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
            if not dataset.path.exists():
                dataset.create()
                verb = "Created"
            else:
                verb = "Updated"
            opt_in_only = [f["name"] for f in self.tooling.describe()["sobjects"]]  # type: ignore
            opt_in_only += OPT_IN_ONLY

            self.return_values = dataset.extract(
                {}, self.logger, extraction_definition, opt_in_only, loading_rules
            )
            self.logger.info(f"{verb} dataset '{name}' in 'datasets/{name}'")
            return self.return_values
