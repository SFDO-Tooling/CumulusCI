import itertools
import re
import typing as T

from cumulusci.salesforce_api.org_schema import Schema

from .extract_yml import ExtractDeclaration, SimplifiedExtractDeclaration


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


def calculate_hard_dependencies(
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
                dependencies.setdefault(source_sfobject, []).append(
                    Dependency(source_sfobject, target, field_name)
                )

    return dependencies
