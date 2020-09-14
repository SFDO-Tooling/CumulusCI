from datetime import date, datetime
from typing import List

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy import Unicode
from sqlalchemy.orm import mapper

from cumulusci.core.config.OrgConfig import OrgConfig
from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.mapping_parser import MappingStep


class SqlAlchemyMixin:
    def _sql_bulk_insert_from_records(
        self, *, connection, table, columns, record_iterable
    ):
        """Persist records from the given generator into the local database."""
        table = self.metadata.tables[table]

        connection.execute(
            table.insert(), [dict(zip(columns, row)) for row in record_iterable]
        )

        self.session.flush()

    def _create_record_type_table(self, table_name):
        """Create a table to store mapping between Record Type Ids and Developer Names."""
        rt_map_model_name = f"{table_name}Model"
        self.models[table_name] = type(rt_map_model_name, (object,), {})
        rt_map_fields = [
            Column("record_type_id", Unicode(18), primary_key=True),
            Column("developer_name", Unicode(255)),
        ]
        rt_map_table = Table(table_name, self.metadata, *rt_map_fields)
        mapper(self.models[table_name], rt_map_table)

    def _extract_record_types(self, sobject, table, conn):
        """Query for Record Type information and persist it in the database."""
        self.logger.info(f"Extracting Record Types for {sobject}")
        query = (
            f"SELECT Id, DeveloperName FROM RecordType WHERE SObjectType='{sobject}'"
        )

        result = self.sf.query(query)

        if result["totalSize"]:
            self._sql_bulk_insert_from_records(
                connection=conn,
                table=table,
                columns=["record_type_id", "developer_name"],
                record_iterable=(
                    [rt["Id"], rt["DeveloperName"]] for rt in result["records"]
                ),
            )


def _handle_primary_key(mapping, fields):
    """Provide support for legacy mappings which used the OID as the pk but
    default to using an autoincrementing int pk and a separate sf_id column"""

    if mapping.get_oid_as_pk():
        id_column = mapping.fields["Id"]
        fields.append(Column(id_column, Unicode(255), primary_key=True))
    else:
        fields.append(Column("id", Integer(), primary_key=True, autoincrement=True))


def create_table(mapping, metadata):
    """Given a mapping data structure (from mapping.yml) and SQLAlchemy
    metadata, create a table matching the mapping.

    Mapping should be a MappingStep instance"""

    fields = []
    _handle_primary_key(mapping, fields)

    # make a field list to create
    for field, db in mapping.get_complete_field_map().items():
        if field == "Id":
            continue

        fields.append(Column(db, Unicode(255)))

    if mapping.record_type:
        fields.append(Column("record_type", Unicode(255)))
    t = Table(mapping.table, metadata, *fields)
    if t.exists():
        raise BulkDataException(f"Table already exists: {mapping.table}")
    return t


def generate_batches(num_records, batch_size):
    """Generate batch size list for splitting a number of tasks into batch jobs.

    Given a number of records to split up, and a batch size, generate a
    stream of batchsize, index pairs"""
    num_batches = (num_records // batch_size) + 1
    for i in range(0, num_batches):
        if i == num_batches - 1:  # last batch
            batch_size = num_records - (batch_size * i)  # leftovers
        if batch_size > 0:
            yield batch_size, i


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


def adjust_relative_dates(
    mapping: MappingStep, org_config: OrgConfig, record: List[str]
):
    """Convert specified date and time fields (in ISO format) relative to the present moment.
    If some date is 2020-07-30, anchor_date is 2020-07-23, and today's date is 2020-09-01,
    that date will become 2020-09-07 - the same position in the timeline relative to today."""

    fields = mapping.get_field_list()

    r = record.copy()

    date_fields = [
        fields.index(f)
        for f in mapping.get_fields_by_type("date", org_config)
        if f in mapping.fields
    ]
    date_time_fields = [
        fields.index(f)
        for f in mapping.get_fields_by_type("datetime", org_config)
        if f in mapping.fields
    ]

    for index in date_fields:
        if r[index]:
            this_date = date.today() + (
                date.fromisoformat(r[index]) - mapping.anchor_date
            )
            r[index] = this_date.isoformat()

    for index in date_time_fields:
        if r[index]:
            this_datetime = datetime.fromisoformat(r[index])
            this_date = date.today() + (this_datetime.date() - mapping.anchor_date)

            new_datetime = datetime.combine(this_date, this_datetime.time())
            r[index] = new_datetime.isoformat()

    return r
