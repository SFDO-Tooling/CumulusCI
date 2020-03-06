from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.tasks.bulkdata.step import (
    BulkApiDmlOperation,
    BulkApiQueryOperation,
    DataOperationType,
    DataOperationStatus,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import TaskOptionsError, BulkDataException
from cumulusci.tasks.bulkdata.utils import RowErrorChecker


class DeleteData(BaseSalesforceApiTask):
    """Query existing data for a specific sObject and perform a Bulk API delete of all responsive records."""

    task_options = {
        "objects": {
            "description": "A list of objects to delete records from in order of deletion.  If passed via command line, use a comma separated string",
            "required": True,
        },
        "where": {
            "description": "A SOQL where-clause (without the keyword WHERE). Only available when 'objects' is length 1.",
            "required": False,
        },
        "hardDelete": {
            "description": "If True, perform a hard delete, bypassing the Recycle Bin. Default: False"
        },
        "ignore_row_errors": {
            "description": "If True, allow the operation to continue even if individual rows fail to delete."
        },
    }
    row_warning_limit = 10

    def _init_options(self, kwargs):
        super(DeleteData, self)._init_options(kwargs)

        # Split and trim objects string into a list if not already a list
        self.options["objects"] = process_list_arg(self.options["objects"])
        if not len(self.options["objects"]) or not self.options["objects"][0]:
            raise TaskOptionsError("At least one object must be specified.")

        self.options["where"] = self.options.get("where", None)
        if len(self.options["objects"]) > 1 and self.options["where"]:
            raise TaskOptionsError(
                "Criteria cannot be specified if more than one object is specified."
            )
        self.options["hardDelete"] = process_bool_arg(self.options.get("hardDelete"))
        self.options["ignore_row_errors"] = process_bool_arg(
            self.options.get("ignore_row_errors")
        )

    def _run_task(self):
        for obj in self.options["objects"]:
            query = f"SELECT Id FROM {obj}"
            if self.options["where"]:
                query += f" WHERE {self.options['where']}"

            self.logger.info(f"Querying for {obj} objects")
            qs = BulkApiQueryOperation(
                sobject=obj, api_options={}, context=self, query=query
            )
            qs.query()
            if qs.job_result.status is not DataOperationStatus.SUCCESS:
                raise BulkDataException(
                    f"Unable to query records for {obj}: {','.join(qs.job_result.job_errors)}"
                )

            if not qs.job_result.records_processed:
                self.logger.info("No records found, skipping delete operation")
                continue

            self.logger.info(f"Deleting {self._object_description(obj)} ")
            ds = BulkApiDmlOperation(
                sobject=obj,
                operation=(
                    DataOperationType.HARD_DELETE
                    if self.options["hardDelete"]
                    else DataOperationType.DELETE
                ),
                api_options={},
                context=self,
                fields=["Id"],
            )
            ds.start()
            ds.load_records(qs.get_results())
            ds.end()

            if ds.job_result.status not in [
                DataOperationStatus.SUCCESS,
                DataOperationStatus.ROW_FAILURE,
            ]:
                raise BulkDataException(
                    f"Unable to delete records for {obj}: {','.join(qs.job_result.job_errors)}"
                )

            error_checker = RowErrorChecker(
                self.logger, self.options["ignore_row_errors"], self.row_warning_limit
            )
            for result in ds.get_results():
                error_checker.check_for_row_error(result, result.id)

    def _object_description(self, obj):
        """Return a readable description of the object set to delete."""
        if self.options["where"]:
            return f'{obj} objects matching "{self.options["where"]}"'
        else:
            return f"all {obj} objects"
