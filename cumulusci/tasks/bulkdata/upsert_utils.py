import logging
import typing as T

from simple_salesforce import Salesforce
from sqlalchemy import Column, MetaData, Table, Unicode, UniqueConstraint, and_
from sqlalchemy.engine.base import Connection
from sqlalchemy.exc import IntegrityError

from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.mapping_parser import CaseInsensitiveDict, MappingStep
from cumulusci.tasks.bulkdata.query_transformers import LoadQueryExtender
from cumulusci.tasks.bulkdata.step import DataOperationType
from cumulusci.tasks.bulkdata.utils import create_table_if_needed, sf_query_to_table

logger = logging.getLogger(__name__)


def _create_empty_upsert_key_table(
    tablename, metadata, fieldnames: T.List[str]
) -> Table:
    """Create an empty table matching the upsert semantics"""
    fields = [Column(fieldname, Unicode(255)) for fieldname in fieldnames]

    # the data fields must be unique
    non_id_fields = [fieldname for fieldname in fieldnames if fieldname.lower() != "id"]
    assert len(fields) == len(non_id_fields) + 1
    fields.append(UniqueConstraint(*non_id_fields))

    return create_table_if_needed(tablename, metadata, fields)


def upsert_tablename_for_obj_and_keys(sf_object, keys):
    return f"upsert_{sf_object}_{'_'.join(keys)}"


def extract_upsert_key_data(
    sf_object: str,
    keys: tuple,
    context,
    metadata: MetaData,
    connection: Connection,
) -> Table:
    """Create a table with keys and IDs from Salesforce"""
    tablename = upsert_tablename_for_obj_and_keys(sf_object, keys)
    if "Id" not in (key.title() for key in keys):
        keys = ("Id",) + keys

    table = _create_empty_upsert_key_table(tablename, metadata, keys)

    soql_query = f"select {','.join(keys)} from {sf_object}"
    try:
        logger.info(f"Extracting records for upsert: `{soql_query}`")
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
    """Is this an upsert that Salesforce cannot do natively?"""
    # is this an upsert and one that Salesforce cannot do by itself?
    keys = mapping.update_key

    if len(keys) > 1:
        return True

    describe_data = mapping.describe_data(sf)

    key = keys[0]
    is_sf_builtin_key = (
        key == "Id"
        or describe_data[key]["externalId"]
        or describe_data[key]["idLookup"]
    )
    return not is_sf_builtin_key


class AddUpsertsToQuery(LoadQueryExtender):
    @property
    def columns_to_add(self):
        if self.mapping.action == DataOperationType.ETL_UPSERT:
            # We've retrieved IDs from the org, so include them.

            # If we treat "Id" as an "external_id_name" then it's
            # allowed to be sparse.
            tablename = upsert_tablename_for_obj_and_keys(
                self.mapping.sf_object, self.mapping.update_key
            )
            table = self.metadata.tables[tablename]
            id_column = table.columns["Id"]
            return [id_column]

    @property
    def outerjoins_to_add(self):
        if self.mapping.action == DataOperationType.ETL_UPSERT:
            tablename = upsert_tablename_for_obj_and_keys(
                self.mapping.sf_object, self.mapping.update_key
            )
            table = self.metadata.tables[tablename]
            return [self._make_outerjoin_for_upsert(table)]

    def _make_outerjoin_for_upsert(
        self,
        upsert_key_table: Table,
    ):
        """Make a query that joins user-provided data to Salesforce IDs"""
        update_data_table = self.metadata.tables[self.mapping.table]

        # normalize columns
        update_table_columns = CaseInsensitiveDict(update_data_table.c.items())

        join_on_clauses = [
            (upsert_key_table.columns[column_name] == update_table_columns[column_name])
            for column_name in self.mapping.update_key
        ]

        return (upsert_key_table, and_(*join_on_clauses))
