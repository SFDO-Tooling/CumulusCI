import collections
import logging
import tempfile
import typing as T
from contextlib import contextmanager, nullcontext
from pathlib import Path

from simple_salesforce import Salesforce
from sqlalchemy import Boolean, Column, Integer, MetaData, Table, Unicode, inspect
from sqlalchemy.engine.base import Connection
from sqlalchemy.orm import Session, mapper

from cumulusci.core.exceptions import BulkDataException
from cumulusci.utils.iterators import iterate_in_chunks

ID_TABLE_NAME = "cumulusci_id_table"


class SqlAlchemyMixin:
    logger: logging.Logger
    metadata: MetaData
    models: dict
    options: dict
    session: Session
    sf: Salesforce

    def _create_record_type_table(self, table_name):
        """Create a table to store mapping between Record Type Ids and Developer Names."""
        rt_map_model_name = f"{table_name}Model"
        self.models[table_name] = type(rt_map_model_name, (object,), {})
        rt_map_fields = [
            Column("record_type_id", Unicode(18), primary_key=True),
            Column("developer_name", Unicode(255)),
            Column("is_person_type", Boolean),
        ]
        rt_map_table = Table(table_name, self.metadata, *rt_map_fields)
        mapper(self.models[table_name], rt_map_table)

    def _extract_record_types(
        self, sobject, tablename: str, conn, is_person_accounts_enabled: bool
    ):
        """Query for Record Type information and persist it in the database."""
        self.logger.info(f"Extracting Record Types for {sobject}")
        if is_person_accounts_enabled:
            query = f"SELECT Id, DeveloperName, IsPersonType FROM RecordType WHERE SObjectType='{sobject}'"
        else:
            query = f"SELECT Id, DeveloperName FROM RecordType WHERE SObjectType='{sobject}'"

        result = self.sf.query(query)

        if result["totalSize"]:
            sql_bulk_insert_from_records(
                connection=conn,
                table=self.metadata.tables[tablename],
                columns=["record_type_id", "developer_name", "is_person_type"],
                record_iterable=(
                    [rt["Id"], rt["DeveloperName"], rt.get("IsPersonType", False)]
                    for rt in result["records"]
                ),
            )

    @contextmanager
    def _temp_database_url(self):
        with tempfile.TemporaryDirectory() as t:
            tempdb = Path(t) / "temp_db.db"

            self.logger.debug(f"Using temporary database {tempdb}")
            database_url = f"sqlite:///{tempdb}"
            yield database_url

    def _database_url(self):
        database_url = self.options.get("database_url")
        if database_url:
            return nullcontext(enter_result=database_url)
        else:
            return self._temp_database_url()

    def _id_generator_for_object(self, sobject: str):
        if sobject not in self._id_generators:

            def _generate_ids():
                counter = 0
                while True:
                    yield f"{sobject}-{counter}"
                    counter += 1

            self._id_generators[sobject] = _generate_ids()

        return self._id_generators[sobject]

    def _update_column(
        self, *, source_model, target_model, key_field, join_field, target_field
    ):
        key_attr = getattr(source_model, key_field)
        join_attr = getattr(target_model, join_field)
        target_attr = getattr(target_model, target_field)

        id_column = inspect(source_model).primary_key[0].name

        try:
            self.session.query(source_model).filter(
                key_attr.isnot(None), key_attr == join_attr
            ).update({key_attr: target_attr}, synchronize_session=False)
        except NotImplementedError:
            # Some databases, such as SQLite, don't support multitable update
            # TODO: review memory consumption of this routine.
            mappings = []
            for row, lookup_id in self.session.query(source_model, target_attr).join(
                target_model, key_attr == join_attr
            ):
                mappings.append(
                    {id_column: getattr(row, id_column), key_field: lookup_id}
                )
            self.session.bulk_update_mappings(source_model, mappings)

    def _update_sf_id_column(self, model, key_field):
        self._update_column(
            source_model=model,
            target_model=self.models[self.ID_TABLE_NAME],
            key_field=key_field,
            join_field="sf_id",
            target_field="id",
        )

    def _is_autopk_database(self):
        # If the type of the Id column on a mapping is INTEGER,
        # this is an autopk database.

        mapping = self.mapping.values()[0]
        id_field = mapping.fields["Id"]
        return isinstance(getattr(self.models[mapping.table], id_field).type, Integer)


