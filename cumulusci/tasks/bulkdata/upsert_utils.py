import typing as T

from simple_salesforce import Salesforce
from sqlalchemy import Column, MetaData, Table, Unicode, UniqueConstraint, and_, select
from sqlalchemy.engine.base import Connection
from sqlalchemy.exc import IntegrityError

from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.mapping_parser import MappingStep
from cumulusci.tasks.bulkdata.utils import sf_query_to_table


def select_for_upsert(
    *,
    mapping: MappingStep,
    metadata: MetaData,
    connection: Connection,
    context,
):
    """Pull data out of Salesforce for upsert matching

    1.  Pull the data out into a temp table
    2.  Make a query that joins the temp table to the
        user-provided table by the update_key
    """
    upsert_key_table = _create_upsert_key_table(
        mapping.sf_object, mapping.update_key, context, metadata, connection
    )
    upsert_query = _create_upsert_join_query(mapping, upsert_key_table, metadata)
    return upsert_query


def _create_upsert_join_query(
    mapping: MappingStep,
    upsert_key_table: Table,
    metadata: MetaData,
):
    """Make a query that joins user-provided data to Salesforce IDs"""
    update_data_table = metadata.tables[mapping.table]

    relevant_data_columns = (
        [update_data_table.c.id.label("_cci_local_id")]
        + [update_data_table.c[key] for key in mapping.fields]
        + [upsert_key_table.c.Id]
    )

    join_on_clauses = [
        (
            upsert_key_table.columns[column_name]
            == update_data_table.columns[column_name]
        )
        for column_name in mapping.update_key
    ]

    q = select(*relevant_data_columns)

    q = q.outerjoin(upsert_key_table, and_(*join_on_clauses))
    return q


def _create_empty_upsert_key_table(
    tablename, metadata, fieldnames: T.List[str]
) -> Table:
    """Create an empty table matching the upsert semantics"""
    if tablename not in metadata.tables:
        fields = [Column(fieldname, Unicode(255)) for fieldname in fieldnames]
        non_id_fields = [
            fieldname for fieldname in fieldnames if fieldname.lower() != "id"
        ]
        assert len(fields) == len(non_id_fields) + 1
        t = Table(tablename, metadata, *fields, UniqueConstraint(*non_id_fields))
        t.create(metadata.bind)
        return t


def _create_upsert_key_table(
    sf_object: str,
    keys: tuple,
    context,
    metadata: MetaData,
    connection: Connection,
) -> Table:
    """Create a table with keys and IDs from Salesforce"""
    tablename = f"upsert_{sf_object}_{'_'.join(keys)}"
    if "Id" not in (key.title() for key in keys):
        keys = ("Id",) + keys

    table = _create_empty_upsert_key_table(tablename, metadata, keys)

    soql_query = f"select {','.join(keys)} from {sf_object}"
    try:
        table = sf_query_to_table(
            table=table,
            sobject=sf_object,
            fields=keys,
            api_options={},
            context=context,
            query=soql_query,
            metadata=metadata,
            connection=connection,
        )
    except IntegrityError as e:
        message = str(e)
        if "UNIQUE constraint failed" not in message:  # pragma: no cover
            raise e
        raise BulkDataException(f"Duplicate values for upsert key:\n {e.params}") from e

    return table


def needs_etl_upsert(mapping: MappingStep, sf: Salesforce):
    """Is this an upsert that Salesforce cannot do nativvly?"""
    # is this an upsert and one that Salesforce cannot do by itself?
    keys = mapping.update_key

    # probably impossible to trigger this assertion, but just in case.
    assert len(keys) == 1, "UPSERT action should only have simple keys"

    describe_data = mapping.describe_data(sf)

    key = keys[0]
    is_sf_builtin_key = (
        key == "Id"
        or describe_data[key]["externalId"]
        or describe_data[key]["idLookup"]
    )
    return not is_sf_builtin_key
