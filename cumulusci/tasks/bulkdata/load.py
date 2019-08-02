import datetime
import os
import io
import unicodecsv

from salesforce_bulk.util import IteratorBytesIO
from sqlalchemy import Column, MetaData, Table, Unicode, create_engine, text
from sqlalchemy.orm import aliased, Session
from sqlalchemy.ext.automap import automap_base

from cumulusci.core.exceptions import BulkDataException
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.utils import (
    BulkJobTaskMixin,
    get_lookup_key_field,
    download_file,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.utils import ordered_yaml_load, process_bool_arg

from cumulusci.utils import os_friendly_path


class LoadData(BulkJobTaskMixin, BaseSalesforceApiTask):

    task_options = {
        "database_url": {
            "description": "The database url to a database containing the test data to load",
            "required": True,
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
    }

    def _init_options(self, kwargs):
        super(LoadData, self)._init_options(kwargs)

        self.options["ignore_row_errors"] = process_bool_arg(
            self.options.get("ignore_row_errors", False)
        )
        if self.options.get("sql_path"):
            if self.options.get("database_url"):
                raise TaskOptionsError(
                    "The database_url option is set dynamically with the sql_path option.  Please unset the database_url option."
                )
            self.options["sql_path"] = os_friendly_path(self.options["sql_path"])
            if not os.path.isfile(self.options["sql_path"]):
                raise TaskOptionsError(
                    "File {} does not exist".format(self.options["sql_path"])
                )
            self.logger.info("Using in-memory sqlite database")
            self.options["database_url"] = "sqlite://"

    def _run_task(self):
        self._init_mapping()
        self._init_db()

        start_step = self.options.get("start_step")
        started = False
        for name, mapping in self.mapping.items():
            # Skip steps until start_step
            if not started and start_step and name != start_step:
                self.logger.info("Skipping step: {}".format(name))
                continue
            started = True

            self.logger.info("Running Job: {}".format(name))
            result = self._load_mapping(mapping)
            if result != "Completed":
                raise BulkDataException(
                    "Job {} did not complete successfully".format(name)
                )

    def _load_mapping(self, mapping):
        """Load data for a single step."""
        mapping["oid_as_pk"] = bool(mapping.get("fields", {}).get("Id"))
        job_id, local_ids_for_batch = self._create_job(mapping)
        result = self._wait_for_job(job_id)

        self._store_inserted_ids(mapping, job_id, local_ids_for_batch)
        return result

    def _create_job(self, mapping):
        """Initiate a bulk insert and upload batches to run in parallel."""
        job_id = self.bulk.create_insert_job(mapping["sf_object"], contentType="CSV")
        self.logger.info("  Created bulk job {}".format(job_id))

        # Upload batches
        local_ids_for_batch = {}
        for batch_file, local_ids in self._get_batches(mapping):
            batch_id = self.bulk.post_batch(job_id, batch_file)
            local_ids_for_batch[batch_id] = local_ids
            self.logger.info("    Uploaded batch {}".format(batch_id))

        self.bulk.close_job(job_id)
        return job_id, local_ids_for_batch

    def _get_batches(self, mapping, batch_size=10000):
        """Get data from the local db"""
        action = mapping.get("action", "insert")
        fields = mapping.get("fields", {}).copy()
        static = mapping.get("static", {})
        lookups = mapping.get("lookups", {})
        record_type = mapping.get("record_type")

        # Skip Id field on insert
        if action == "insert" and "Id" in fields:
            del fields["Id"]

        # Build the list of fields to import
        columns = []
        columns.extend(fields.keys())
        columns.extend(lookups.keys())
        columns.extend(static.keys())

        if record_type:
            columns.append("RecordTypeId")
            # default to the profile assigned recordtype if we can't find any
            # query for the RT by developer name
            query = (
                "SELECT Id FROM RecordType WHERE SObjectType='{0}'"
                "AND DeveloperName = '{1}' LIMIT 1"
            )
            record_type_id = self.sf.query(
                query.format(mapping.get("sf_object"), record_type)
            )["records"][0]["Id"]

        query = self._query_db(mapping)

        total_rows = 0
        batch_num = 1

        def start_batch():
            batch_file = io.BytesIO()
            writer = unicodecsv.writer(batch_file)
            writer.writerow(columns)
            batch_ids = []
            return batch_file, writer, batch_ids

        batch_file, writer, batch_ids = start_batch()
        for row in query.yield_per(batch_size):
            total_rows += 1

            # Add static values to row
            pkey = row[0]
            row = list(row[1:]) + list(static.values())
            if record_type:
                row.append(record_type_id)

            writer.writerow([self._convert(value) for value in row])
            batch_ids.append(pkey)

            # Yield and start a new file every [batch_size] rows
            if not total_rows % batch_size:
                batch_file.seek(0)
                self.logger.info("    Processing batch {}".format(batch_num))
                yield batch_file, batch_ids
                batch_file, writer, batch_ids = start_batch()
                batch_num += 1

        # Yield result file for final batch
        if batch_ids:
            batch_file.seek(0)
            yield batch_file, batch_ids

        self.logger.info(
            "  Prepared {} rows for import to {}".format(
                total_rows, mapping["sf_object"]
            )
        )

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

        for f in fields.values():
            columns.append(model.__table__.columns[f])
        lookups = mapping.get("lookups", {}).copy()
        for lookup in lookups.values():
            lookup["aliased_table"] = aliased(
                self.metadata.tables["{}_sf_ids".format(lookup["table"])]
            )
            columns.append(lookup["aliased_table"].columns.sf_id)

        query = self.session.query(*columns)
        if "record_type" in mapping and hasattr(model, "record_type"):
            query = query.filter(model.record_type == mapping["record_type"])
        if "filters" in mapping:
            filter_args = []
            for f in mapping["filters"]:
                filter_args.append(text(f))
            query = query.filter(*filter_args)
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
        self.logger.info(str(query))
        return query

    def _convert(self, value):
        if value:
            if isinstance(value, datetime.datetime):
                return value.isoformat()
            return value

    def _store_inserted_ids(self, mapping, job_id, local_ids_for_batch):
        """Get the job results and store inserted SF Ids in a new table"""
        id_table_name = self._reset_id_table(mapping)
        conn = self.session.connection()
        for batch_id, local_ids in local_ids_for_batch.items():
            try:
                results_url = "{}/job/{}/batch/{}/result".format(
                    self.bulk.endpoint, job_id, batch_id
                )
                # Download entire result file to a temporary file first
                # to avoid the server dropping connections
                with download_file(results_url, self.bulk) as f:
                    self.logger.info(
                        "  Downloaded results for batch {}".format(batch_id)
                    )
                    self._store_inserted_ids_for_batch(
                        f, local_ids, id_table_name, conn
                    )
                self.logger.info(
                    "  Updated {} for batch {}".format(id_table_name, batch_id)
                )
            except BulkDataException:
                raise
            except Exception as e:
                raise BulkDataException(
                    "Failed to download results for batch {} ({})".format(
                        batch_id, str(e)
                    )
                )

        self.session.commit()

    def _reset_id_table(self, mapping):
        """Create an empty table to hold the inserted SF Ids"""
        if not hasattr(self, "_initialized_id_tables"):
            self._initialized_id_tables = set()
        id_table_name = "{}_sf_ids".format(mapping["table"])
        if id_table_name not in self._initialized_id_tables:
            if id_table_name in self.metadata.tables:
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

    def _store_inserted_ids_for_batch(
        self, result_file, local_ids, id_table_name, conn
    ):
        # Set up a function to generate rows based on this result file
        def produce_csv():
            """Iterate over job results and prepare rows for id table"""
            reader = unicodecsv.reader(result_file)
            next(reader)  # skip header
            i = 0
            for row, local_id in zip(reader, local_ids):
                if row[1] == "true":  # Success
                    sf_id = row[0]
                    yield "{},{}\n".format(local_id, sf_id).encode("utf-8")
                else:
                    if self.options["ignore_row_errors"]:
                        self.logger.warning(
                            "      Error on row {}: {}".format(i, row[3])
                        )
                    else:
                        raise BulkDataException("Error on row {}: {}".format(i, row[3]))
                i += 1

        # Bulk insert rows into id table
        columns = ("id", "sf_id")
        data_file = IteratorBytesIO(produce_csv())
        self._sql_bulk_insert_from_csv(conn, id_table_name, columns, data_file)

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
        self.engine = create_engine(self.options["database_url"])

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

    def _init_mapping(self):
        with open(self.options["mapping"], "r") as f:
            self.mapping = ordered_yaml_load(f)
