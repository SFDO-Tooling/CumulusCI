from cumulusci.core.datasets import Dataset
from cumulusci.salesforce_api.org_schema import Filters, get_org_schema
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


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
            "description": "A file describing what to be extracted."
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options.setdefault("dataset", "default")

    def _run_task(self):
        name = self.options["dataset"]
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
            dataset.extract()
            self.logger.info(f"{verb} dataset '{name}' in 'datasets/{name}'")