def create_table(mapping, metadata) -> Table:
    """Given a mapping data structure (from mapping.yml) and SQLAlchemy
    metadata, create a table matching the mapping.

    Mapping should be a MappingStep instance"""

    fields = []
    # _handle_primary_key(mapping, fields)
    id_column = mapping.fields["Id"]  # Guaranteed to be present by mapping parser.
    fields.append(Column(id_column, Unicode(255), primary_key=True))

    # make a field list to create
    # for field, db in mapping.get_complete_field_map().items():
    for field, db in zip(
        mapping.get_extract_field_list(), mapping.get_database_column_list()
    ).items():
        if field == "Id":
            continue

        fields.append(Column(db, Unicode(255)))

    if mapping.record_type:
        fields.append(Column("record_type", Unicode(255)))
    return create_table_if_needed(mapping.table, metadata, fields)


def create_table_if_needed(tablename, metadata, fields: T.List[Column]) -> Table:
    t = Table(tablename, metadata, *fields)
    inspector = inspect(metadata.bind)
    if inspector.has_table(tablename):
        raise BulkDataException(f"Table already exists: {tablename}")
    t.create(metadata.bind)
    return t


def generate_batches(num_records, batch_size):
    """Generate batch size list for splitting a number of tasks into batch jobs.

    Given a number of records to split up, and a batch size, generate a
    stream of batchsize, index pairs"""
    num_batches, left_over = divmod(num_records, batch_size)
    if left_over:
        num_batches += 1  # need an extra batch for the clean-up
    for i in range(0, num_batches):
        is_last_batch = i == num_batches - 1
        if is_last_batch and left_over:
            batch_size = left_over
        if batch_size > 0:
            yield batch_size, i, num_batches


class RowErrorChecker:
    def __init__(self, logger, ignore_row_errors, row_warning_limit):
        self.logger = logger
        self.ignore_row_errors = ignore_row_errors
        self.row_warning_limit = row_warning_limit
        self.row_error_count = 0

    def check_for_row_error(self, result, row_id):
        if not result.success:
            msg = f"Error on record with id {row_id}: {result.error}"
            if self.ignore_row_errors:
                if self.row_error_count < self.row_warning_limit:
                    self.logger.warning(msg)
                elif self.row_error_count == self.row_warning_limit:
                    self.logger.warning("Further warnings suppressed")
                self.row_error_count += 1
                return self.row_error_count
            else:
                raise BulkDataException(msg)


def consume(iterator):
    """Consume an iterator for its side effects.

    Simplified from the function in https://docs.python.org/3/library/itertools.html
    """
    collections.deque(iterator, maxlen=0)


def sql_bulk_insert_from_records(
    *,
    connection: Connection,
    table: Table,
    columns: T.Tuple[str],
    record_iterable: T.Iterable,
) -> None:
    """Persist records from the given generator into the local database."""
    consume(
        sql_bulk_insert_from_records_incremental(
            connection=connection,
            table=table,
            columns=columns,
            record_iterable=record_iterable,
        )
    )


def sql_bulk_insert_from_records_incremental(
    *,
    connection: Connection,
    table: Table,
    columns: T.Tuple[str],
    record_iterable: T.Iterable,
):
    """Generator that persists batches of records from the given generator into the local database

    Yields after every batch."""
    dict_iterable = (dict(zip(columns, row)) for row in record_iterable)
    for group in iterate_in_chunks(10000, dict_iterable):
        with connection.begin():
            connection.execute(table.insert(), group)
        # self.session.flush()  -- Did this line do anything?
        yield


def sf_query_to_table(
    *,
    table: Table,
    metadata: MetaData,
    connection: Connection,
    sobject: str,
    fields: T.List[str],
    **queryargs,
) -> Table:
    """Cache data from Salesforce in a SQL Alchemy Table."""
    from cumulusci.tasks.bulkdata.step import DataOperationStatus, get_query_operation

    qs = get_query_operation(sobject=sobject, fields=fields, **queryargs)
    qs.query()
    if qs.job_result.status is not DataOperationStatus.SUCCESS:  # pragma: no cover
        raise BulkDataException(
            f"Unable to query records for {sobject}: {','.join(qs.job_result.job_errors)}"
        )
    results = qs.get_results()

    sql_bulk_insert_from_records(
        connection=connection,
        table=table,
        columns=tuple(fields),
        record_iterable=results,
    )
    return table
