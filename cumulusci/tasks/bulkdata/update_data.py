import csv
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from snowfakery import generate_data

from cumulusci.core.exceptions import BulkDataException, TaskOptionsError
from cumulusci.core.utils import (
    process_bool_arg,
    process_list_arg,
    process_list_of_pairs_dict_arg,
)
from cumulusci.tasks.bulkdata.step import (
    DataApi,
    DataOperationStatus,
    DataOperationType,
    get_dml_operation,
    get_query_operation,
)
from cumulusci.tasks.bulkdata.utils import RowErrorChecker
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class UpdateData(BaseSalesforceApiTask):
    """Update records of an sObject matching a where-clause."""

    task_options = {
        "object": {
            "description": "An SObject",
            "required": True,
        },
        "where": {
            "description": "A SOQL where-clause (without the keyword WHERE).",
            "required": False,
        },
        "api": {
            "description": "The desired Salesforce API to use, which may be 'rest', 'bulk', or "
            "'smart' to auto-select based on record volume. The default is 'smart'.",
            "required": False,
        },
        "fields": {
            "description": "Fields to download as input to the Snowfakery recipe",
            "required": False,
        },
        "recipe": {
            "description": "Snowfakery recipe to be executed on each row",
            "required": True,
        },
        "recipe_options": {
            "required": False,
            "description": """Pass values to override options in the format VAR1:foo,VAR2:bar

            Example: --recipe_options weight:10,color:purple""",
        },
        "ignore_row_errors": {
            "description": "If True, allow the operation to continue even if individual rows fail to delete."
        },
    }
    row_warning_limit = 10

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.sobject = self.options["object"]

        def identifier(f):
            return isinstance(f, str) and f.isidentifier()

        if not identifier(self.sobject):
            raise TaskOptionsError(
                f"`object` option should be an sObject name, not {self.sobject}"
            )

        self.where = self.options.get("where")
        self.fields = process_list_arg(self.options.get("fields", []))
        bad_fields = [f for f in self.fields if not identifier(f)]
        if bad_fields:
            plural = "s" if len(bad_fields) > 1 else ""
            verb = "are" if len(bad_fields) > 1 else "is"
            article = "an " if len(bad_fields) == 1 else ""
            raise TaskOptionsError(
                f"Field{plural} `{'`,`'.join(bad_fields)}` {verb} not {article}identifier{plural}"
            )

        self.inject_namespaces = process_bool_arg(
            self.task_options.get("inject_namespaces", True)
        )
        self.recipe = self.options.get("recipe")
        self.recipe_options = process_list_of_pairs_dict_arg(
            self.options.get("recipe_options", {})
        )
        self.ignore_row_errors = process_bool_arg(
            self.options.get("ignore_row_errors", False)
        )

        try:
            self.api = {
                "bulk": DataApi.BULK,
                "rest": DataApi.REST,
                "smart": DataApi.SMART,
            }[self.options.get("api", "smart").lower()]
        except KeyError:
            raise TaskOptionsError(
                f"{self.options['api']} is not a valid value for API (valid: bulk, rest, smart)"
            )

    def _run_task(self):
        obj = self._validate_and_inject_namespace_prefixes(
            should_inject_namespaces=self.inject_namespaces,
            sobjects_to_validate=[self.sobject],
            operation_to_validate="updateable",
        )[0]
        fields = ["Id"] + self.fields
        qs = self.query_objects(obj, fields)
        if not qs:
            self.logger.info(f"No records found, skipping update operation for {obj}")
            return
        with self.save_records(qs, fields) as csvfile, TemporaryDirectory() as outdir:
            csv_out = self.generate_data(csvfile, Path(outdir))
            with csv_out.open() as csv_out:
                enriched_data = csv.DictReader(csv_out)
                oid_index = enriched_data.fieldnames.index("Oid")
                enriched_data.fieldnames[oid_index] = "Id"
                self.load_data(qs.job_result.records_processed, enriched_data)

        self.logger.info(f"Updated {self._object_description(obj)}")

    def generate_data(self, csvfile: Path, outdir: Path) -> Path:
        generate_data(
            yaml_file=self.recipe,
            user_options=self.recipe_options,
            update_input_file=csvfile,
            update_passthrough_fields=["Oid"],
            plugin_options={
                "org_config": self.org_config,
                "project_config": self.project_config,
            },
            output_folder=outdir,
            output_format="csv",
        )
        created_csv = tuple(outdir.glob("*.csv"))
        assert len(created_csv) == 1, "CSV was not created by Snowfakery"
        return created_csv[0]

    @contextmanager
    def save_records(self, qs, fields):  # -> Path
        with TemporaryDirectory() as t:
            csvfile = Path(t) / "input.csv"
            with csvfile.open("w") as f:
                writer = csv.writer(f)
                snowfakery_fieldnames = ["Oid"] + fields[1:]
                writer.writerow(snowfakery_fieldnames)
                writer.writerows(qs.get_results())

            yield csvfile

    def query_objects(self, obj, fields):
        query = f"SELECT {','.join(fields)} FROM {obj}"
        if self.where:
            query += f" WHERE {self.options['where']}"

        qs = get_query_operation(
            sobject=obj,
            fields=fields,
            api_options={},
            context=self,
            query=query,
            api=DataApi.SMART,  # maybe this should always be bulk
        )

        self.logger.info(f"Querying for {obj} objects")
        qs.query()
        if qs.job_result.status is not DataOperationStatus.SUCCESS:
            raise BulkDataException(
                f"Unable to query records for {obj}: {','.join(qs.job_result.job_errors)}"
            )
        if not qs.job_result.records_processed:
            return None
        return qs

    def load_data(self, row_count: int, records: csv.DictReader):
        obj = self.sobject
        self.logger.info(f"Loading data {self._object_description(obj)} ")
        fieldnames = [
            f for f in records.fieldnames if f != "id" and not f.startswith("_")
        ]

        ds = get_dml_operation(
            sobject=obj,
            operation=DataOperationType.UPDATE,
            fields=fieldnames,
            api_options={},
            context=self,
            api=self.api,
            volume=row_count,
        )

        def cleanup(record):
            return tuple(record[fieldname] for fieldname in fieldnames)

        ds.start()
        ds.load_records(cleanup(record) for record in records)
        ds.end()

        if ds.job_result.status not in [
            DataOperationStatus.SUCCESS,
            DataOperationStatus.ROW_FAILURE,
        ]:
            raise BulkDataException(
                f"Unable to update records for {obj}: {','.join(ds.job_result.job_errors)}"
            )

        error_checker = RowErrorChecker(
            self.logger, self.ignore_row_errors, self.row_warning_limit
        )
        for result in ds.get_results():
            error_checker.check_for_row_error(result, result.id)
        return ds

    def _object_description(self, obj):
        """Return a readable description of the object set to update."""
        if self.where:
            return f'{obj} objects matching "{self.options["where"]}"'
        else:
            return f"all {obj} objects"
