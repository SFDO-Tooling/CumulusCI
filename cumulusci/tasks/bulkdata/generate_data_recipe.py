import csv
import itertools
import logging
import re
import typing as T
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from sqlalchemy import MetaData, create_engine

from cumulusci.cli.runtime import CliRuntime
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.org_schema import Schema, get_org_schema
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask
from cumulusci.utils.http.multi_request import CompositeParallelSalesforce

from .extract import ExtractData
from .generate_data_recipe_utils.extract_yml import (
    ExtractDeclaration,
    ExtractRulesFile,
    SimplifiedExtractDeclaration,
)


class GenerateDataRecipe(BaseSalesforceApiTask):
    task_options = {}
    task_options = {
        "output_directory": {
            "description": "Where output CSV files and Snowfakery recipe (grammar)",
            "required": True,
        },
        "extract_rules": {
            "description": "A file containing declarations about what objects and fields "
            "to download and what API to use. (optional)",
            "required": False,
        },
    }

    def _run_task(self):
        self.output_directory = Path(self.options.get("output_directory", "datasets"))
        if not self.output_directory.exists():
            raise TaskOptionsError(
                f"Output directory does not exist: {self.output_directory}"
            )
        if self.options.get("extract_rules"):
            extract_rules_path = Path(self.options.get("extract_rules"))
            if not extract_rules_path.exists():
                raise TaskOptionsError("Rules file does not exist")

            self.extract_rules = ExtractRulesFile.parse_from_yaml(extract_rules_path)
            assert isinstance(self.extract_rules, list)
        else:
            self.extract_rules = [
                ExtractDeclaration(
                    sf_object="OBJECTS(POPULATED)", fields=["FIELDS(ALL)"]
                )
            ]

        recipe = export_data_and_snowfakery_recipe(
            self.sf,
            self.project_config,
            self.org_config,
            self.extract_rules,
            self.output_directory,
            self.logger,
        )
        self.logger.info(f"Created {recipe}")


SKIP_PATTERNS = (
    ".*permission.*",
    ".*use.*",
    ".*access.*",
    "group",
    ".*share",
    "NetworkUserHistoryRecent",
    "IdeaComment",
    "ContentDocumentLink",
    "OutgoingEmail",
    "OutgoingEmailRelation",
    "Vote",
)
SKIP_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in SKIP_PATTERNS]


def partition(pred, iterable):
    "Use a predicate to partition entries into false entries and true entries"
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = itertools.tee(iterable)
    return itertools.filterfalse(pred, t1), filter(pred, t2)


def simplify_sfobject_declarations(
    declarations, schema: Schema, populated_sobjects: list[str]
):
    """Generate a new list of declarations such that all sf_object patterns
    (like OBJECTS(CUSTOM)) have been resolved to specific names and defaults
    have been merged in."""
    simple_declarations, complex_declarations = partition(
        lambda d: d.complex_type, declarations
    )
    simple_declarations = list(simple_declarations)
    simple_declarations = (
        ExtractDeclaration.normalize_user_supplied_simple_declarations(
            simple_declarations, DEFAULT_DECLARATIONS
        )
    )
    simple_declarations = merge_complex_declarations_with_simple_declarations(
        simple_declarations, complex_declarations, schema, populated_sobjects
    )
    return simple_declarations


class Dependency(T.NamedTuple):
    table_name_from: str
    table_name_to: str
    field_name: str


def merge_complex_declarations_with_simple_declarations(
    simple_declarations: list[ExtractDeclaration],
    complex_declarations: list[ExtractDeclaration],
    schema: Schema,
    populated_sobjects: list[str],
) -> list[ExtractDeclaration]:
    simple_declarations = simple_declarations.copy()

    specific_sobject_decl_names = [obj.sf_object for obj in simple_declarations]
    complex_declarations = list(complex_declarations)

    simplified_declarations = [
        simplify_complex_sobject_declaration(decl, schema, populated_sobjects)
        for decl in complex_declarations
    ]
    for decl_set in simplified_declarations:
        for decl in decl_set:
            if decl.sf_object not in specific_sobject_decl_names and not any(
                pat.match(decl.sf_object.lower()) for pat in SKIP_PATTERNS
            ):
                simple_declarations.append(decl)

    return simple_declarations


