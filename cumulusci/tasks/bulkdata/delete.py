from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.tasks.bulkdata.step import (
    BulkApiDmlOperation,
    BulkApiQueryOperation,
    DataOperationType,
    DataOperationStatus,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import TaskOptionsError, BulkDataException


class DeleteData(BaseSalesforceApiTask):
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
            qs = BulkApiQueryOperation(obj, {}, self, query)
            qs.query()
            if qs.status is not DataOperationStatus.SUCCESS:
                raise BulkDataException(f"Unable to query records for {obj}")

            self.logger.info(f"Deleting {self._object_description(obj)} ")
            ds = BulkApiDmlOperation(
                obj,
                DataOperationType.HARD_DELETE
                if self.options["hardDelete"]
                else DataOperationType.DELETE,
                {},
                self,
                ["Id"],
            )
            ds.start()
            ds.load_records(map(lambda result: [result[0]], qs.get_results()))
            ds.end()

            for result in ds.get_results():
                if not result.success and not self.options["ignore_row_errors"]:
                    raise BulkDataException(f"Failed to delete record {result.id}")

    def _object_description(self, obj):
        if self.options["where"]:
            return f'{obj} objects matching "{self.options["where"]}"'
        else:
            return f"all {obj} objects"
