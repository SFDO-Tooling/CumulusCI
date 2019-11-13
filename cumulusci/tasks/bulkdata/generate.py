from collections import defaultdict

import click
import yaml

from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class GenerateMapping(BaseSalesforceApiTask):
    task_docs = """
    Generate a mapping file for use with the `extract_dataset` and `load_dataset` tasks.
    This task will examine the schema in the specified org and attempt to infer a
    mapping suitable for extracting data in packaged and custom objects as well as
    customized standard objects.

    Mappings must be serializable, and hence must resolve reference cycles - situations
    where Object A refers to B, and B also refers to A. Mapping generation will stop
    and request user input to resolve such cycles by identifying the correct load order.
    Alternately, specify the `ignore` option with the name of one of the
    lookup fields to suppress it and break the cycle. `ignore` can be specified as a list in
    `cumulusci.yml` or as a comma-separated string at the command line.

    In most cases, the mapping generated will need minor tweaking by the user. Note
    that the mapping omits features that are not currently well supported by the
    `extract_dataset` and `load_dataset` tasks, such as references to
    the `User` object.
    """

    task_options = {
        "path": {"description": "Location to write the mapping file", "required": True},
        "namespace_prefix": {"description": "The namespace prefix to use"},
        "ignore": {
            "description": "Object API names, or fields in Object.Field format, to ignore"
        },
    }

    core_fields = ["Id", "Name", "FirstName", "LastName"]

    def _init_options(self, kwargs):
        super(GenerateMapping, self)._init_options(kwargs)
        if "namespace_prefix" not in self.options:
            self.options["namespace_prefix"] = ""

        if self.options["namespace_prefix"] and not self.options[
            "namespace_prefix"
        ].endswith("__"):
            self.options["namespace_prefix"] += "__"

        self.options["ignore"] = process_list_arg(self.options.get("ignore", []))

    def _run_task(self):
        self.logger.info("Collecting sObject information")
        self._collect_objects()
        self._build_schema()
        filename = self.options["path"]
        self.logger.info(f"Creating mapping schema {filename}")
        self._build_mapping()
        with open(filename, "w") as f:
            yaml.dump(self.mapping, f, sort_keys=False)

    def _collect_objects(self):
        """Walk the global describe and identify the sObjects we need to include in a minimal operation."""
        self.mapping_objects = []

        # Cache the global describe, which we'll walk.
        self.global_describe = self.sf.describe()

        # First, we'll get a list of all objects that are either
        # (a) custom, no namespace
        # (b) custom, with our namespace
        # (c) not ours (standard or other package), but have fields with our namespace or no namespace
        self.describes = {}  # Cache per-object describes for efficiency
        for obj in self.global_describe["sobjects"]:
            self.describes[obj["name"]] = getattr(self.sf, obj["name"]).describe()
            if self._is_our_custom_api_name(obj["name"]) or self._has_our_custom_fields(
                self.describes[obj["name"]]
            ):
                if self._is_object_mappable(obj):
                    self.mapping_objects.append(obj["name"])

        # Add any objects that are required by our own,
        # meaning any object we are looking up to with a custom field,
        # or any master-detail parent of any included object.
        index = 0
        while index < len(self.mapping_objects):
            obj = self.mapping_objects[index]
            for field in self.describes[obj]["fields"]:
                if field["type"] == "reference":
                    if field["relationshipOrder"] == 1 or self._is_any_custom_api_name(
                        field["name"]
                    ):
                        self.mapping_objects.extend(
                            [
                                obj
                                for obj in field["referenceTo"]
                                if obj not in self.mapping_objects
                                and self._is_object_mappable(self.describes[obj])
                            ]
                        )

            index += 1

    def _build_schema(self):
        """Convert self.mapping_objects into a schema, including field details and interobject references,
        in self.schema and self.refs"""

        # Now, find all the fields we need to include.
        # For custom objects, we include all custom fields. This includes custom objects
        # that our package doesn't own.
        # For standard objects, we include all custom fields, all required standard fields,
        # and master-detail relationships. Required means createable and not nillable.
        # In all cases, ensure that RecordTypeId is included if and only if there are Record Types
        self.schema = {}
        self.refs = defaultdict(lambda: defaultdict(set))
        for obj in self.mapping_objects:
            self.schema[obj] = {}

            for field in self.describes[obj]["fields"]:
                if any(
                    [
                        self._is_any_custom_api_name(field["name"]),
                        self._is_core_field(field["name"]),
                        self._is_required_field(field),
                        self._is_lookup_to_included_object(field),
                    ]
                ):
                    if self._is_field_mappable(obj, field):
                        self.schema[obj][field["name"]] = field

                        if field["type"] == "reference":
                            for target in field["referenceTo"]:
                                # We've already vetted that this field is referencing
                                # included objects, via `_is_field_mappable()`
                                if target != obj:
                                    self.refs[obj][target].add(field["name"])
                if (
                    field["name"] == "RecordTypeId"
                    and len(self.describes[obj]["recordTypeInfos"]) > 1
                ):
                    # "Master" is included even if no RTs.
                    self.schema[obj][field["name"]] = field

    def _build_mapping(self):
        """Output self.schema in mapping file format by constructing a dict and serializing to YAML"""
        objs = set(self.schema.keys())
        stack = self._split_dependencies(objs, self.refs)

        field_sort = (
            lambda f: "  " + f
            if f == "Id"
            else (" " + f if f in self.core_fields else f)
        )

        self.mapping = {}
        for obj in stack:
            key = f"Insert {obj}"
            self.mapping[key] = {}
            self.mapping[key]["sf_object"] = f"{obj}"
            self.mapping[key]["table"] = f"{obj}"
            fields = []
            lookups = []
            for field in self.schema[obj].values():
                if field["type"] == "reference" and field["name"] != "RecordTypeId":
                    lookups.append(field["name"])
                else:
                    fields.append(field["name"])
            self.mapping[key]["fields"] = {}
            if fields:
                if "Id" not in fields:
                    fields.append("Id")
                fields.sort(key=field_sort)
                for field in fields:
                    self.mapping[key]["fields"][field] = (
                        field if field != "Id" else "sf_id"
                    )
            if lookups:
                lookups.sort(key=field_sort)
                self.mapping[key]["lookups"] = {}
                for field in lookups:
                    # First, determine what manner of lookup we have here.
                    referenceTo = self.schema[obj][field]["referenceTo"]

                    if len(referenceTo) > 1:  # Polymorphic lookup
                        self.logger.warning(
                            f"Field {obj}.{field} is a polymorphic lookup, which is not supported"
                        )
                    elif referenceTo[0] == obj:  # Self-lookup
                        self.mapping[key]["lookups"][field] = {
                            "table": referenceTo[0],
                            "after": key,
                        }
                    elif stack.index(referenceTo[0]) > stack.index(
                        obj
                    ):  # Dependent lookup
                        self.mapping[key]["lookups"][field] = {
                            "table": referenceTo[0],
                            "after": f"Insert {referenceTo[0]}",
                        }
                    else:  # Regular lookup
                        self.mapping[key]["lookups"][field] = {"table": referenceTo[0]}

    def _split_dependencies(self, objs, dependencies):
        """Attempt to flatten the object network into a sequence of load operations."""
        stack = []
        objs_remaining = objs.copy()

        # The structure of `dependencies` is:
        # key = object, value = set of objects it references.

        # Iterate through our list of objects
        # For each object, if it is not dependent on any other objects, place it at the end of the stack.
        # Once an object is placed in the stack, remove dependencies to it (they're satisfied)
        while objs_remaining:
            objs_without_deps = [
                obj
                for obj in objs_remaining
                if obj not in dependencies or not dependencies[obj]
            ]

            if not objs_without_deps:
                self.logger.info(
                    "CumulusCI needs help to complete the mapping; the schema contains reference cycles and unresolved dependencies."
                )
                self.logger.info(f"Mapped objects: {', '.join(stack)}")
                self.logger.info("Remaining objects:")
                for obj in objs_remaining:
                    self.logger.info(obj)
                    for other_obj in dependencies[obj]:
                        self.logger.info(
                            f"   references {other_obj} via: {', '.join(dependencies[obj][other_obj])}"
                        )
                choice = click.prompt(
                    "Which object should we load first?",
                    type=click.Choice(list(objs_remaining)),
                    show_choices=True,
                )
                objs_without_deps = [choice]

            for obj in objs_without_deps:
                stack.append(obj)

                # Remove all dependencies on this object (they're satisfied)
                for other_obj in dependencies:
                    if obj in dependencies.get(other_obj):
                        del dependencies[other_obj][obj]

                # Remove this object from our remaining set.
                objs_remaining.remove(obj)

        return stack

    def _is_any_custom_api_name(self, api_name):
        """True if the entity name is custom (including any package)."""
        return api_name.endswith("__c")

    def _is_our_custom_api_name(self, api_name):
        """True if the entity name is custom and has our namespace prefix (if we have one)
        or if the entity does not have a namespace"""
        return self._is_any_custom_api_name(api_name) and (
            (
                self.options["namespace_prefix"]
                and api_name.startswith(self.options["namespace_prefix"])
            )
            or api_name.count("__") == 1
        )

    def _is_core_field(self, api_name):
        """True if this field is one that we should always include regardless
        of other settings or field configuration, such as Contact.FirstName.
        DB-level required fields don't need to be so handled."""

        return api_name in self.core_fields

    def _is_object_mappable(self, obj):
        """True if this object is one we can map, meaning it's an sObject and not
        some other kind of entity, it's not ignored, it's Bulk API compatible,
        and it's not in a hard-coded list of entities we can't currently handle."""

        return not any(
            [
                obj["name"] in self.options["ignore"],  # User-specified exclusions
                obj["name"].endswith(
                    "ChangeEvent"
                ),  # Change Data Capture entities (which get custom fields)
                obj["name"].endswith("__mdt"),  # Custom Metadata Types (MDAPI only)
                obj["name"].endswith("__e"),  # Platform Events
                obj["customSetting"],  # Not Bulk API compatible
                obj["name"]  # Objects we can't or shouldn't load/save
                in [
                    "User",
                    "Group",
                    "LookedUpFromActivity",
                    "OpenActivity",
                    "Task",
                    "Event",
                    "ActivityHistory",
                ],
            ]
        )

    def _is_field_mappable(self, obj, field):
        """True if this field is one we can map, meaning it's not ignored,
        it's createable by the Bulk API, it's not a deprecated field,
        and it's not a type of reference we can't handle without special
        configuration (self-lookup or reference to objects not included
        in this operation)."""
        return not any(
            [
                f"{obj}.{field['name']}" in self.options["ignore"],  # User-ignored list
                "(Deprecated)" in field["label"],  # Deprecated managed fields
                field["type"] == "base64",  # No Bulk API support for base64 blob fields
                not field["createable"],  # Non-writeable fields
                field["type"] == "reference"  # Outside lookups
                and not self._are_lookup_targets_in_operation(field),
            ]
        )

    def _is_required_field(self, field):
        """True if the field is either database-level required or a master-detail
        relationship field."""
        return (field["createable"] and not field["nillable"]) or (
            field["type"] == "reference" and field["relationshipOrder"] == 1
        )

    def _has_our_custom_fields(self, obj):
        """True if the object is owned by us or contains any field owned by us."""
        return any(
            [self._is_our_custom_api_name(field["name"]) for field in obj["fields"]]
        )

    def _are_lookup_targets_in_operation(self, field):
        """True if this lookup field aims at objects we are already including (all targets
        must match, although we don't provide actual support for polymorphism)."""
        return all([f in self.mapping_objects for f in field["referenceTo"]])

    def _is_lookup_to_included_object(self, field):
        """True if this field is a lookup and also references only objects we are
        already including."""
        return field["type"] == "reference" and self._are_lookup_targets_in_operation(
            field
        )