def simplify_complex_sobject_declaration(
    decl: ExtractDeclaration, schema: Schema, populated_sobjects
):
    if decl.complex_type == "standard":

        def matches_obj(obj):
            return not obj.custom

    elif decl.complex_type == "custom":

        def matches_obj(obj):
            return obj.custom

    elif decl.complex_type == "all":

        def matches_obj(obj):
            return True

    elif decl.complex_type == "populated":

        def matches_obj(obj):
            return obj.name in populated_sobjects

    else:
        assert 0, decl.complex_type

    matching_objects = [obj["name"] for obj in schema.sobjects if matches_obj(obj)]
    decls = [
        synthesize_declaration_for_sobject(obj, decl.fields) for obj in matching_objects
    ]
    return decls


def expand_field_definitions(
    sobject_decl: ExtractDeclaration, schema_fields
) -> SimplifiedExtractDeclaration:
    simple_declarations, complex_declarations = partition(
        lambda d: "(" in d, sobject_decl.fields
    )
    declarations = list(simple_declarations)
    for c in complex_declarations:
        ctype = ExtractDeclaration.parse_field_complex_type(c)
        if not ctype:
            raise TypeError(f"Could not parse {c}")  # FIX THIS EXCEPTION

        if ctype == "standard":
            # find updateable standard fields
            declarations.extend(
                field.name
                for field in schema_fields.values()
                if field.createable and not field.custom
            )
        elif ctype == "custom":
            declarations.extend(
                field.name
                for field in schema_fields.values()
                if field.createable and field.custom
            )
        elif ctype == "required":
            # required fields are always exported
            pass
        elif ctype == "all":
            declarations.extend(
                field.name for field in schema_fields.values() if field.createable
            )
        else:
            raise NotImplementedError(type)
    declarations.extend(
        field.name
        for field in schema_fields.values()
        if (field.createable and not field.nillable and field.name not in declarations)
    )
    new_sobject_decl = dict(sobject_decl)
    del new_sobject_decl["fields_"]
    return SimplifiedExtractDeclaration(**new_sobject_decl, fields=declarations)


def flatten_declarations(
    declarations: list[ExtractDeclaration], schema: Schema, populated_sobjects
) -> list[SimplifiedExtractDeclaration]:
    merged_declarations = simplify_sfobject_declarations(
        declarations, schema, populated_sobjects
    )
    simplified_declarations = [
        expand_field_definitions(decl, schema[decl.sf_object].fields)
        for decl in merged_declarations
    ]

    return simplified_declarations


def object_template_from_decl(sf_object):
    for_each = {
        "var": "current_row",
        "value": {"Dataset.iterate": {"dataset": f"{sf_object}.csv"}},
    }

    return {
        "object": sf_object,
        "include": f"generated_fields_{sf_object}",
        "for_each": for_each,
    }


def macro_template_from_decl(decl):
    def as_lookup(field_name, target):
        return {
            "Dataset.object_reference": {
                "object": target,
                "id": "${{current_row.%s}}" % field_name,
            }
        }

    simple_fields = {
        field_name: "${{current_row.%s}}" % field_name for field_name in decl.fields
    }
    lookups = {
        field_name: as_lookup(field_name, target)
        for field_name, target in decl.lookups.items()
    }
    return {
        "macro": f"generated_fields_{decl.sf_object}",
        "fields": {**simple_fields, **lookups},
    }


def recipe_from_declarations(templates: list, static_data_filename):
    root = [
        {"plugin": "snowfakery.standard_plugins.datasets.Dataset"},
        {"include_file": static_data_filename},
    ]
    root.extend(templates)
    return root

    # relevant_sobjects = [sobject for sobject in sobjects if schema[sobject].createable]


