import tempfile
import typing as T
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

from sqlalchemy import Column, MetaData, Table, Unicode, create_engine, func, inspect
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

from cumulusci.core.enums import StrEnum
from cumulusci.core.exceptions import BulkDataException, TaskOptionsError
from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.org_schema import get_org_schema
from cumulusci.tasks.bulkdata.dates import adjust_relative_dates
from cumulusci.tasks.bulkdata.mapping_parser import (
    CaseInsensitiveDict,
    MappingLookup,
    MappingStep,
    parse_from_yaml,
    validate_and_inject_mapping,
)
from cumulusci.tasks.bulkdata.query_transformers import (
    ID_TABLE_NAME,
    AddLookupsToQuery,
    AddMappingFiltersToQuery,
    AddPersonAccountsToQuery,
    AddRecordTypesToQuery,
    DynamicLookupQueryExtender,
)
from cumulusci.tasks.bulkdata.step import (
    DEFAULT_BULK_BATCH_SIZE,
    DataApi,
    DataOperationJobResult,
    DataOperationStatus,
    DataOperationType,
    RestApiDmlOperation,
    get_dml_operation,
)
from cumulusci.tasks.bulkdata.upsert_utils import (
    AddUpsertsToQuery,
    extract_upsert_key_data,
    needs_etl_upsert,
)
from cumulusci.tasks.bulkdata.utils import (
    RowErrorChecker,
    SqlAlchemyMixin,
    sql_bulk_insert_from_records,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class LoadData(SqlAlchemyMixin, BaseSalesforceApiTask):
    """Perform Bulk API operations to load data defined by a mapping from a local store into an org."""

    task_options = {
        "database_url": {
            "description": "The database url to a database containing the test data to load"
        },
        "mapping": {
            "description": "The path to a yaml file containing mappings of the database fields to Salesforce object fields",
            "required": True,
        },
        "start_step": {
            "description": "If specified, skip steps before this one in the mapping",
            "required": False,
        },
        "sql_path": {
            "description": "If specified, a database will be created from an SQL script at the provided path"
        },
        "ignore_row_errors": {
            "description": "If True, allow the load to continue even if individual rows fail to load."
        },
        "reset_oids": {
            "description": "If True (the default), and the _sf_ids tables exist, reset them before continuing.",
            "required": False,
        },
        "bulk_mode": {
            "description": "Set to Serial to force serial mode on all jobs. Parallel is the default."
        },
        "inject_namespaces": {
            "description": "If True, the package namespace prefix will be "
            "automatically added to (or removed from) objects "
            "and fields based on the name used in the org. Defaults to True."
        },
        "drop_missing_schema": {
            "description": "Set to True to skip any missing objects or fields instead of stopping with an error."
        },
        "set_recently_viewed": {
            "description": "By default, the first 1000 records inserted via the Bulk API will be set as recently viewed. If fewer than 1000 records are inserted, existing objects of the same type being inserted will also be set as recently viewed.",
        },
        "org_shape_match_only": {
            "description": "When True, all path options are ignored and only a dataset matching the org shape name will be loaded. Defaults to False."
        },
        "enable_rollback": {
            "description": "When True, performs rollback operation incase of error. Defaults to False"
        },
    }
    row_warning_limit = 10

    def _init_options(self, kwargs):
        super(LoadData, self)._init_options(kwargs)

        self.options["ignore_row_errors"] = process_bool_arg(
            self.options.get("ignore_row_errors") or False
        )
        self._init_dataset()
        self.reset_oids = self.options.get("reset_oids", True)
        self.bulk_mode = (
            self.options.get("bulk_mode") and self.options.get("bulk_mode").title()
        )
        if self.bulk_mode and self.bulk_mode not in ["Serial", "Parallel"]:
            raise TaskOptionsError("bulk_mode must be either Serial or Parallel")

        inject_namespaces = self.options.get("inject_namespaces")
        self.options["inject_namespaces"] = process_bool_arg(
            True if inject_namespaces is None else inject_namespaces
        )
        self.options["drop_missing_schema"] = process_bool_arg(
            self.options.get("drop_missing_schema") or False
        )
        self.options["set_recently_viewed"] = process_bool_arg(
            self.options.get("set_recently_viewed", True)
        )
        self.options["enable_rollback"] = process_bool_arg(
            self.options.get("enable_rollback", False)
        )
        self._id_generators = {}
        self._old_format = False
        self.ID_TABLE_NAME = ID_TABLE_NAME

    def _init_dataset(self):
        """Find the dataset paths to use with the following sequence:
        1. If `org_shape_match_only` is True (defaults False),
           unset any other path options that may have been supplied.
        2. Prefer a supplied `database_url`.
        3. If `sql_path` was supplied, but not `mapping`, use default `mapping` value.
        4. If `mapping` was supplied, but not `sql_path`, use default `sql_path` value.
        5. If no path options were supplied, look for a dataset matching the org shape.
        6. If no matching dataset was found AND `org_shape_match_only` is False,
           look for a dataset with the default `mapping` and `sql_path` values
           (as previously defaulted in the standard library yml).
        """
        self.options["org_shape_match_only"] = process_bool_arg(
            self.options.get("org_shape_match_only", False)
        )
        if self.options["org_shape_match_only"]:
            self.options["mapping"] = None
            self.options["sql_path"] = None
            self.options["database_url"] = None
            self.logger.warning(
                "The `default_dataset_only` option has been deprecated. "
                "Please switch to the `load_sample_data` task."
            )

        self.options.setdefault("database_url", None)
        if self.options.get("database_url"):
            # prefer database_url if it's set
            self.options["sql_path"] = None
        elif self.options.get("sql_path"):
            self.options.setdefault("mapping", "datasets/mapping.yml")
        elif self.options.get("mapping"):
            self.options.setdefault("sql_path", "datasets/sample.sql")
        elif found_dataset := (
            self._find_matching_dataset() or self._find_default_dataset()
        ):  # didn't get either database_url or sql_path
            mapping_path, dataset_path = found_dataset
            self.options["mapping"] = mapping_path
            self.options["sql_path"] = dataset_path
        else:
            self.has_dataset = False
            return
        self.has_dataset = True

    def _find_matching_dataset(self) -> T.Optional[T.Tuple[str, str]]:
        org_shape = self.org_config.lookup("config_name") if self.org_config else None
        if not org_shape:
            return None  # persistent org
        dataset_folder = f"datasets/{org_shape}"
        if Path(dataset_folder).exists():
            # check for dataset.sql and mapping.yml
            mapping_path = f"{dataset_folder}/{org_shape}.mapping.yml"
            dataset_path = f"{dataset_folder}/{org_shape}.dataset.sql"
            if Path(mapping_path).exists() and Path(dataset_path).exists():
                return (mapping_path, dataset_path)
            else:
                self.logger.warning(
                    f"Found datasets/{org_shape} but it did not contain {org_shape}.mapping.yml and {org_shape}.dataset.yml."
                )
        return None

    def _find_default_dataset(self) -> T.Optional[T.Tuple[str, str]]:
        if self.options["org_shape_match_only"]:
            return None
        dataset_path = "datasets/sample.sql"
        mapping_path = "datasets/mapping.yml"
        if Path(dataset_path).exists() and Path(mapping_path).exists():
            return (mapping_path, dataset_path)
        return None

    def _run_task(self):
        if not self.has_dataset:
            if org_shape := self.org_config.lookup("config_name"):
                self.logger.info(
                    f"No data will be loaded because there was no dataset found matching your org shape name ('{org_shape}')."
                )
            else:
                self.logger.info(
                    "No data will be loaded because this is a persistent org and no dataset was specified."
                )
            return
        self._init_mapping()
        with self._init_db():
            self._expand_mapping()
            self._initialize_id_table(self.reset_oids)
            start_step = self.options.get("start_step")
            started = False
            results = {}
            for name, mapping in self.mapping.items():
                # Skip steps until start_step
                if not started and start_step and name != start_step:
                    self.logger.info(f"Skipping step: {name}")
                    continue

                started = True

                self.logger.info(f"Running step: {name}")
                result = self._execute_step(mapping)
                if result.status is DataOperationStatus.JOB_FAILURE:
                    raise BulkDataException(
                        f"Step {name} did not complete successfully: {','.join(result.job_errors)}"
                    )

                if name in self.after_steps:
                    for after_name, after_step in self.after_steps[name].items():
                        self.logger.info(f"Running post-load step: {after_name}")
                        result = self._execute_step(after_step)
                        if result.status is DataOperationStatus.JOB_FAILURE:
                            raise BulkDataException(
                                f"Step {after_name} did not complete successfully: {','.join(result.job_errors)}"
                            )
                results[name] = StepResultInfo(
                    mapping.sf_object, result, mapping.record_type
                )
        if self.options["set_recently_viewed"]:
            try:
                self.logger.info("Setting records to 'recently viewed'.")
                set_recently_viewed = self._set_viewed()
            except Exception as e:
                self.logger.warning(f"Could not set recently viewed because {e}")
                set_recently_viewed = [SetRecentlyViewedInfo("ALL", e)]
        else:
            set_recently_viewed = False

        self.return_values = {
            "step_results": {
                step_name: result_info.simplify()
                for step_name, result_info in results.items()
            },
        }
        if set_recently_viewed is not False:
            self.return_values["set_recently_viewed"] = set_recently_viewed

    def _execute_step(
        self, mapping: MappingStep
    ) -> T.Union[DataOperationJobResult, MagicMock]:
        """Load data for a single step."""

        if "RecordTypeId" in mapping.fields:
            conn = self.session.connection()
            self._load_record_types([mapping.sf_object], conn)
            self.session.commit()

        step, query = self.configure_step(mapping)

        with tempfile.TemporaryFile(mode="w+t") as local_ids:
            # Store the previous values of the records before upsert
            # This is so that we can perform rollback
            if (
                mapping.action
                in [
                    DataOperationType.ETL_UPSERT,
                    DataOperationType.UPSERT,
                    DataOperationType.UPDATE,
                ]
                and self.options["enable_rollback"]
            ):
                UpdateRollback.prepare_for_rollback(
                    self, step, self._stream_queried_data(mapping, local_ids, query)
                )
            step.start()
            if mapping.action == DataOperationType.SELECT:
                step.select_records(
                    self._stream_queried_data(mapping, local_ids, query)
                )
            else:
                step.load_records(self._stream_queried_data(mapping, local_ids, query))
            step.end()

            # Process Job Results
            if step.job_result.status is not DataOperationStatus.JOB_FAILURE:
                local_ids.seek(0)
                self._process_job_results(mapping, step, local_ids)
            elif (
                step.job_result.status is DataOperationStatus.JOB_FAILURE
                and self.options["enable_rollback"]
            ):
                Rollback._perform_rollback(self)

            return step.job_result

    def process_lookup_fields(self, mapping, fields, polymorphic_fields):
        """Modify fields and priority fields based on lookup and polymorphic checks."""
        # Store the lookups and their original order for re-insertion at the end
        original_lookups = [name for name in fields if name in mapping.lookups]
        max_insert_index = -1
        for name, lookup in mapping.lookups.items():
            if name in fields:
                # Get the index of the lookup field before removing it
                insert_index = fields.index(name)
                max_insert_index = max(max_insert_index, insert_index)
                # Remove the lookup field from fields
                fields.remove(name)

                # Do the same for priority fields
                lookup_in_priority_fields = False
                if name in mapping.select_options.priority_fields:
                    # Set flag to True
                    lookup_in_priority_fields = True
                    # Remove the lookup field from priority fields
                    del mapping.select_options.priority_fields[name]

                # Check if this lookup field is polymorphic
                if (
                    name in polymorphic_fields
                    and len(polymorphic_fields[name]["referenceTo"]) > 1
                ):
                    # Convert to list if string
                    if not isinstance(lookup.table, list):
                        lookup.table = [lookup.table]
                    # Polymorphic field handling
                    polymorphic_references = lookup.table
                    relationship_name = polymorphic_fields[name]["relationshipName"]

                    # Loop through each polymorphic type (e.g., Contact, Lead)
                    for ref_type in polymorphic_references:
                        # Find the mapping step for this polymorphic type
                        lookup_mapping_step = next(
                            (
                                step
                                for step in self.mapping.values()
                                if step.table == ref_type
                            ),
                            None,
                        )
                        if lookup_mapping_step:
                            lookup_fields = lookup_mapping_step.fields.keys()
                            # Insert fields in the format {relationship_name}.{ref_type}.{lookup_field}
                            for field in lookup_fields:
                                fields.insert(
                                    insert_index,
                                    f"{relationship_name}.{lookup_mapping_step.sf_object}.{field}",
                                )
                                insert_index += 1
                                max_insert_index = max(max_insert_index, insert_index)
                                if lookup_in_priority_fields:
                                    mapping.select_options.priority_fields[
                                        f"{relationship_name}.{lookup_mapping_step.sf_object}.{field}"
                                    ] = f"{relationship_name}.{lookup_mapping_step.sf_object}.{field}"

                else:
                    # Non-polymorphic field handling
                    lookup_table = lookup.table

                    if isinstance(lookup_table, list):
                        lookup_table = lookup_table[0]

                    # Get the mapping step for the non-polymorphic reference
                    lookup_mapping_step = next(
                        (
                            step
                            for step in self.mapping.values()
                            if step.table == lookup_table
                        ),
                        None,
                    )

                    if lookup_mapping_step:
                        relationship_name = polymorphic_fields[name]["relationshipName"]
                        lookup_fields = lookup_mapping_step.fields.keys()

                        # Insert the new fields at the same position as the removed lookup field
                        for field in lookup_fields:
                            fields.insert(insert_index, f"{relationship_name}.{field}")
                            insert_index += 1
                            max_insert_index = max(max_insert_index, insert_index)
                            if lookup_in_priority_fields:
                                mapping.select_options.priority_fields[
                                    f"{relationship_name}.{field}"
                                ] = f"{relationship_name}.{field}"

        # Append the original lookups at the end in the same order
        for name in original_lookups:
            if name not in fields:
                fields.insert(max_insert_index, name)
                max_insert_index += 1

    def configure_step(self, mapping):
        """Create a step appropriate to the action"""
        bulk_mode = mapping.bulk_mode or self.bulk_mode or "Parallel"
        api_options = {"batch_size": mapping.batch_size, "bulk_mode": bulk_mode}
        num_records_in_target = None
        content_type = None

        fields = mapping.get_load_field_list()

        # implement "smart" upsert
        if mapping.action == DataOperationType.SMART_UPSERT:
            if needs_etl_upsert(mapping, self.sf):
                mapping.action = DataOperationType.ETL_UPSERT
            else:
                mapping.action = DataOperationType.UPSERT

        if mapping.action == DataOperationType.ETL_UPSERT:
            extract_upsert_key_data(
                mapping.sf_object,
                mapping.update_key,
                self,
                self.metadata,
                self.session.connection(),
            )

            # If we treat "Id" as an "external_id_name" then it's
            # allowed to be sparse.
            api_options["update_key"] = "Id"
            action = DataOperationType.UPSERT
            fields.append("Id")
        elif mapping.action == DataOperationType.UPSERT:
            self.check_simple_upsert(mapping)
            api_options["update_key"] = mapping.update_key[0]
            action = DataOperationType.UPSERT
        elif mapping.action == DataOperationType.SELECT:
            # Set content type to json
            content_type = "JSON"
            # Bulk process expects DataOpertionType to be QUERY
            action = DataOperationType.QUERY
            # Determine number of records in the target org
            record_count_response = self.sf.restful(
                f"limits/recordCount?sObjects={mapping.sf_object}"
            )
            sobject_map = {
                entry["name"]: entry["count"]
                for entry in record_count_response["sObjects"]
            }
            num_records_in_target = sobject_map.get(mapping.sf_object, None)

            # Check for similarity selection strategy and modify fields accordingly
            if mapping.select_options.strategy == "similarity":
                # Describe the object to determine polymorphic lookups
                describe_result = self.sf.restful(
                    f"sobjects/{mapping.sf_object}/describe"
                )
                polymorphic_fields = {
                    field["name"]: field
                    for field in describe_result["fields"]
                    if field["type"] == "reference"
                }
                self.process_lookup_fields(mapping, fields, polymorphic_fields)
        else:
            action = mapping.action

        query = self._query_db(mapping)

        # Set volume
        volume = (
            num_records_in_target
            if num_records_in_target is not None
            else query.count()
        )

        step = get_dml_operation(
            sobject=mapping.sf_object,
            operation=action,
            api_options=api_options,
            context=self,
            fields=fields,
            api=mapping.api,
            volume=volume,
            selection_strategy=mapping.select_options.strategy,
            selection_filter=mapping.select_options.filter,
            selection_priority_fields=mapping.select_options.priority_fields,
            content_type=content_type,
            threshold=mapping.select_options.threshold,
        )
        return step, query

    def check_simple_upsert(self, mapping):
        """Check that this upsert is correct."""
        if needs_etl_upsert(mapping, self.sf):
            raise BulkDataException(
                f"This update key is not compatible with a simple upsert: `{','.join(mapping.update_key)}`. "
                "Use `action: ETL_UPSERT` instead."
            )

    def _stream_queried_data(self, mapping, local_ids, query):
        """Get data from the local db"""

        statics = self._get_statics(mapping)
        total_rows = 0

        if mapping.anchor_date:
            date_context = mapping.get_relative_date_context(
                mapping.get_load_field_list(), self.sf
            )
        # Clamping the yield from the query ensures we do not
        # create more Bulk API batches than expected, regardless
        # of batch size, while capping memory usage.
        batch_size = mapping.batch_size or DEFAULT_BULK_BATCH_SIZE
        for row in query.yield_per(batch_size):
            total_rows += 1
            pkey = row[0]
            row = list(row[1:]) + statics

            if mapping.anchor_date and (date_context[0] or date_context[1]):
                row = adjust_relative_dates(
                    mapping, date_context, row, DataOperationType.INSERT
                )

            if mapping.action is DataOperationType.UPDATE:
                if len(row) > 1 and all([f is None for f in row[1:]]):
                    # Skip update rows that contain no values
                    total_rows -= 1
                    continue

            local_ids.write(str(pkey) + "\n")
            yield row

        self.logger.info(
            f"Prepared {total_rows} rows for {mapping.action.value} to {mapping.sf_object}."
        )

    def _load_record_types(self, sobjects, conn):
        """Persist record types for the given sObjects into the database."""
        for sobject in sobjects:
            table_name = sobject + "_rt_target_mapping"
            self._extract_record_types(
                sobject, table_name, conn, self.org_config.is_person_accounts_enabled
            )

    def _get_statics(self, mapping):
        """Return the static values (not column names) to be appended to
        records for this mapping."""
        statics = list(mapping.static.values())
        if mapping.record_type:
            query = (
                f"SELECT Id FROM RecordType WHERE SObjectType='{mapping.sf_object}'"
                f"AND DeveloperName = '{mapping.record_type}' LIMIT 1"
            )
            records = self.sf.query(query)["records"]
            if records:
                record_type_id = records[0]["Id"]
            else:
                raise BulkDataException(f"Cannot find RecordType with query `{query}`")
            statics.append(record_type_id)

        return statics

    def _query_db(self, mapping):
        """Build a query to retrieve data from the local db.

        Includes columns from the mapping
        as well as joining to the id tables to get real SF ids
        for lookups.
        """
        model = self.models[mapping.table]

        id_column = model.__table__.primary_key.columns.keys()[0]
        columns = [getattr(model, id_column)]

        table_cases = CaseInsensitiveDict(model.__table__.columns)
        for name, f in mapping.fields.items():
            if name not in ("Id", "RecordTypeId", "RecordType"):
                column = table_cases.get(f)
                columns.append(column)

        query = self.session.query(*columns)

        classes = [
            AddRecordTypesToQuery,
            AddMappingFiltersToQuery,
            AddUpsertsToQuery,
        ]
        transformers = []
        if (
            mapping.action == DataOperationType.SELECT
            and mapping.select_options.strategy == "similarity"
        ):
            transformers.append(
                DynamicLookupQueryExtender(
                    mapping, self.mapping, self.metadata, model, self._old_format
                )
            )
        transformers.append(
            AddLookupsToQuery(mapping, self.metadata, model, self._old_format)
        )

        transformers.extend([cls(mapping, self.metadata, model) for cls in classes])

        if mapping.sf_object == "Contact" and self._can_load_person_accounts(mapping):
            transformers.append(AddPersonAccountsToQuery(mapping, self.metadata, model))

        for transformer in transformers:
            query = transformer.add_columns(query)

        for transformer in transformers:
            query = transformer.add_filters(query)

        for transformer in transformers:
            query = transformer.add_outerjoins(query)

        query = self._sort_by_lookups(query, mapping, model)
        return query

    def _sort_by_lookups(self, query, mapping, model):
        lookups = [lookup for lookup in mapping.lookups.values() if not lookup.after]
        for lookup in lookups:
            key_field = lookup.get_lookup_key_field(model)
            lookup_column = getattr(model, key_field)
            query = query.order_by(lookup_column)

        return query

    def _process_job_results(self, mapping, step, local_ids):
        """Get the job results and process the results. If we're raising for
        row-level errors, do so; if we're inserting, store the new Ids."""

        is_insert_upsert_or_select = mapping.action in (
            DataOperationType.INSERT,
            DataOperationType.UPSERT,
            DataOperationType.ETL_UPSERT,
            DataOperationType.SELECT,
        )

        conn = self.session.connection()
        sf_id_results = self._generate_results_id_map(step, local_ids)

        for i in range(len(sf_id_results)):
            # Check for old_format of load sql files
            if str(sf_id_results[i][0]).isnumeric():
                self._old_format = True
                # Set id column with new naming format (<sobject> - <counter>)
                sf_id_results[i][0] = mapping.table + "-" + str(sf_id_results[i][0])
            else:
                break
        # If we know we have no successful inserts, don't attempt to persist Ids.
        # Do, however, drain the generator to get error-checking behavior.
        if is_insert_upsert_or_select and (
            step.job_result.records_processed - step.job_result.total_row_errors
        ):
            table = self.metadata.tables[self.ID_TABLE_NAME]
            sql_bulk_insert_from_records(
                connection=conn,
                table=table,
                columns=("id", "sf_id"),
                record_iterable=sf_id_results,
            )

        # Contact records for Person Accounts are inserted during an Account
        # sf_object step.  Insert records into the Contact ID table for
        # person account Contact records so lookups to
        # person account Contact records get populated downstream as expected.
        if (
            is_insert_upsert_or_select
            and mapping.sf_object == "Contact"
            and self._can_load_person_accounts(mapping)
        ):
            account_id_lookup = mapping.lookups.get("AccountId")
            if account_id_lookup:
                sql_bulk_insert_from_records(
                    connection=conn,
                    table=self.metadata.tables[self.ID_TABLE_NAME],
                    columns=("id", "sf_id"),
                    record_iterable=self._generate_contact_id_map_for_person_accounts(
                        mapping, account_id_lookup, conn
                    ),
                )

        if is_insert_upsert_or_select:
            self.session.commit()

    def _generate_results_id_map(self, step, local_ids):
        """Consume results from load and prepare rows for id table.
        Raise BulkDataException on row errors if configured to do so.
        Adds created records into insert_rollback Table
        Performs rollback in case of any errors if enable_rollback is True"""
        error_checker = RowErrorChecker(
            self.logger, self.options["ignore_row_errors"], self.row_warning_limit
        )
        local_ids = (lid.strip("\n") for lid in local_ids)
        sf_id_results = []
        created_results = []
        failed_results = []
        for result, local_id in zip(step.get_results(), local_ids):
            if result.success:
                sf_id_results.append([local_id, result.id])
                if result.created:
                    created_results.append([result.id])
            else:
                failed_results.append([result, local_id])

        # We record failed_results separately since if a unsuccesful record
        # was in between, it would not store all the successful ids
        for result, local_id in failed_results:
            try:
                error_checker.check_for_row_error(result, local_id)
            except Exception as e:
                if self.options["enable_rollback"]:
                    CreateRollback.prepare_for_rollback(self, step, created_results)
                    Rollback._perform_rollback(self)
                raise e
        if self.options["enable_rollback"]:
            CreateRollback.prepare_for_rollback(self, step, created_results)
        return sf_id_results

    def _initialize_id_table(self, should_reset_table):
        """initalize or find table to hold the inserted SF Ids

        The table has a name like xxx_sf_ids and has just two columns, id and sf_id.

        If the table already exists, should_reset_table determines whether to
        drop and recreate it or not.
        """

        already_exists = self.ID_TABLE_NAME in self.metadata.tables

        if already_exists and not should_reset_table:
            return
        elif already_exists:
            self.metadata.remove(self.metadata.tables[self.ID_TABLE_NAME])
        id_table = Table(
            self.ID_TABLE_NAME,
            self.metadata,
            Column("id", Unicode(255), primary_key=True),
            Column("sf_id", Unicode(18)),
        )
        if id_table.exists():
            id_table.drop()
        id_table.create()

    def _sqlite_load(self):
        """Read a SQLite script and initialize the in-memory database."""
        conn = self.session.connection()
        cursor = conn.connection.cursor()
        with open(self.options["sql_path"], "r", encoding="utf-8") as f:
            try:
                cursor.executescript(f.read())
            finally:
                cursor.close()
        # self.session.flush()

    @contextmanager
    def _init_db(self):
        """Initialize the database and automapper."""
        # initialize the DB engine
        with self._database_url() as database_url:
            parent_engine = create_engine(database_url)
            with parent_engine.connect() as connection:
                # initialize the DB session
                self.session = Session(connection)

                if self.options.get("sql_path"):
                    self._sqlite_load()

                # initialize DB metadata
                self.metadata = MetaData()
                self.metadata.bind = connection
                self.inspector = inspect(parent_engine)

                # empty the record of initalized tables
                Rollback._initialized_rollback_tables_api = {}

                # initialize the automap mapping
                self.base = automap_base(bind=connection, metadata=self.metadata)
                self.base.prepare(connection, reflect=True)

                # Loop through mappings and reflect each referenced table
                self.models = {}
                for name, mapping in self.mapping.items():
                    if mapping.table not in self.models:
                        try:
                            self.models[mapping.table] = self.base.classes[
                                mapping.table
                            ]
                        except KeyError as e:
                            raise BulkDataException(f"Table not found in dataset: {e}")

                    # create any Record Type tables we need
                    if "RecordTypeId" in mapping.fields:
                        self._create_record_type_table(
                            mapping.get_destination_record_type_table()
                        )
                self.metadata.create_all()

                self._validate_org_has_person_accounts_enabled_if_person_account_data_exists()
                yield

    def _init_mapping(self):
        """Load a YAML mapping file."""
        mapping_file_path = self.options.get("mapping")
        if not mapping_file_path:
            raise TaskOptionsError("Mapping file path required")

        self.mapping = parse_from_yaml(mapping_file_path)

        validate_and_inject_mapping(
            mapping=self.mapping,
            sf=self.sf,
            namespace=self.project_config.project__package__namespace,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=self.options["inject_namespaces"],
            drop_missing=self.options["drop_missing_schema"],
        )

    def _expand_mapping(self):
        """Walk the mapping and generate any required 'after' steps
        to handle dependent and self-lookups."""
        # Expand the mapping to handle dependent lookups
        self.after_steps = defaultdict(dict)

        for step in self.mapping.values():
            if any([lookup.after for lookup in step.lookups.values()]):
                # We have deferred/dependent lookups.
                # Synthesize mapping steps for them.

                sobject = step.sf_object
                after_list = {
                    lookup.after for lookup in step.lookups.values() if lookup.after
                }

                for after in after_list:
                    lookups = {
                        lookup_field: lookup
                        for lookup_field, lookup in step.lookups.items()
                        if lookup.after == after
                    }
                    name = f"Update {sobject} Dependencies After {after}"
                    mapping = MappingStep(
                        sf_object=sobject,
                        api=step.api,
                        action="update",
                        table=step.table,
                    )
                    mapping.lookups["Id"] = MappingLookup(
                        name="Id",
                        table=step["table"],
                        key_field=self.models[
                            step["table"]
                        ].__table__.primary_key.columns.keys()[0],
                    )
                    for lookup in lookups:
                        mapping.lookups[lookup] = lookups[lookup].copy()
                        mapping.lookups[lookup].after = None

                    self.after_steps[after][name] = mapping

    def _validate_org_has_person_accounts_enabled_if_person_account_data_exists(self):
        """
        To ensure data is loaded from the dataset as expected as well as avoid partial
        failues, raise a BulkDataException if there exists Account or Contact records with
        IsPersonAccount as 'true' but the org does not have person accounts enabled.
        """
        for mapping in self.mapping.values():
            if mapping.sf_object in [
                "Account",
                "Contact",
            ] and self._db_has_person_accounts_column(mapping):
                table = self.models[mapping.table].__table__
                if (
                    self.session.query(table)
                    .filter(table.columns.get("IsPersonAccount") == "true")
                    .first()
                    and not self.org_config.is_person_accounts_enabled
                ):
                    raise BulkDataException(
                        "Your dataset contains Person Account data but Person Accounts is not enabled for your org."
                    )

    def _db_has_person_accounts_column(self, mapping):
        """Returns whether "IsPersonAccount" is a column in mapping's table."""
        return (
            self.models[mapping.table].__table__.columns.get("IsPersonAccount")
            is not None
        )

    def _can_load_person_accounts(self, mapping) -> bool:
        """Returns whether person accounts can be loaded:
        - The mapping has a "IsPersonAccount" column
        - Person Accounts is enabled in the org.
        """
        return (
            self._db_has_person_accounts_column(mapping)
            and self.org_config.is_person_accounts_enabled
        )

    def _generate_contact_id_map_for_person_accounts(
        self, contact_mapping, account_id_lookup, conn
    ):
        """
        Yields (local_id, sf_id) for Contact records where IsPersonAccount
        is true that can handle large data volumes.

        We know a Person Account record is related to one and only one Contact
        record.  Therefore, we can map local Contact IDs to Salesforce IDs
        by previously inserted Account records:
        - Query the DB to get the map: Salesforce Account ID ->
          local Contact ID
        - Query Salesforce to get the map: Salesforce Account ID ->
          Salesforce Contact ID
        - Merge the maps
        """
        # Contact table columns
        contact_model = self.models[contact_mapping.table]

        contact_id_column = getattr(
            contact_model, contact_model.__table__.primary_key.columns.keys()[0]
        )
        account_id_column = getattr(
            contact_model, account_id_lookup.get_lookup_key_field(contact_model)
        )

        # Account ID table + column
        account_sf_ids_table = account_id_lookup.aliased_table
        account_sf_id_column = account_sf_ids_table.columns["sf_id"]

        # Query the Contact table for person account contact records so we can
        # create a Map: Account SF ID --> Contact ID.  Outer join the
        # Account SF IDs table to get each Contact's associated
        # Account SF ID.
        if self._old_format:
            query = (
                self.session.query(contact_id_column, account_sf_id_column)
                .filter(
                    func.lower(contact_model.__table__.columns.get("IsPersonAccount"))
                    == "true"
                )
                .outerjoin(
                    account_sf_ids_table,
                    account_sf_ids_table.columns["id"]
                    == str(account_id_lookup.table) + "-" + account_id_column,
                )
            )
        else:
            query = (
                self.session.query(contact_id_column, account_sf_id_column)
                .filter(
                    func.lower(contact_model.__table__.columns.get("IsPersonAccount"))
                    == "true"
                )
                .outerjoin(
                    account_sf_ids_table,
                    account_sf_ids_table.columns["id"] == account_id_column,
                )
            )

        # Stream the results so we can process batches of 200 Contacts
        # in case we have large data volumes.
        query_result = conn.execution_options(stream_results=True).execute(
            query.statement
        )

        while True:
            # While we have a chunk to process
            chunk = query_result.fetchmany(200)
            if not chunk:
                break

            # Collect Map: Account SF ID --> Contact ID
            contact_ids_by_account_sf_id = {record[1]: record[0] for record in chunk}

            # Query Map: Account SF ID --> Contact SF ID
            # It's safe to use query_all since the chunk size to 200.
            for record in self.sf.query_all(
                "SELECT Id, AccountId FROM Contact WHERE IsPersonAccount = true AND AccountId IN ('{}')".format(
                    "','".join(contact_ids_by_account_sf_id.keys())
                )
            )["records"]:
                contact_id = contact_ids_by_account_sf_id.get(record["AccountId"])
                contact_sf_id = record["Id"]

                # Join maps together to get tuple (Contact ID, Contact SF ID) to insert into step's ID Table.
                if self._old_format:
                    yield (contact_mapping.table + "-" + str(contact_id), contact_sf_id)
                else:
                    yield (contact_id, contact_sf_id)

    def _set_viewed(self) -> T.List["SetRecentlyViewedInfo"]:
        """Set items as recently viewed. Filter out custom objects without custom tabs."""
        object_names = set()
        custom_objects = set()
        results = []

        # Separate standard and custom objects
        for mapping in self.mapping.values():
            object_name = mapping.sf_object
            if object_name.endswith("__c"):
                custom_objects.add(object_name)
            else:
                object_names.add(object_name)
        # collect SobjectName that have custom tabs
        if custom_objects:
            try:
                custom_tab_objects = self.sf.query_all(
                    "SELECT SObjectName FROM TabDefinition WHERE IsCustom = true AND SObjectName IN ('{}')".format(
                        "','".join(sorted(custom_objects))
                    )
                )
                for record in custom_tab_objects["records"]:
                    object_names.add(record["SobjectName"])
            except Exception as e:
                self.logger.warning(
                    f"Cannot get the list of custom tabs to set recently viewed status on them. Error: {e}"
                )
        with get_org_schema(
            self.sf, self.org_config, included_objects=object_names, force_recache=True
        ) as org_schema:
            for mapped_item in sorted(object_names):
                if org_schema[mapped_item].mruEnabled:
                    try:
                        self.sf.query_all(
                            f"SELECT Id FROM {mapped_item} ORDER BY CreatedDate DESC LIMIT 1000 FOR VIEW"
                        )
                        results.append(SetRecentlyViewedInfo(mapped_item, None))
                    except Exception as e:
                        self.logger.warning(
                            f"Cannot set recently viewed status for {mapped_item}. Error: {e}"
                        )
                        results.append(SetRecentlyViewedInfo(mapped_item, e))
        return results


class RollbackType(StrEnum):
    """Enum to specify type of rollback"""

    UPSERT = "upsert_rollback"
    INSERT = "insert_rollback"


class Rollback:
    # Store the table name and it's corresponding API (rest or bulk)
    _initialized_rollback_tables_api = {}

    @staticmethod
    def _create_tables_for_rollback(context, step, rollback_type: RollbackType) -> str:
        """Create the tables required for upsert and insert rollback"""
        table_name = f"{step.sobject}_{rollback_type}"

        if table_name not in Rollback._initialized_rollback_tables_api:
            common_columns = [Column("Id", Unicode(255), primary_key=True)]

            additional_columns = (
                [Column(field, Unicode(255)) for field in step.fields if field != "Id"]
                if rollback_type is RollbackType.UPSERT
                else []
            )

            columns = common_columns + additional_columns

            # Create the table
            rollback_table = Table(table_name, context.metadata, *columns)
            rollback_table.create()

            # Store the API in the initialized tables dictionary
            if isinstance(step, RestApiDmlOperation):
                Rollback._initialized_rollback_tables_api[table_name] = DataApi.REST
            else:
                Rollback._initialized_rollback_tables_api[table_name] = DataApi.BULK

        return table_name

    @staticmethod
    def _perform_rollback(context):
        """Perform total rollback"""
        context.logger.info("--Initiated Rollback Procedure--")
        for table in reversed(context.metadata.sorted_tables):
            if table.name.endswith(RollbackType.INSERT):
                CreateRollback._perform_rollback(context, table)
            elif table.name.endswith(RollbackType.UPSERT):
                UpdateRollback._perform_rollback(context, table)
        context.logger.info("--Finished Rollback Procedure--")


class UpdateRollback:
    @staticmethod
    def prepare_for_rollback(context, step, records):
        """Retrieve previous values for records being updated"""
        results, columns = step.get_prev_record_values(records)
        if results:
            table_name = Rollback._create_tables_for_rollback(
                context, step, RollbackType.UPSERT
            )
            conn = context.session.connection()
            sql_bulk_insert_from_records(
                connection=conn,
                table=context.metadata.tables[table_name],
                columns=columns,
                record_iterable=results,
            )

    @staticmethod
    def _perform_rollback(context, table: Table) -> None:
        """Perform rollback for updated records"""
        sf_object = table.name.split(f"_{RollbackType.UPSERT.value}")[0]
        records = context.session.query(table).all()

        if records:
            context.logger.info(f"Reverting upserts for {sf_object}")
            api_options = {"update_key": "Id"}

            # Use get_dml_operation to create an UPSERT step
            step = get_dml_operation(
                sobject=sf_object,
                operation=DataOperationType.UPSERT,
                api_options=api_options,
                context=context,
                fields=[column.name for column in table.columns],
                api=Rollback._initialized_rollback_tables_api[table.name],
                volume=len(records),
            )
            step.start()
            step.load_records(records)
            step.end()
            context.logger.info("Done")


class CreateRollback:
    @staticmethod
    def prepare_for_rollback(context, step, records):
        """Store the sf_ids of all records that were created
        to prepare for rollback"""
        if records:
            table_name = Rollback._create_tables_for_rollback(
                context, step, RollbackType.INSERT
            )
            conn = context.session.connection()
            sql_bulk_insert_from_records(
                connection=conn,
                table=context.metadata.tables[table_name],
                columns=["Id"],
                record_iterable=records,
            )

    @staticmethod
    def _perform_rollback(context, table: Table) -> None:
        """Perform rollback for insert operation"""
        sf_object = table.name.split(f"_{RollbackType.INSERT.value}")[0]
        records = context.session.query(table).all()

        if records:
            context.logger.info(f"Deleting {sf_object} records")
            # Perform DELETE operation using get_dml_operation
            step = get_dml_operation(
                sobject=sf_object,
                operation=DataOperationType.DELETE,
                fields=["Id"],
                api_options={},
                context=context,
                api=Rollback._initialized_rollback_tables_api[table.name],
                volume=len(records),
            )
            step.start()
            step.load_records(records)
            step.end()
            context.logger.info("Done")


class StepResultInfo(T.NamedTuple):
    """Represent a Step Result in a form easily convertible to JSON"""

    sobject: str
    result: DataOperationJobResult
    record_type: str = None

    def simplify(self):
        return {
            "sobject": self.sobject,
            "record_type": self.record_type,
            **self.result.simplify(),
        }


class SetRecentlyViewedInfo(T.NamedTuple):
    """Did the set recently succeed or fail?"""

    sobject: str
    error: T.Optional[Exception]
