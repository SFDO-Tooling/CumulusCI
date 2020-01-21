import datetime
import yaml

from collections import defaultdict
from sqlalchemy import Column, MetaData, Table, Unicode, create_engine, text
from sqlalchemy.orm import aliased, Session
from sqlalchemy.ext.automap import automap_base

from cumulusci.core.exceptions import BulkDataException
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.utils import get_lookup_key_field, SqlAlchemyMixin

from cumulusci.tasks.bulkdata.step import BulkApiDmlStep, Status, Operation
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.utils import process_bool_arg
from cumulusci.utils import os_friendly_path


class LoadData(BaseSalesforceApiTask, SqlAlchemyMixin):
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
        "bulk_mode": {},
    }

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
            result = self._load_mapping(mapping)
            if result is Status.FAILURE:
                raise BulkDataException(f"Step {name} did not complete successfully")

            if name in self.after_steps:
                for after_name, after_step in self.after_steps[name].items():
                    self.logger.info(f"Running post-load step: {after_name}")
                    result = self._load_mapping(after_step)
                    if result is Status.FAILURE:
                        raise BulkDataException(
                            f"Step {after_name} did not complete successfully"
                        )

    def _load_mapping(self, mapping):
        """Load data for a single step."""

        if "RecordTypeId" in mapping["fields"]:
            conn = self.session.connection()
            self._load_record_types([mapping["sf_object"]], conn)

        mapping["oid_as_pk"] = bool(mapping.get("fields", {}).get("Id"))

        step = BulkApiDmlStep(
            mapping["sf_object"],
            Operation.INSERT if mapping.get("action") == "insert" else Operation.UPDATE,
            {},
            self,
            self._get_columns(mapping),
        )

        step.start()
        step.load_records(self._stream_queried_data(mapping))
        step.end()

        if step.status is not Status.FAILURE:
            self._process_job_results(mapping, step)

        return step.status

    def _stream_queried_data(self, mapping):
        """Get data from the local db"""

        statics = self._get_statics(mapping)
        query = self._query_db(mapping)

        total_rows = 0
        self.local_ids = []

        for (
            row
        ) in query:  # FIXME: use .yield_per(10000) to clamp upper limit of memory use?
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

            self.local_ids.append(pkey)
            yield row

        self.logger.info(
            f"  Prepared {total_rows} rows for {mapping['action']} to {mapping['sf_object']}"
        )

    def _get_columns(self, mapping):
        lookups = mapping.get("lookups", {})

        # Build the list of fields to import
        columns = []
        columns.extend(mapping.get("fields", {}).keys())
        # Don't include lookups with an `after:` spec (dependent lookups)
        columns.extend([f for f in lookups if "after" not in lookups[f]])
        columns.extend(mapping.get("static", {}).keys())
        # If we're using Record Type mapping, `RecordTypeId` goes at the end.
        if "RecordTypeId" in columns:
            columns.remove("RecordTypeId")

        if mapping["action"] == "insert" and "Id" in columns:
            columns.remove("Id")
        if mapping.get("record_type") or "RecordTypeId" in mapping.get("fields", {}):
            columns.append("RecordTypeId")

        return columns

    def _load_record_types(self, sobjects, conn):
        for sobject in sobjects:
            table_name = sobject + "_rt_target_mapping"
            self._extract_record_types(sobject, table_name, conn)

    def _get_statics(self, mapping):
        statics = list(mapping.get("static", {}).values())
        if mapping.get("record_type"):
            query = (
                f"SELECT Id FROM RecordType WHERE SObjectType='{mapping.get('sf_object')}'"
                f"AND DeveloperName = '{mapping['record_type']}' LIMIT 1"
            )
            record_type_id = self.sf.query(query)["records"][0]["Id"]
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
            if name != "RecordTypeId":
                columns.append(model.__table__.columns[f])

        lookups = {
            lookup_field: lookup
            for lookup_field, lookup in mapping.get("lookups", {}).items()
            if "after" not in lookup
        }
        for lookup in lookups.values():
            lookup["aliased_table"] = aliased(
                self.metadata.tables[f"{lookup['table']}_sf_ids"]
            )
            columns.append(lookup["aliased_table"].columns.sf_id)

        if "RecordTypeId" in mapping["fields"]:
            rt_dest_table = self.metadata.tables[
                mapping["sf_object"] + "_rt_target_mapping"
            ]
            columns.append(rt_dest_table.columns.record_type_id)

        query = self.session.query(*columns)
        if "record_type" in mapping and hasattr(model, "record_type"):
            query = query.filter(model.record_type == mapping["record_type"])
        if "filters" in mapping:
            filter_args = []
            for f in mapping["filters"]:
                filter_args.append(text(f))
            query = query.filter(*filter_args)

        if "RecordTypeId" in mapping["fields"]:
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
            key_field = get_lookup_key_field(lookup, sf_field)
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
        if value:
            if isinstance(value, datetime.datetime):
                return value.isoformat()
            return value

    def _process_job_results(self, mapping, step):
        """Get the job results and process the results. If we're raising for
        row-level errors, do so; if we're inserting, store the new Ids."""
        if mapping["action"] == "insert":
            id_table_name = self._initialize_id_table(mapping, self.reset_oids)
            conn = self.session.connection()

        results_generator = self._generate_results_id_map(step, self.local_ids)
        if mapping["action"] == "insert":
            self._sql_bulk_insert_from_records(
                conn, id_table_name, ("id", "sf_id"), results_generator
            )
        else:
            for r in results_generator:
                pass  # Drain generator to validate results

        if mapping["action"] == "insert":
            self.session.commit()

    def _generate_results_id_map(self, step, local_ids):
        """Consume results from load and prepare rows for id table.
        Raise BulkDataException on row errors if configured to do so."""

        for result, local_id in zip(step.get_results(), local_ids):
            if result.success:
                yield (local_id, result.id)
            else:
                if self.options["ignore_row_errors"]:
                    self.logger.warning(
                        f"Error on record with id {local_id}: {result.error}"
                    )
                else:
                    raise BulkDataException(
                        f"Error on record with id {local_id}: {result.error}"
                    )

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
        conn = self.session.connection()
        cursor = conn.connection.cursor()
        with open(self.options["sql_path"], "r") as f:
            try:
                cursor.executescript(f.read())
            finally:
                cursor.close()
        # self.session.flush()

    def _init_db(self):
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
            if "fields" in mapping and "RecordTypeId" in mapping["fields"]:
                self._create_record_type_table(
                    mapping["sf_object"] + "_rt_target_mapping"
                )
        self.metadata.create_all()

    def _init_mapping(self):
        with open(self.options["mapping"], "r") as f:
            self.mapping = yaml.safe_load(f)

    def _expand_mapping(self):
        # Expand the mapping to handle dependent lookups
        self.after_steps = defaultdict(dict)

        for step in self.mapping.values():
            step["action"] = step.get("action", "insert")
            if "lookups" in step and any(
                ["after" in l for l in step["lookups"].values()]
            ):
                # We have deferred/dependent lookups.
                # Synthesize mapping steps for them.

                sobject = step["sf_object"]
                after_list = {
                    l["after"] for l in step["lookups"].values() if "after" in l
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
                    mapping["lookups"]["Id"] = {
                        "table": step["table"],
                        "key_field": self.models[
                            step["table"]
                        ].__table__.primary_key.columns.keys()[0],
                    }
                    for l in lookups:
                        mapping["lookups"][l] = lookups[l].copy()
                        del mapping["lookups"][l]["after"]

                    self.after_steps[after][name] = mapping