def doit(export_declarations):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    directory = Path("/tmp/out")
    directory.mkdir(exist_ok=True)

    runtime = CliRuntime()
    _, org_config = runtime.get_org("qa")
    sf = get_simple_salesforce_connection(runtime.project_config, org_config)
    export_data_and_snowfakery_recipe(
        sf, runtime.project_config, org_config, export_declarations, directory, logger
    )
    print(directory)


def export_data_and_snowfakery_recipe(
    sf, project_config, org_config, export_declarations, directory, logger
) -> Path:
    with get_org_schema(sf, org_config) as schema:
        # constrain to populated sobjects to reduce wasted effort
        potential_objects = [
            obj.name for obj in schema.values() if obj.queryable and obj.createable
        ]
        populated_sobjects = find_populated_objects(sf, potential_objects)
        flattened_declarations = {
            decl.sf_object: decl
            for decl in flatten_declarations(
                export_declarations, schema, populated_sobjects
            )
        }
        finalized_declarations = {
            objname: flattened_declarations[objname]
            for objname in populated_sobjects
            if (objname in flattened_declarations)
        }

        extend_declarations_to_include_referenced_tables(finalized_declarations, schema)
        classify_and_filter_lookups(finalized_declarations, schema)

        extracted_objects = extract_objects(
            finalized_declarations.values(),
            schema,
            directory,
            project_config,
            org_config,
            logger,
        )
        recipe = directory / "sample.data_recipe.yml"
        write_recipe(finalized_declarations, extracted_objects, recipe)
        return recipe


def classify_and_filter_lookups(decls, schema: Schema):
    """Move lookups into their own field, if they reference a table we're including"""
    referenceable_tables = [decl.sf_object for decl in decls.values()]
    for decl in decls.values():
        sobject_schema_info = schema[decl.sf_object]
        fields, lookups_and_targets = fields_and_lookups_for_decl(
            decl, sobject_schema_info, referenceable_tables
        )
        decl.fields = list(fields)
        decl.lookups = dict(lookups_and_targets)


def write_recipe(finalized_declarations, extracted_objects, filename):
    static_data_filename = Path(
        str(filename).replace(
            "sample.data_recipe.yml", "sample_generated.data_recipe.yml"
        )
    )
    macro_templates = [
        macro_template_from_decl(finalized_declarations[sf_object])
        for sf_object in extracted_objects
    ]

    with open(static_data_filename, "w") as file:
        generated_file = macro_templates
        yaml.dump(generated_file, file, sort_keys=False)

    including_templates = [
        object_template_from_decl(sf_object) for sf_object in extracted_objects
    ]

    recipe = recipe_from_declarations(
        including_templates, "sample_generated.data_recipe.yml"
    )
    with open(filename, "w") as file:
        yaml.dump(recipe, file, sort_keys=False)


def find_populated_objects(sf, objs):
    with CompositeParallelSalesforce(sf, max_workers=8, chunk_size=5) as cpsf:
        responses, errors = cpsf.do_composite_requests(
            (
                {
                    "method": "GET",
                    "url": f"/services/data/v{sf.sf_version}/query/?q=select count() from {obj}",
                    "referenceId": f"ref{obj}",
                }
                for obj in objs
                if not any(pat.match(obj) for pat in SKIP_PATTERNS)
            )
        )
        from pprint import pprint

        errors = list(errors)
        if errors:
            pprint(("Errors", list(errors)))
        errors, successes = partition(
            lambda response: response["httpStatusCode"] == 200, responses
        )
        errors = list(errors)
        if errors:
            pprint(("Errors", list(errors)))

    non_empty = (
        response for response in successes if response["body"]["totalSize"] > 0
    )
    return [response["referenceId"].removeprefix("ref") for response in non_empty]


