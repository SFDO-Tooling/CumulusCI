from cumulusci.core.datasets import Dataset
from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.mapping_parser import (
    parse_from_yaml,
    validate_and_inject_mapping,
)
from cumulusci.tasks.bulkdata.step import DataOperationType
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class LoadDataSetCheck(BaseSalesforceApiTask):
    task_docs = """
        A preflight check to ensure a dataset can be loaded successfully
    """
    task_options = {
        "dataset": {
            "description": "Dataset on which preflight checks need to be performed",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super(BaseSalesforceApiTask, self)._init_options(kwargs)
        if "dataset" not in self.options:
            self.options["dataset"] = "default"

    def _run_task(self):
        mapping_file_path = Dataset(
            self.options["dataset"],
            self.project_config,
            self.sf,
            self.org_config,
            schema=None,
        ).mapping_file
        self.mapping = parse_from_yaml(mapping_file_path)
        try:
            validate_and_inject_mapping(
                mapping=self.mapping,
                sf=self.sf,
                namespace=self.project_config.project__package__namespace,
                data_operation=DataOperationType.INSERT,
                inject_namespaces=True,
                drop_missing=False,
            )
            self.return_values = True
        except BulkDataException as e:
            self.logger.error(e)
            self.return_values = False
        return self.return_values
