import datetime
import io

from collections import defaultdict
from salesforce_bulk.util import IteratorBytesIO
from sqlalchemy import Column, MetaData, Table, Unicode, create_engine, text
from sqlalchemy.orm import aliased, Session
from sqlalchemy.ext.automap import automap_base
import unicodecsv
import yaml

from cumulusci.core.exceptions import BulkDataException
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.utils import (
    BulkJobTaskMixin,
    get_lookup_key_field,
    download_file,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.utils import process_bool_arg

from cumulusci.utils import os_friendly_path


class LoadData(BulkJobTaskMixin, BaseSalesforceApiTask):

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
        if self.bulk_mode and self.bulk_mode not in [
            "Serial",
            "Parallel",
        ]:
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

            self.logger.info(f"Running Job: {name}")
            result = self._load_mapping(mapping)
            if result != "Completed":
                raise BulkDataException(f"Job {name} did not complete successfully")
            if name in self.after_steps:
                for after_name, after_step in self.after_steps[name].items():
                    self.logger.info(f"Running post-load step: {after_name}")
                    result = self._load_mapping(after_step)
                    if result != "Completed":
                        raise BulkDataException(
                            f"Job {after_name} did not complete successfully"
                        )

    def _load_mapping(self, mapping):
        """Load data for a single step."""

        if "RecordTypeId" in mapping["fields"]:
            conn = self.session.connection()
            self._load_record_types([mapping["sf_object"]], conn)
        mapping["oid_as_pk"] = bool(mapping.get("fields", {}).get("Id"))
        job_id, local_ids_for_batch = self._create_job(mapping)
        result = self._wait_for_job(job_id)

        self._process_job_results(mapping, job_id, local_ids_for_batch)

        return result

    def _create_job(self, mapping):
        """Initiate a bulk insert or update and upload batches to run in parallel."""
        action = mapping["action"]
        step_mode = mapping.get("bulk_mode")
        task_mode = self.bulk_mode
        mode = step_mode or task_mode or "Parallel"

        if action == "insert":
            job_id = self.bulk.create_insert_job(
                mapping["sf_object"], contentType="CSV", concurrency=mode
            )
        else:
            job_id = self.bulk.create_update_job(
                mapping["sf_object"], contentType="CSV", concurrency=mode
            )

        self.logger.info(f"  Created bulk job {job_id}")

        # Upload batches
        local_ids_for_batch = {}
        for batch_file, local_ids in self._get_batches(mapping):
            batch_id = self.bulk.post_batch(job_id, batch_file)
            local_ids_for_batch[batch_id] = local_ids
            self.logger.info(f"    Uploaded batch {batch_id}")

        self.bulk.close_job(job_id)
        return job_id, local_ids_for_batch

    def _get_batches(self, mapping, batch_size=10000):
        """Get data from the local db"""

        columns = self._get_columns(mapping)
        statics = self._get_statics(mapping)
        query = self._query_db(mapping)

        total_rows = 0
        batch_num = 1

        batch_file, writer, batch_ids = self._start_batch(columns)
        for row in query.yield_per(batch_size):
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

            writer.writerow(row)
            batch_ids.append(pkey)

            # Yield and start a new file every [batch_size] rows
            if not total_rows % batch_size:
                batch_file.seek(0)
                self.logger.info(f"    Processing batch {batch_num}")
                yield batch_file, batch_ids
                batch_file, writer, batch_ids = self._start_batch(columns)
                batch_num += 1

        # Yield result file for final batch
        if batch_ids:
            batch_file.seek(0)
            yield batch_file, batch_ids

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

    def _start_batch(self, columns):
        batch_file = io.BytesIO()
        writer = unicodecsv.writer(batch_file)
        writer.writerow(columns)
        batch_ids = []
        return batch_file, writer, batch_ids

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

        self.logger.debug(str(query))

        return query

    def _convert(self, value):
        if value:
            if isinstance(value, datetime.datetime):
                return value.isoformat()
            return value

    def _process_job_results(self, mapping, job_id, local_ids_for_batch):
        """Get the job results and process the results. If we're raising for
        row-level errors, do so; if we're inserting, store the new Ids."""
        if mapping["action"] == "insert":
            id_table_name = self._initialize_id_table(mapping, self.reset_oids)
            conn = self.session.connection()

        for batch_id, local_ids in local_ids_for_batch.items():
            try:
                results_url = (
                    f"{self.bulk.endpoint}/job/{job_id}/batch/{batch_id}/result"
                )
                # Download entire result file to a temporary file first
                # to avoid the server dropping connections
                with download_file(results_url, self.bulk) as f:
                    self.logger.info(f"  Downloaded results for batch {batch_id}")
                    results_generator = self._generate_results_id_map(f, local_ids)
                    if mapping["action"] == "insert":
                        self._sql_bulk_insert_from_csv(
                            conn,
                            id_table_name,
                            ("id", "sf_id"),
                            IteratorBytesIO(results_generator),
                        )
                        self.logger.info(
                            f"  Updated {id_table_name} for batch {batch_id}"
                        )
                    else:
                        for r in results_generator:
                            pass  # Drain generator to validate results

            except BulkDataException:
                raise
            except Exception as e:
                raise BulkDataException(
                    f"Failed to download results for batch {batch_id} ({str(e)})"
                )

        if mapping["action"] == "insert":
            self.session.commit()

    def _generate_results_id_map(self, result_file, local_ids):
        """Iterate over job results and prepare rows for id table"""
        reader = unicodecsv.reader(result_file)
        next(reader)  # skip header
        i = 0
        for row, local_id in zip(reader, local_ids):
            if row[1] == "true":  # Success
                sf_id = row[0]
                yield f"{local_id},{sf_id}\n".encode("utf-8")
            else:
                if self.options["ignore_row_errors"]:
                    self.logger.warning(f"      Error on row {i}: {row[3]}")
                else:
                    raise BulkDataException(f"Error on row {i}: {row[3]}")
            i += 1

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
