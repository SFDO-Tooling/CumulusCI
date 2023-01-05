from itertools import chain
from logging import Logger
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Set

import yaml

from cumulusci.salesforce_api.org_schema import Filters, get_org_schema
from cumulusci.salesforce_api.org_schema_models import Field
from cumulusci.tasks.bulkdata.mapping_parser import CaseInsensitiveDict
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask
from cumulusci.utils import snake_to_camel
from cumulusci.utils.collections import OrderedSet
from cumulusci.utils.database.database_context import DatabaseContext

# It would be nice to be able to convert with a mapping file and no org
# But it gets messy, especially for old-style mapping files with
# table names, field names and lookup names that are different between
# SQL and Salesforce.
# Maybe we should have a task to update old-style mapping files to new-style


class ConvertDatasetToRecipe(BaseSalesforceApiTask):
    task_options = {
        "recipe": {"description": "Recipe to be output.", "required": True},
        "database_url": {
            "description": "Dataset to convert in db format. Do not specify if you also specified `sql_path`",
            "required": False,
        },
        "sql_path": {
            "description": "Dataset to convert in SQL format. Do not specify if you also specified `database_url`",
            "required": False,
        },
    }

    def _validate_options(self):
        ...  # TODO

    def _run_task(self):
        db = self.db_from_options(self.options)

        recipe_path = self.options.get("recipe")
        assert recipe_path
        recipe = SnowfakeryRecipeGenerator(Path(recipe_path))
        schema_context = get_org_schema(
            self.sf,
            self.org_config,
            include_counts=False,
            filters=[Filters.extractable, Filters.createable],
        )

        with db, schema_context as schema:
            self.tables_to_snowfakery(db, schema, recipe)
        recipe.save()
        self.logger.info(f"Wrote {recipe_path}")
        self.return_values = {"recipe": recipe_path}
        return self.return_values

    def tables_to_snowfakery(self, db, schema, recipe):
        tables = sorted(
            tablename
            for tablename in db.tables
            if not tablename.endswith("rt_mapping") and tablename in schema.keys()
        )

        used_nicknames = set()
        for tablename in tables:
            namefields = namefields_for_sobject(
                schema[tablename].fields, db.tables[tablename].columns.keys()
            )

            rows = db.rows_for(tablename)
            for row in rows:
                n = nickname_for_row(tablename, dict(row), used_nicknames, namefields)
                recipe.nicknames[(tablename, str(row["id"]))] = n
                used_nicknames.add(n)

        for tablename in tables:
            self.logger.info(tablename)
            sql_table = db.tables[tablename]
            schema_table = schema[tablename]
            field_name_converter = FieldNameConverter(
                tuple(sql_table.columns.keys()),
                tuple(schema_table.fields.keys()),
                self.logger,
            )
            references = CaseInsensitiveDict(
                {
                    f.name: f.referenceTo
                    for f in schema_table.fields.values()
                    if f.referenceTo
                }
            )
            rows = db.rows_for(tablename)

            for row in rows:
                canonical_row = field_name_converter.canonicalize_field_names(dict(row))
                values = self.convert_row_values(
                    tablename, canonical_row, references, recipe.nicknames
                )
                id_ = str(row["id"]) if row["id"] else None
                recipe.add_template(tablename, values, id_=id_)

    def db_from_options(self, options):
        if database_url := options.get("database_url"):
            return DatabaseContext.from_database_url(database_url)
        elif sql_path := options.get("sql_path"):
            return DatabaseContext.from_sql_file(Path(sql_path))
        assert False, "Should be unreachable"  # pragma: no cover

    def convert_row_values(
        self, tablename: str, row, references, nicknames: dict
    ) -> Dict[str, object]:
        ret = {
            str(field_name): self.cleanup_field(
                tablename, field_name, value, references.get(field_name, ()), nicknames
            )
            for field_name, value in row.items()
            if field_name.lower() != "id"
        }
        return {k: v for k, v in ret.items() if v}

    def cleanup_field(
        self, sobject, field_name, field_value, references: Sequence, nicknames: dict
    ):
        if field_value in ("", None):
            return None
        elif references:
            lookup_key = (references[0], str(field_value))
            if nickname := nicknames.get(lookup_key):
                return {"reference": nickname}
            else:
                if nicknames.get(lookup_key) is not False:
                    nicknames[lookup_key] = False
                    print(
                        f"Cannot find record for {(references[0], str(field_value))} for {sobject}.{field_name}"
                    )

        return field_value