def fields_and_lookups_for_decl(decl, sobject_schema_info, referenceable_tables):
    simple_fields, lookups = partition(
        lambda field_name: sobject_schema_info.fields[field_name].referenceTo,
        decl.fields,
    )

    def target_table(field_info):
        if len(field_info.referenceTo) == 1:
            target = field_info.referenceTo[0]
        else:
            target = "Polymorphic lookups are not supported"
        return target

    lookups = list(lookups)

    lookups_and_targets = (
        (lookup, target_table(sobject_schema_info.fields[lookup])) for lookup in lookups
    )
    lookups_and_targets = (
        (lookup, table)
        for lookup, table in lookups_and_targets
        if table in referenceable_tables
    )
    return simple_fields, lookups_and_targets


def mapping_decl_for_extract_decl(
    decl: SimplifiedExtractDeclaration,
):
    lookups = {lookup: {"table": table} for lookup, table in decl.lookups.items()}
    mapping_dict = {
        "sf_object": decl.sf_object,
    }
    if decl.where:
        mapping_dict["soql_filter"] = decl.where
    mapping_dict["fields"] = decl.fields
    mapping_dict["lookups"] = lookups

    if mapping_dict.get("fields") or mapping_dict.get("lookups"):
        return (f"Insert {decl.sf_object}", mapping_dict)
    else:
        return None


def calculate_dependencies(
    decls: list[SimplifiedExtractDeclaration], schema: Schema
) -> dict:
    dependencies = {}
    for source_sfobject, source_decl in decls.items():
        for field_name in source_decl.fields:
            field_info = schema[source_sfobject].fields[field_name]
            references = field_info.referenceTo
            if len(references) == 1:
                target = references[0]
                if not field_info.nillable:
                    dependencies.setdefault(source_sfobject, []).append(
                        Dependency(source_sfobject, target, field_name)
                    )

    return dependencies


def mapping_file_from_declarations(
    decls: list[SimplifiedExtractDeclaration], schema: Schema
):
    assert decls is not None
    mappings = [mapping_decl_for_extract_decl(decl) for decl in decls]
    return dict(pair for pair in mappings if pair)


def extract_objects(
    simplified_extract_decls: list[SimplifiedExtractDeclaration],
    schema,
    directory: Path,
    project_config,
    org_config,
    logger,
) -> list[str]:
    extracted_objects = []
    mapping_declarations = mapping_file_from_declarations(
        simplified_extract_decls, schema
    )
    with TemporaryDirectory() as tempdir:
        database_url = run_extract_task(
            mapping_declarations,
            Path(tempdir),
            project_config,
            org_config,
            logger,
        )
        with db_values_from_db_url(database_url) as query_results:
            for tablename, query_result in query_results.items():
                csv_path = directory / f"{tablename}.csv"
                keys = query_result.keys()

                # don't make a CSV for empty query result
                first, query_result = peek_iter(query_result)
                if first is None:
                    continue

                with csv_path.open("w") as f:
                    csv_writer = csv.writer(f)
                    csv_writer.writerow(keys)
                    csv_writer.writerows(query_result)
                extracted_objects.append(tablename)

    return extracted_objects


def peek_iter(iterator, default=None) -> tuple[any, iter]:
    "Look ahead at the first item in an iterator"
    peek = next(iterator, default)
    return peek, itertools.chain([peek], iterator)


def synthesize_declaration_for_sobject(sf_object, fields):
    return DEFAULT_DECLARATIONS.get(sf_object) or SimplifiedExtractDeclaration(
        sf_object=sf_object, fields=fields
    )


def extend_declarations_to_include_referenced_tables(
    decls: dict[str, SimplifiedExtractDeclaration], schema: Schema
) -> dict[str, SimplifiedExtractDeclaration]:
    dependencies = calculate_dependencies(decls, schema)
    to_process = list(decls.values())

    while to_process:
        sf_object = to_process.pop()
        my_dependencies = dependencies.get(sf_object)
        if my_dependencies:
            for dep in my_dependencies:
                target_table = dep.to
                if target_table not in decls:
                    required_fields = [
                        field
                        for field in schema[target_table].fields
                        if not field.nillable
                    ]
                    decls[target_table] = synthesize_declaration_for_sobject(
                        sf_object, required_fields
                    )
                    to_process.append(decls[target_table])


