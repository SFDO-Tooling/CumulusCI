from collections import defaultdict
import datetime
from unittest.mock import MagicMock
from typing import Union

from sqlalchemy import Column, MetaData, Table, Unicode, create_engine, text
from sqlalchemy.orm import aliased, Session
from sqlalchemy.ext.automap import automap_base

from cumulusci.core.exceptions import BulkDataException, TaskOptionsError
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.bulkdata.utils import (
    SqlAlchemyMixin,
    RowErrorChecker,
)
from cumulusci.tasks.bulkdata.step import (
    BulkApiDmlOperation,
    DataOperationStatus,
    DataOperationType,
    DataOperationJobResult,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils import os_friendly_path

from cumulusci.tasks.bulkdata.mapping_parser import (
    parse_from_yaml,
    MappingStep,
    MappingLookup,
)


class LoadData(BaseSalesforceApiTask, SqlAlchemyMixin):
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
    }
    row_warning_limit = 10

    def _init_options(self, kwargs):
        super(LoadData, self)._init_options(kwargs)

        self.options["ignore_row_errors"] = process_bool_arg(
            self.options.get("ignore_row_errors", False)
        )
        if self.options.get("database_url"):
            # prefer database_url if it's set
            self.options["sql_path"] = None
        elif self.options.get("sql_path"):
            self.options["sql_path"] = os_friendly_path(self.options["sql_path"])
            self.options["database_url"] = None
        else:
            raise TaskOptionsError(
                "You must set either the database_url or sql_path option."
            )
        self.reset_oids = self.options.get("reset_oids", True)
        self.bulk_mode = (
            self.options.get("bulk_mode") and self.options.get("bulk_mode").title()
        )
        if self.bulk_mode and self.bulk_mode not in ["Serial", "Parallel"]:
            raise TaskOptionsError("bulk_mode must be either Serial or Parallel")

    def _run_task(self):
        self._init_mapping()
        self._init_db()
        self._expand_mapping()

        start_step = self.options.get("start_step")
        started = False
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

    def _execute_step(
        self, mapping: MappingStep
    ) -> Union[DataOperationJobResult, MagicMock]:
        """Load data for a single step."""

        if mapping.get("fields", {}).get("RecordTypeId"):
            conn = self.session.connection()
            self._load_record_types([mapping["sf_object"]], conn)
            self.session.commit()

        mapping["oid_as_pk"] = bool(mapping.get("fields", {}).get("Id"))

        bulk_mode = mapping.get("bulk_mode") or self.bulk_mode or "Parallel"

        step = BulkApiDmlOperation(
            sobject=mapping["sf_object"],
            operation=(
                DataOperationType.INSERT
                if mapping.get("action") == "insert"
                else DataOperationType.UPDATE
            ),
            api_options={"bulk_mode": bulk_mode},
            context=self,
            fields=self._get_columns(mapping),
        )

        local_ids = []
        step.start()
        step.load_records(self._stream_queried_data(mapping, local_ids))
        step.end()

        if step.job_result.status is not DataOperationStatus.JOB_FAILURE:
            self._process_job_results(mapping, step, local_ids)

        return step.job_result

    def _stream_queried_data(self, mapping, local_ids):
        """Get data from the local db"""

        statics = self._get_statics(mapping)
        query = self._query_db(mapping)

        total_rows = 0

        # 10,000 is the maximum Bulk API size. Clamping the yield from the query ensures we do not
        # create more Bulk API batches than expected, regardless of batch size, while capping
        # memory usage.
        for row in query.yield_per(10000):
            total_rows += 1
            # Add static values to row
            pkey = row[0]
            row = list(row[1:]) + statics
            row = [self._convert(value) for value in row]
            if mapping["action"] == "update":
                if len(row) > 1 and all([f is None for f in row[1:]]):
                    # Skip update rows that contain no values
                    total_rows -= 1
                    continue

            local_ids.append(pkey)
            yield row

        self.logger.info(
            f"Prepared {total_rows} rows for {mapping['action']} to {mapping['sf_object']}"
        )

    def _get_columns(self, mapping):
        """Build a flat list of columns for the given mapping,
        including fields, lookups, and statics."""
        lookups = mapping.get("lookups", {})

        # Build the list of fields to import
        columns = []
        columns.extend(mapping.get("fields", {}).keys())
        # Don't include lookups with an `after:` spec (dependent lookups)
        columns.extend([f for f in lookups if not lookups[f].get("after")])
        columns.extend(mapping.get("static", {}).keys())
        # If we're using Record Type mapping, `RecordTypeId` goes at the end.
        if "RecordTypeId" in columns:
            columns.remove("RecordTypeId")
        if "RecordType" in columns:
            columns.remove("RecordType")

        if mapping["action"] == "insert" and "Id" in columns:
            columns.remove("Id")
        if mapping.get("record_type") or "RecordTypeId" in mapping.get("fields", {}):
            columns.append("RecordTypeId")

        return columns

    def _load_record_types(self, sobjects, conn):
        """Persist record types for the given sObjects into the database."""
        for sobject in sobjects:
            table_name = sobject + "_rt_target_mapping"
            self._extract_record_types(sobject, table_name, conn)

    def _get_statics(self, mapping):
        """Return the static values (not column names) to be appended to
        records for this mapping."""
        statics = list(mapping.get("static", {}).values())
        if mapping.get("record_type"):
            query = (
                f"SELECT Id FROM RecordType WHERE SObjectType='{mapping.get('sf_object')}'"
                f"AND DeveloperName = '{mapping['record_type']}' LIMIT 1"
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
        model = self.models[mapping.get("table")]

        # Use primary key instead of the field mapped to SF Id
        fields = mapping.get("fields", {}).copy()
        if mapping["oid_as_pk"]:
            del fields["Id"]

        id_column = model.__table__.primary_key.columns.keys()[0]
        columns = [getattr(model, id_column)]

        for name, f in fields.items():
            if name not in ("RecordTypeId", "RecordType"):
                columns.append(model.__table__.columns[f])

        lookups = {
            lookup_field: lookup
            for lookup_field, lookup in mapping.get("lookups", {}).items()
            if not lookup.get("after")
        }

        for lookup in lookups.values():
            lookup["aliased_table"] = aliased(
                self.metadata.tables[f"{lookup['table']}_sf_ids"]
            )
            columns.append(lookup["aliased_table"].columns.sf_id)

        if mapping["fields"].get("RecordTypeId"):
            rt_dest_table = self.metadata.tables[
                mapping["sf_object"] + "_rt_target_mapping"
            ]
            columns.append(rt_dest_table.columns.record_type_id)

        query = self.session.query(*columns)
        if mapping.get("record_type") and hasattr(model, "record_type"):
            query = query.filter(model.record_type == mapping["record_type"])
        if mapping.get("filters"):
            filter_args = []
            for f in mapping["filters"]:
                filter_args.append(text(f))
            query = query.filter(*filter_args)

        if mapping["fields"].get("RecordTypeId"):
            rt_source_table = self.metadata.tables[mapping["sf_object"] + "_rt_mapping"]
            rt_dest_table = self.metadata.tables[
                mapping["sf_object"] + "_rt_target_mapping"
            ]
            query = query.outerjoin(
                rt_source_table,
                rt_source_table.columns.record_type_id
                == getattr(model, mapping["fields"]["RecordTypeId"]),
            )
            query = query.outerjoin(
                rt_dest_table,
                rt_dest_table.columns.developer_name
                == rt_source_table.columns.developer_name,
            )

        for sf_field, lookup in lookups.items():
            # Outer join with lookup ids table:
            # returns main obj even if lookup is null
            key_field = lookup.get_lookup_key_field(model)
            value_column = getattr(model, key_field)
            query = query.outerjoin(
                lookup["aliased_table"],
                lookup["aliased_table"].columns.id == value_column,
            )
            # Order by foreign key to minimize lock contention
            # by trying to keep lookup targets in the same batch
            lookup_column = getattr(model, key_field)
            query = query.order_by(lookup_column)

        return query

    def _convert(self, value):
        """If value is a date, return its ISO8601 representation, otherwise return value."""
        if value:
            if isinstance(value, datetime.datetime):
                return value.isoformat()
            return value

    def _process_job_results(self, mapping, step, local_ids):
        """Get the job results and process the results. If we're raising for
        row-level errors, do so; if we're inserting, store the new Ids."""
        if mapping["action"] == "insert":
            id_table_name = self._initialize_id_table(mapping, self.reset_oids)
            conn = self.session.connection()

        results_generator = self._generate_results_id_map(step, local_ids)

        # If we know we have no successful inserts, don't attempt to persist Ids.
        # Do, however, drain the generator to get error-checking behavior.
        if mapping["action"] == "insert" and (
            step.job_result.records_processed - step.job_result.total_row_errors
        ):
            self._sql_bulk_insert_from_records(
                connection=conn,
                table=id_table_name,
                columns=("id", "sf_id"),
                record_iterable=results_generator,
            )
        else:
            for r in results_generator:
                pass  # Drain generator to validate results

        if mapping["action"] == "insert":
            self.session.commit()

    def _generate_results_id_map(self, step, local_ids):
        """Consume results from load and prepare rows for id table.
        Raise BulkDataException on row errors if configured to do so."""
        error_checker = RowErrorChecker(
            self.logger, self.options["ignore_row_errors"], self.row_warning_limit
        )
        for result, local_id in zip(step.get_results(), local_ids):
            if result.success:
                yield (local_id, result.id)
            else:
                error_checker.check_for_row_error(result, local_id)

    def _initialize_id_table(self, mapping, should_reset_table):
        """initalize or find table to hold the inserted SF Ids

        The table has a name like xxx_sf_ids and has just two columns, id and sf_id.

        If the table already exists, should_reset_table determines whether to
        drop and recreate it or not.
        """
        id_table_name = f"{mapping['table']}_sf_ids"

        already_exists = id_table_name in self.metadata.tables

        if already_exists and not should_reset_table:
            return id_table_name

        if not hasattr(self, "_initialized_id_tables"):
            self._initialized_id_tables = set()
        if id_table_name not in self._initialized_id_tables:
            if already_exists:
                self.metadata.remove(self.metadata.tables[id_table_name])
            id_table = Table(
                id_table_name,
                self.metadata,
                Column("id", Unicode(255), primary_key=True),
                Column("sf_id", Unicode(18)),
            )
            if id_table.exists():
                id_table.drop()
            id_table.create()
            self._initialized_id_tables.add(id_table_name)
        return id_table_name

    def _sqlite_load(self):
        """Read a SQLite script and initialize the in-memory database."""
        conn = self.session.connection()
        cursor = conn.connection.cursor()
        with open(self.options["sql_path"], "r") as f:
            try:
                cursor.executescript(f.read())
            finally:
                cursor.close()
        # self.session.flush()

    def _init_db(self):
        """Initialize the database and automapper."""
        # initialize the DB engine
        database_url = self.options["database_url"] or "sqlite://"
        if database_url == "sqlite://":
            self.logger.info("Using in-memory SQLite database")
        self.engine = create_engine(database_url)

        # initialize the DB session
        self.session = Session(self.engine)

        if self.options.get("sql_path"):
            self._sqlite_load()

        # initialize DB metadata
        self.metadata = MetaData()
        self.metadata.bind = self.engine

        # initialize the automap mapping
        self.base = automap_base(bind=self.engine, metadata=self.metadata)
        self.base.prepare(self.engine, reflect=True)

        # Loop through mappings and reflect each referenced table
        self.models = {}
        for name, mapping in self.mapping.items():
            if "table" in mapping and mapping["table"] not in self.models:
                self.models[mapping["table"]] = self.base.classes[mapping["table"]]

            # create any Record Type tables we need
            if mapping.get("fields", {}).get("RecordTypeId"):
                self._create_record_type_table(
                    mapping["sf_object"] + "_rt_target_mapping"
                )
        self.metadata.create_all()

    def _init_mapping(self):
        """Load a YAML mapping file."""
        mapping_file_path = self.options["mapping"]
        if not mapping_file_path:
            raise TaskOptionsError("Mapping file path required")

        self.mapping = parse_from_yaml(mapping_file_path)

    def _expand_mapping(self):
        """Walk the mapping and generate any required 'after' steps
        to handle dependent and self-lookups."""
        # Expand the mapping to handle dependent lookups
        self.after_steps = defaultdict(dict)

        for step in self.mapping.values():
            step["action"] = step.get("action", "insert")
            if step.get("lookups") and any(
                [l.get("after") for l in step["lookups"].values()]
            ):
                # We have deferred/dependent lookups.
                # Synthesize mapping steps for them.

                sobject = step["sf_object"]
                after_list = {
                    l["after"] for l in step["lookups"].values() if l.get("after")
                }

                for after in after_list:
                    lookups = {
                        lookup_field: lookup
                        for lookup_field, lookup in step["lookups"].items()
                        if lookup.get("after") == after
                    }
                    name = f"Update {sobject} Dependencies After {after}"
                    mapping = {
                        "sf_object": sobject,
                        "action": "update",
                        "table": step["table"],
                        "lookups": {},
                        "fields": {},
                    }
                    mapping["lookups"]["Id"] = MappingLookup(
                        name="Id",
                        table=step["table"],
                        key_field=self.models[
                            step["table"]
                        ].__table__.primary_key.columns.keys()[0],
                    )
                    for l in lookups:
                        mapping["lookups"][l] = lookups[l].copy()
                        mapping["lookups"][l]["after"] = None

                    self.after_steps[after][name] = mapping