class FieldNameConverter:
    def __init__(
        self, sql_fields: Sequence[str], sobject_fields: Sequence[str], logger: Logger
    ):
        self.field_name_mapping = self._build_field_name_mapping(
            sql_fields, sobject_fields, logger
        )

    @staticmethod
    def _build_field_name_mapping(
        sql_fields: Sequence[str], sobject_fields: Sequence[str], logger: Logger
    ) -> Dict:
        real_names = CaseInsensitiveDict(zip(sobject_fields, sobject_fields))

        def salesforce_ize_name(orig):
            return "__".join(snake_to_camel(part) for part in orig.split("__"))

        def canonicalize(orig):
            if new := real_names.get(orig):
                return new
            elif new := real_names.get(salesforce_ize_name(orig)):
                return new
            return None

        mapping = {original: canonicalize(original) for original in sql_fields}
        for orig, new in list(mapping.items()):
            if new is None:
                mapping[orig] = orig
                logger.warning(f"Field name cannot be found in schema {orig}")

        return mapping

    def canonicalize_field_names(self, row: Mapping):
        mappings = self.field_name_mapping
        return {mappings[k]: v for k, v in row.items()}


def namefields_for_sobject(
    schema_fields: Mapping[str, Field], table_fields: Sequence[str]
) -> Sequence[str]:
    explicitNameFields = [
        str(field.name) for field in schema_fields.values() if field.nameField
    ]
    knownNameFields = [
        str(fieldname) for fieldname in NAME_FIELDS if fieldname in schema_fields.keys()
    ]
    likelyNameFields = [
        str(field.name)
        for field in schema_fields.values()
        if field.name.endswith("Name") or field.name.endswith("Number")
    ]
    # dict instead of set to maintain order
    unified = {
        field: None
        for field in chain(explicitNameFields, knownNameFields, likelyNameFields)
        if field in table_fields
    }
    unified["id"] = None
    return tuple(unified.keys())


def nickname_for_row(
    tablename: str, row: Mapping, used_nicknames: Set, namefields: Sequence[str]
):
    nickname_parts = [row[fieldname] for fieldname in namefields if row[fieldname]]
    nickfield = nickname_parts.pop(0)
    proposed_name = f"{tablename}-{nickfield}"
    while proposed_name in used_nicknames:
        assert nickname_parts
        proposed_name += f"-{nickname_parts.pop(0)}"
    return proposed_name


class SnowfakeryRecipeGenerator:
    def __init__(self, recipe: Path):
        recipe.write_text("X")  # test writability
        self.recipe = recipe
        self.data = []
        self.nicknames = {}

    def add_template(
        self,
        sobject: str,
        fields: Dict[str, object],
        nickname: Optional[str] = None,
        id_: Optional[str] = None,
    ):
        data: Dict[str, object] = {"object": sobject}
        assert not nickname and id_, "Nickname or id, not both"
        if id_:
            nickname = self.nicknames[(sobject, id_)]

        if nickname:
            data["nickname"] = nickname
        data["fields"] = fields
        self.data.append(data)

    def save(self):
        with open(self.recipe, "w") as f:
            self.data.sort(key=lambda v: v["nickname"])
            yaml.safe_dump(self.data, f, indent=1, sort_keys=False)


NAME_FIELDS = OrderedSet(
    (
        "ApiName",
        "DeveloperName",
        "Name",
        "LastName",
        "ChangeRequestNumber",
        "LineItemNumber",
        "Domain",
        "FunctionName",
        "OrderItemNumber",
        "WorkPlanTemplateEntryNumber",
        "CaseNumber",
        "LocalPart",
        "EventRelayNumber",
        "ProductWarrantyTermNumber",
        "WarrantyTermName",
        "MasterLabel",
        "AssetRelationshipNumber",
        "IncidentNumber",
        "FirstName",
        "ProblemNumber",
        "DocumentRecipient",
        "TestSuiteName",
        "AssociatedLocationNumber",
        "FriendlyName",
        "Title",
        "Subject",
        "ProcessExceptionNumber",
        "SolutionName",
        "OrderNumber",
        "WorkOrderNumber",
        "ResponseShortText",
        "AssetWarrantyNumber",
        "ContractNumber",
        "Label",
    )
)
