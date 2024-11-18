import typing as T
from functools import cached_property

from sqlalchemy import String, and_, func, text
from sqlalchemy.orm import Query, aliased
from sqlalchemy.sql import literal_column

from cumulusci.core.exceptions import BulkDataException

Criterion = T.Any
ID_TABLE_NAME = "cumulusci_id_table"


class LoadQueryExtender:
    """Class that transforms a load.py query with columns, filters, joins"""

    @cached_property
    def columns_to_add(*args) -> T.Optional[T.List]:
        return None

    @cached_property
    def filters_to_add(*args) -> T.Optional[T.List]:
        return None

    @cached_property
    def outerjoins_to_add(*args) -> T.Optional[T.List]:
        return None

    def __init__(self, mapping, metadata, model) -> None:
        self.mapping, self.metadata, self.model = mapping, metadata, model

    def add_columns(self, query: Query):
        """Add columns to the query"""
        if self.columns_to_add:
            query = query.add_columns(*self.columns_to_add)
        return query

    def add_filters(self, query: Query):
        """Add filters to the query"""
        if self.filters_to_add:
            return query.filter(*self.filters_to_add)
        return query

    def add_outerjoins(self, query: Query):
        """Add outer joins to the query"""
        if self.outerjoins_to_add:
            for table, condition in self.outerjoins_to_add:
                query = query.outerjoin(table, condition)
        return query


class AddLookupsToQuery(LoadQueryExtender):
    """Adds columns and joins relatinng to lookups"""

    def __init__(self, mapping, metadata, model, _old_format) -> None:
        super().__init__(mapping, metadata, model)
        self._old_format = _old_format
        self.lookups = [
            lookup for lookup in self.mapping.lookups.values() if not lookup.after
        ]

    @cached_property
    def columns_to_add(self):
        for lookup in self.lookups:
            lookup.aliased_table = aliased(self.metadata.tables[ID_TABLE_NAME])
        return [lookup.aliased_table.columns.sf_id for lookup in self.lookups]

    @cached_property
    def outerjoins_to_add(self):
        # Outer join with lookup ids table:
        # returns main obj even if lookup is null
        def join_for_lookup(lookup):
            key_field = lookup.get_lookup_key_field(self.model)
            value_column = getattr(self.model, key_field)
            if self._old_format:
                return (
                    lookup.aliased_table,
                    lookup.aliased_table.columns.id
                    == str(lookup.table) + "-" + func.cast(value_column, String),
                )
            else:
                return (
                    lookup.aliased_table,
                    lookup.aliased_table.columns.id == value_column,
                )

        return [join_for_lookup(lookup) for lookup in self.lookups]


class DynamicLookupQueryExtender(LoadQueryExtender):
    """Dynamically adds columns and joins for all fields in lookup tables, handling polymorphic lookups"""

    def __init__(
        self, mapping, all_mappings, metadata, model, _old_format: bool
    ) -> None:
        super().__init__(mapping, metadata, model)
        self._old_format = _old_format
        self.all_mappings = all_mappings
        self.lookups = [
            lookup for lookup in self.mapping.lookups.values() if not lookup.after
        ]

    @cached_property
    def columns_to_add(self):
        """Add all relevant fields from lookup tables directly without CASE, with support for polymorphic lookups."""
        columns = []
        for lookup in self.lookups:
            tables = lookup.table if isinstance(lookup.table, list) else [lookup.table]
            lookup.parent_tables = [
                aliased(
                    self.metadata.tables[table], name=f"{lookup.name}_{table}_alias"
                )
                for table in tables
            ]

            for parent_table, table_name in zip(lookup.parent_tables, tables):
                # Find the mapping step for this polymorphic type
                lookup_mapping_step = next(
                    (
                        step
                        for step in self.all_mappings.values()
                        if step.table == table_name
                    ),
                    None,
                )
                if lookup_mapping_step:
                    load_fields = lookup_mapping_step.fields.keys()
                    for field in load_fields:
                        if field in lookup_mapping_step.fields:
                            matching_column = next(
                                (
                                    col
                                    for col in parent_table.columns
                                    if col.name == lookup_mapping_step.fields[field]
                                )
                            )
                            columns.append(
                                matching_column.label(f"{parent_table.name}_{field}")
                            )
                        else:
                            # Append an empty string if the field is not present
                            columns.append(
                                literal_column("''").label(
                                    f"{parent_table.name}_{field}"
                                )
                            )
        return columns

    @cached_property
    def outerjoins_to_add(self):
        """Add outer joins for each lookup table directly, including handling for polymorphic lookups."""

        def join_for_lookup(lookup, parent_table):
            key_field = lookup.get_lookup_key_field(self.model)
            value_column = getattr(self.model, key_field)
            return (parent_table, parent_table.columns.id == value_column)

        joins = []
        for lookup in self.lookups:
            for parent_table in lookup.parent_tables:
                joins.append(join_for_lookup(lookup, parent_table))
        return joins