def run_extract_task(
    mapping_declarations,
    tempdir: Path,
    project_config,
    org_config,
    logger,
) -> str:
    mapping_file = tempdir / "temp_mapping.yml"
    mapping_file.write_text(yaml.dump(mapping_declarations, sort_keys=False))
    p = Path("/tmp/mappping_for_debuggming.yml")
    p.write_text(yaml.dump(mapping_declarations, sort_keys=False))
    database_url = f"sqlite:///{tempdir}/temp_db.db"

    task_config = TaskConfig(
        {
            "options": {
                "mapping": mapping_file,
                "database_url": database_url,
            }
        },
    )

    task = ExtractData(project_config, task_config, org_config, logger=logger)
    task()
    return database_url


@contextmanager
def db_values_from_db_url(database_url: str):
    engine = create_engine(database_url)
    metadata = MetaData(engine)
    metadata.reflect()

    with engine.connect() as connection:
        values = {
            table_name: connection.execute(f"select * from {table.name}")
            for table_name, table in metadata.tables.items()
        }
        yield values


_DEFAULT_DECLARATIONS = [
    ExtractDeclaration(
        sf_object="Account", where="Name != 'Sample Account for Entitlements'"
    ),
    ExtractDeclaration(sf_object="BusinessHours", where="Name != 'Default'"),
    ExtractDeclaration(sf_object="ContentWorkspace", where="Name != 'Asset Library'"),
    ExtractDeclaration(sf_object="Entitlement", where="Name != 'Sample Entitlement'"),
    ExtractDeclaration(
        sf_object="FieldServiceMobileSettings",
        where="DeveloperName != 'Field_Service_Mobile_Settings'",
    ),
    ExtractDeclaration(
        sf_object="PricebookEntry",
        where="Pricebook2.Id != NULL and Pricebook2.Name != 'Standard Price Book'",
    ),
    ExtractDeclaration(sf_object="Pricebook2", where="Name != 'Standard Price Book'"),
    ExtractDeclaration(
        sf_object="WebLink", where="Name != 'ViewCampaignInfluenceReport'"
    ),
    ExtractDeclaration(
        sf_object="Folder",
        where="DeveloperName NOT IN ('SharedApp', 'EinsteinBotReports')",
    ),
    ExtractDeclaration(
        sf_object="MilestoneType",
        where="Name NOT IN ('First Response to Customer', 'Escalate Case', 'Close Case')",
    ),
    ExtractDeclaration(
        sf_object="WorkBadgeDefinition",
        where="Name NOT IN ('Thanks', 'You\\'re a RockStar!', 'Team Player',"
        "'All About Execution', 'Teacher', 'Top Performer', 'Hot Lead',"
        "'Key Win', 'Customer Hero', 'Competition Crusher',"
        "'Deal Maker', 'Gold Star')",
    ),
    ExtractDeclaration(
        sf_object="EmailTemplate",
        where="DeveloperName NOT IN ('CommunityLockoutEmailTemplate',"
        "'CommunityVerificationEmailTemplate',"
        "'CommunityChgEmailVerOldTemplate',"
        "'CommunityChgEmailVerNewTemplate',"
        "'CommunityDeviceActEmailTemplate',"
        "'CommunityWelcomeEmailTemplate',"
        "'CommunityChangePasswordEmailTemplate',"
        "'CommunityForgotPasswordEmailTemplate' )",
    ),
]
DEFAULT_DECLARATIONS = {decl.sf_object: decl for decl in _DEFAULT_DECLARATIONS}


# doit(
#     [
#         ExtractDeclaration(sf_object="Account", fields=["FIELDS(CUSTOM)"]),
#         ExtractDeclaration(sf_object="Contact", fields=["FIELDS(STANDARD)"]),
#         ExtractDeclaration(sf_object="OBJECTS(POPULATED)", fields=["FIELDS(STANDARD)"]),
#     ]
# )
