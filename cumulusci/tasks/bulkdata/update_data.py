from csv import DictReader
from pathlib import Path

from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.bulkdata.step import (
    DataOperationType,
    DataOperationStatus,
    DataApi,
    get_dml_operation,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import TaskOptionsError, BulkDataException
from cumulusci.tasks.bulkdata.utils import RowErrorChecker


class UpdateData(BaseSalesforceApiTask):
    """Update one or more columns based on CSV records"""

    task_options = {
        "object": {"description": "What SObject's records should be updated"},
        "csv": {"description": "The path to a CSV file to read.", "required": True},
        "ignore_row_errors": {
            "description": "If True, allow the operation to continue even if individual rows fail to delete."
        },
        "inject_namespaces": {
            "description": "If True, the package namespace prefix will be "
            "automatically added to (or removed from) objects "
            "and fields based on the name used in the org. Defaults to True."
        },
        "api": {
            "description": "The desired Salesforce API to use, which may be 'rest', 'bulk', or "
            "'smart' to auto-select based on record volume. The default is 'smart'."
        },
    }
    row_warning_limit = 10

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.object = self.options["object"]

        self.options["ignore_row_errors"] = process_bool_arg(
            self.options.get("ignore_row_errors") or False
        )
        inject_namespaces = self.options.get("inject_namespaces")
        self.options["inject_namespaces"] = process_bool_arg(
            True if inject_namespaces is None else inject_namespaces
        )
        try:
            self.options["api"] = {
                "bulk": DataApi.BULK,
                "rest": DataApi.REST,
                "smart": DataApi.SMART,
            }[self.options.get("api", "smart").lower()]
        except KeyError:
            raise TaskOptionsError(
                f"{self.options['api']} is not a valid value for API (valid: bulk, rest, smart)"
            )

    def _validate_and_inject_namespace(self):
        """Perform namespace injection and ensure that we can successfully delete all of the selected objects."""
        ...  # TODO

    def _run_task(self):
        self._validate_and_inject_namespace()

        input_file = Path(self.options["csv"])

        line_count = count_lines(input_file)

        with input_file.open() as input_data:
            reader = DictReader(input_data)
            values = (row.values() for row in reader)
            ds = get_dml_operation(
                sobject=self.object,
                operation=(DataOperationType.UPDATE),
                fields=reader.fieldnames,
                api_options={},
                context=self,
                api=self.options["api"],
                volume=line_count,
            )
            ds.start()
            ds.load_records(values)
            ds.end()

            if ds.job_result.status not in [
                DataOperationStatus.SUCCESS,
                DataOperationStatus.ROW_FAILURE,
            ]:
                raise BulkDataException(
                    f"Unable to update records for {self.object}: {','.join(ds.job_result.job_errors)}"
                )

            error_checker = RowErrorChecker(
                self.logger, self.options["ignore_row_errors"], self.row_warning_limit
            )
            for result in ds.get_results():
                error_checker.check_for_row_error(result, result.id)


def count_lines(filename):
    with open(filename) as f:
        for n, _ in enumerate(f):
            ...
        return n
