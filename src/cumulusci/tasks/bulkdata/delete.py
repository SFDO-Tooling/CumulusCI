from cumulusci.core.exceptions import BulkDataException, TaskOptionsError
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.tasks.bulkdata.step import (
    DataApi,
    DataOperationStatus,
    DataOperationType,
    get_dml_operation,
    get_query_operation,
)
from cumulusci.tasks.bulkdata.utils import RowErrorChecker
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class DeleteData(BaseSalesforceApiTask):
    """Query existing data for a specific sObject and perform a Bulk API delete of all matching records."""

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
            "description": "If True, perform a hard delete, bypassing the Recycle Bin. Note that this requires the Bulk API Hard Delete permission. Default: False"
        },
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
        self.options["hardDelete"] = process_bool_arg(
            self.options.get("hardDelete") or False
        )
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

        if self.options["hardDelete"] and self.options["api"] is DataApi.REST:
            raise TaskOptionsError("The hardDelete option requires Bulk API.")

    @staticmethod
    def _is_injectable(element: str) -> bool:
        return element.count("__") == 1

    def _validate_and_inject_namespace(self):
        """Perform namespace injection and ensure that we can successfully delete all of the selected objects."""

        global_describe = {
            entry["name"]: entry
            for entry in self.org_config.salesforce_client.describe()["sobjects"]
        }

        # Namespace injection
        if (
            self.options["inject_namespaces"]
            and self.project_config.project__package__namespace
        ):

            def inject(element: str):
                return f"{self.project_config.project__package__namespace}__{element}"

            self.sobjects = []
            for sobject in self.options["objects"]:
                if self._is_injectable(sobject):
                    injected = inject(sobject)
                    if sobject in global_describe and injected in global_describe:
                        self.logger.warning(
                            f"Both {sobject} and {injected} are present in the target org. Using {sobject}."
                        )

                    if sobject not in global_describe and injected in global_describe:
                        self.sobjects.append(injected)
                    else:
                        self.sobjects.append(sobject)
                else:
                    self.sobjects.append(sobject)
        else:
            self.sobjects = self.options["objects"]

        # Validate CRUD
        non_deletable_objects = [
            s
            for s in self.sobjects
            if not (s in global_describe and global_describe[s]["deletable"])
        ]
        if non_deletable_objects:
            raise BulkDataException(
                f"The objects {', '.join(non_deletable_objects)} are not present or cannot be deleted."
            )

    def _run_task(self):
        self._validate_and_inject_namespace()

        for obj in self.sobjects:
            query = f"SELECT Id FROM {obj}"
            if self.options["where"]:
                query += f" WHERE {self.options['where']}"

            qs = get_query_operation(
                sobject=obj,
                fields=["Id"],
                api_options={},
                context=self,
                query=query,
                api=self.options["api"],
            )

            self.logger.info(f"Querying for {obj} objects")
            qs.query()
            if qs.job_result.status is not DataOperationStatus.SUCCESS:
                raise BulkDataException(
                    f"Unable to query records for {obj}: {','.join(qs.job_result.job_errors)}"
                )
            if not qs.job_result.records_processed:
                self.logger.info(
                    f"No records found, skipping delete operation for {obj}"
                )
                continue

            self.logger.info(f"Deleting {self._object_description(obj)} ")
            ds = get_dml_operation(
                sobject=obj,
                operation=(
                    DataOperationType.HARD_DELETE
                    if self.options["hardDelete"]
                    else DataOperationType.DELETE
                ),
                fields=["Id"],
                api_options={},
                context=self,
                api=self.options["api"],
                volume=qs.job_result.records_processed,
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