class AddRecordTypesToQuery(LoadQueryExtender):
    """Adds columns, joins and filters relatinng to recordtypes"""

    def __init__(self, mapping, metadata, model) -> None:
        super().__init__(mapping, metadata, model)
        if "RecordTypeId" in mapping.fields:
            self.rt_dest_table = metadata.tables[
                mapping.get_destination_record_type_table()
            ]
        else:
            self.rt_dest_table = None

    @cached_property
    def columns_to_add(self):
        if self.rt_dest_table is not None:
            return [self.rt_dest_table.columns.record_type_id]

    @cached_property
    def filters_to_add(self):
        if self.mapping.record_type and hasattr(self.model, "record_type"):
            return [self.model.record_type == self.mapping.record_type]

    @cached_property
    def outerjoins_to_add(self):

        if "RecordTypeId" in self.mapping.fields:
            try:
                rt_source_table = self.metadata.tables[
                    self.mapping.get_source_record_type_table()
                ]

            except KeyError as e:
                # For generate_and_load_from_yaml, In case of namespace_inject true, mapping table name doesn't have namespace added
                # We are checking for table_rt_mapping table
                try:
                    rt_source_table = self.metadata.tables[
                        f"{self.mapping.table}_rt_mapping"
                    ]

                except KeyError as f:

                    raise BulkDataException(
                        "A record type mapping table was not found in your dataset. "
                        f"Was it generated by extract_data? {e}",
                    ) from f

            rt_dest_table = self.metadata.tables[
                self.mapping.get_destination_record_type_table()
            ]

            # Check if 'is_person_type' column exists in rt_source_table.columns
            is_person_type_column = getattr(
                rt_source_table.columns, "is_person_type", None
            )
            # If it does not exist, set condition to True
            is_person_type_condition = (
                rt_dest_table.columns.is_person_type == is_person_type_column
                if is_person_type_column is not None
                else True
            )

            return [
                (
                    rt_source_table,
                    rt_source_table.columns.record_type_id
                    == getattr(self.model, self.mapping.fields["RecordTypeId"]),
                ),
                # Combination of IsPersonType and DeveloperName is unique
                (
                    rt_dest_table,
                    and_(
                        rt_dest_table.columns.developer_name
                        == rt_source_table.columns.developer_name,
                        is_person_type_condition,
                    ),
                ),
            ]


class AddMappingFiltersToQuery(LoadQueryExtender):
    """Adds filters relating to user-specified filters"""

    @cached_property
    def filters_to_add(self):
        if self.mapping.filters:
            return [text(f) for f in self.mapping.filters]


class AddPersonAccountsToQuery(LoadQueryExtender):
    """Add filters relating to Person accounts."""

    @cached_property
    def filters_to_add(self):
        """Filter out non-person account Contact records.
        Contact records for person accounts were already created by the system."""

        assert self.mapping.sf_object == "Contact"
        return [
            func.lower(self.model.__table__.columns.get("IsPersonAccount")) == "false"
        ]
