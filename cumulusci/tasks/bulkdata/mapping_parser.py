from datetime import date
from typing import Dict, List, Union, IO, Optional, Any, Callable, Mapping
from logging import getLogger
from pathlib import Path
from requests.structures import CaseInsensitiveDict as RequestsCaseInsensitiveDict

from pydantic import Field, validator, root_validator, ValidationError

from cumulusci.core.config.OrgConfig import OrgConfig
from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.step import DataOperationType, DataApi
from cumulusci.tasks.bulkdata.dates import iso_to_date
from cumulusci.utils.yaml.model_parser import CCIDictModel
from cumulusci.utils import convert_to_snake_case

from typing_extensions import Literal

logger = getLogger(__name__)


class CaseInsensitiveDict(RequestsCaseInsensitiveDict):
    def __init__(self, *args, **kwargs):
        self._canonical_keys = {}
        super().__init__(*args, **kwargs)

    def canonical_key(self, name):
        return self._canonical_keys[name.lower()]

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._canonical_keys[key.lower()] = key


class MappingLookup(CCIDictModel):
    "Lookup relationship between two tables."
    table: Optional[str] = None
    key_field: Optional[str] = None
    value_field: Optional[str] = None
    join_field: Optional[str] = None
    after: Optional[str] = None
    aliased_table: Optional[Any] = None
    name: Optional[str] = None  # populated by parent

    def get_lookup_key_field(self, model=None):
        "Find the field name for this lookup."
        guesses = []
        if self.get("key_field"):
            guesses.append(self.get("key_field"))

        guesses.append(self.name)

        if not model:
            return guesses[0]

        # CCI used snake_case until mid-2020.
        # At some point this code could probably be simplified.
        snake_cased_guesses = list(map(convert_to_snake_case, guesses))
        guesses = guesses + snake_cased_guesses
        for guess in guesses:
            if hasattr(model, guess):
                return guess
        raise KeyError(
            f"Could not find a key field for {self.name}.\n"
            + f"Tried {', '.join(guesses)}"
        )


class MappingStep(CCIDictModel):
    "Step in a load or extract process"
    sf_object: str
    table: Optional[str] = None
    fields_: Dict[str, str] = Field({}, alias="fields")
    lookups: Dict[str, MappingLookup] = {}
    static: Dict[str, str] = {}
    filters: List[str] = []
    action: DataOperationType = DataOperationType.INSERT
    api: DataApi = DataApi.SMART
    batch_size: int = 200
    record_type: Optional[str] = None  # should be discussed and probably deprecated
    bulk_mode: Optional[
        Literal["Serial", "Parallel"]
    ] = None  # default should come from task options
    anchor_date: Optional[str] = None

    def get_destination_record_type_table(self):
        """Returns the name of the record type table for the target org."""
        return f"{self.sf_object}_rt_target_mapping"

    def get_source_record_type_table(self):
        """Returns the name of the record type table for the source org."""
        return f"{self.sf_object}_rt_mapping"

    def get_fields_by_type(self, field_type: str, org_config: OrgConfig):
        describe = getattr(org_config.salesforce_client, self.sf_object).describe()
        describe = CaseInsensitiveDict(
            {entry["name"]: entry for entry in describe["fields"]}
        )

        return [f for f in describe if describe[f]["type"] == field_type]

    def get_load_field_list(self):
        """Build a flat list of fields for the given mapping,
        including fields, lookups, and statics."""
        # Build the list of fields to import
        fields = ["Id"]
        fields.extend([f for f in self.fields.keys() if f != "Id"])

        # Don't include lookups with an `after:` spec (dependent lookups)
        fields.extend([f for f in self.lookups if not self.lookups[f].after])
        fields.extend(self.static.keys())

        # If we're using Record Type mapping, `RecordTypeId` goes at the end.
        if "RecordTypeId" in fields:
            fields.remove("RecordTypeId")

        if self.action is DataOperationType.INSERT and "Id" in fields:
            fields.remove("Id")
        if self.record_type or "RecordTypeId" in self.fields:
            fields.append("RecordTypeId")

        return fields

    def get_extract_field_list(self):
        """Build a flat list of Salesforce fields for the given mapping, including fields, lookups, and record types,
        for an extraction operation.
        The Id field is guaranteed to come first in the list."""

        # Build the list of fields to import
        fields = ["Id"]
        fields.extend([f for f in self.fields.keys() if f != "Id"])
        fields.extend(self.lookups.keys())

        # If we're using Record Type mapping, `RecordTypeId` goes at the end.
        # This makes it easier to manage the relationship with database columns.
        if "RecordTypeId" in fields:
            fields.remove("RecordTypeId")

        if "RecordTypeId" in self.fields:
            fields.append("RecordTypeId")

        return fields

    def get_database_column_list(self):
        columns = [
            self.fields.get(f) or self.lookups.get(f).get_lookup_key_field()
            for f in self.get_extract_field_list()
        ]
        # The fixed Record Type is added statically during extract.
        if self.record_type:
            columns.append("record_type")

        return columns

    def get_relative_date_context(self, org_config: OrgConfig):
        """Return a tuple of (list of date field indices,
        list of datetime field indices, current date)."""
        # Note: because of how we order fields (regular fields come first),
        # it's irrelevant whether we use `extract` or `load` field list.
        fields = self.get_extract_field_list()

        date_fields = [
            fields.index(f)
            for f in self.get_fields_by_type("date", org_config)
            if f in self.fields
        ]
        date_time_fields = [
            fields.index(f)
            for f in self.get_fields_by_type("datetime", org_config)
            if f in self.fields
        ]

        return (date_fields, date_time_fields, date.today())

    @validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v):
        assert v <= 200 and v > 0

    @validator("anchor_date")
    @classmethod
    def validate_anchor_date(cls, v):
        return iso_to_date(v)

    @validator("record_type")
    @classmethod
    def record_type_is_deprecated(cls, v):
        logger.warning(
            "record_type is deprecated. Just supply a RecordTypeId column declaration and it will be inferred"
        )
        return v

    @validator("fields_", pre=True)
    @classmethod
    def standardize_fields_to_dict(cls, values):
        if values is None:
            values = {}
        if type(values) is list:
            return {elem: elem for elem in values}

        if "Id" not in values:
            values["Id"] = "sf_id"

        return values

    @validator("lookups")
    @classmethod
    def lookups_deprecated(cls, v):
        logger.warning(
            "The lookups: key is deprecated. We recommend moving all lookups into fields: and recapturing data sets."
        )

        return v

    @root_validator
    @classmethod
    def set_default_table(cls, values):
        """Automatically populate the `table` key with `sf_object`, if not present."""
        if values["table"] is None:
            values["table"] = values.get("sf_object")

        return values

    @root_validator  # not really a validator, more like a post-processor
    @classmethod
    def fixup_lookup_names(cls, v):
        "Allow lookup objects to know the key they were attached to in the mapping file."
        for name, lookup in v["lookups"].items():
            lookup.name = name
        return v

    def get_soql(self):
        """Return a SOQL query suitable for extracting data for this mapping."""
        soql = (
            f"SELECT {', '.join(self.get_extract_field_list())} FROM {self.sf_object}"
        )

        if self.record_type:
            soql += f" WHERE RecordType.DeveloperName = '{self.record_type}'"

        return soql

    @staticmethod
    def _is_injectable(element: str) -> bool:
        return element.count("__") == 1

    def _get_permission_type(self, operation: DataOperationType) -> str:
        if operation is DataOperationType.QUERY:
            return "queryable"
        if (
            operation is DataOperationType.INSERT
            and self.action is DataOperationType.UPDATE
        ):
            return "updateable"

        return "createable"

    def _check_object_permission(
        self, global_describe: Mapping, sobject: str, operation: DataOperationType
    ):
        assert sobject in global_describe
        perm = self._get_permission_type(operation)
        return global_describe[sobject][perm]

    def _check_field_permission(
        self, describe: Mapping, field: str, operation: DataOperationType
    ):
        perm = self._get_permission_type(operation)
        # Fields don't have "queryable" permission.
        return field in describe and (
            describe[field].get(perm) if perm in describe[field] else True
        )

    def _validate_field_dict(
        self,
        describe: CaseInsensitiveDict,
        field_dict: Dict[str, Any],
        inject: Optional[Callable[[str], str]],
        drop_missing: bool,
        data_operation_type: DataOperationType,
    ) -> bool:
        ret = True

        orig_fields = field_dict.copy()
        for f, entry in orig_fields.items():
            # Do we need to inject this field?
            if f.lower() == "id":
                del field_dict[f]
                field_dict["Id"] = entry
                continue

            if inject and self._is_injectable(f) and inject(f) not in orig_fields:
                if f in describe and inject(f) in describe:
                    logger.warning(
                        f"Both {self.sf_object}.{f} and {self.sf_object}.{inject(f)} are present in the target org. Using {f}."
                    )

                if f not in describe and inject(f) in describe:
                    field_dict[inject(f)] = entry
                    del field_dict[f]
                    f = inject(f)

            # Canonicalize the key's case
            try:
                new_name = describe.canonical_key(f)
            except KeyError:
                logger.warning(
                    f"Field {self.sf_object}.{f} does not exist or is not visible to the current user."
                )
            else:
                del field_dict[f]
                field_dict[new_name] = entry
                f = new_name

            # Do we have the right permissions for this field, or do we need to drop it?
            is_after_lookup = hasattr(field_dict[f], "after")
            if not self._check_field_permission(
                describe,
                f,
                data_operation_type
                if not is_after_lookup
                else DataOperationType.UPDATE,
            ):
                logger.warning(
                    f"Field {self.sf_object}.{f} is not present or does not have the correct permissions."
                )
                if drop_missing:
                    del field_dict[f]
                else:
                    ret = False

        return ret

    def _validate_sobject(
        self,
        global_describe: CaseInsensitiveDict,
        inject: Optional[Callable[[str], str]],
        data_operation_type: DataOperationType,
    ) -> bool:
        # Determine whether we need to inject our sObject.
        if inject and self._is_injectable(self.sf_object):
            if (
                self.sf_object in global_describe
                and inject(self.sf_object) in global_describe
            ):
                logger.warning(
                    f"Both {self.sf_object} and {inject(self.sf_object)} are present in the target org. Using {self.sf_object}."
                )

            if (
                self.sf_object not in global_describe
                and inject(self.sf_object) in global_describe
            ):
                self.sf_object = inject(self.sf_object)

        try:
            self.sf_object = global_describe.canonical_key(self.sf_object)
        except KeyError:
            logger.warning(
                f"sObject {self.sf_object} does not exist or is not visible to the current user."
            )
            return False

        # Validate our access to this sObject.
        if not self._check_object_permission(
            global_describe, self.sf_object, data_operation_type
        ):
            logger.warning(
                f"sObject {self.sf_object} does not have the correct permissions for {data_operation_type}."
            )
            return False

        return True

    def _move_lookups_from_fields(self, describe: CaseInsensitiveDict):
        new_lookups = []
        for f, detail in self.fields.items():
            field_desc = describe[f]
            if field_desc["type"] == "reference":
                new_lookups.append(f)

        for f in new_lookups:
            self.lookups[f] = MappingLookup(name=f)
            del self.fields[f]

    def validate_and_inject_namespace(
        self,
        org_config: OrgConfig,
        namespace: Optional[str],
        operation: DataOperationType,
        inject_namespaces: bool = False,
        drop_missing: bool = False,
    ):
        """Process the schema elements in this step.

        First, we inject the namespace into object and field names where applicable.
        Second, we validate that all fields are accessible by the running user with the
        correct permission level for this operation.
        Lastly, if drop_missing is True, we strip any fields that are not present (namespaced
        or otherwise) from the target org.

        Return True if this object should be processed. If drop_missing is True, a False return
        value indicates we should skip this object. If drop_missing is False, a False return
        value indicates that one or more schema elements couldn't be validated."""

        if namespace and inject_namespaces:

            def inject(element: str):
                return f"{namespace}__{element}"

        else:
            inject = None

        global_describe = CaseInsensitiveDict(
            {
                entry["name"]: entry
                for entry in org_config.salesforce_client.describe()["sobjects"]
            }
        )

        if not self._validate_sobject(global_describe, inject, operation):
            # Don't attempt to validate field permissions if the object doesn't exist.
            return False

        # Validate, inject, and drop (if configured) fields.
        # By this point, we know the attribute is valid.
        describe = getattr(org_config.salesforce_client, self.sf_object).describe()
        describe = CaseInsensitiveDict(
            {entry["name"]: entry for entry in describe["fields"]}
        )

        if not self._validate_field_dict(
            describe, self.fields, inject, drop_missing, operation
        ):
            return False

        # At this point we've canonicalized the entries in `fields`
        # Move any entries from `fields` that are lookup fields into
        # `lookups`, and synthesize MappingLookups for them.
        self._move_lookups_from_fields(describe)

        if not self._validate_field_dict(
            describe, self.lookups, inject, drop_missing, operation
        ):
            return False

        return True


class MappingSteps(CCIDictModel):
    "Mapping of named steps"
    __root__: Dict[str, MappingStep]


ValidationError = ValidationError  # export Pydantic's Validation Error under an alias


def parse_from_yaml(source: Union[str, Path, IO]) -> Dict:
    "Parse from a path, url, path-like or file-like"
    return MappingSteps.parse_from_yaml(source)


def _drop_schema(mapping: Dict, org_config: OrgConfig, should_continue: List[bool]):
    # Drop any steps with sObjects that are not present.
    for (include, step_name) in zip(should_continue, list(mapping.keys())):
        if not include:
            del mapping[step_name]

    # Remove any remaining lookups to dropped objects.
    for m in mapping.values():
        describe = getattr(org_config.salesforce_client, m.sf_object).describe()
        describe = {entry["name"]: entry for entry in describe["fields"]}

        tables = [step.table for step in mapping.values() if step.table]

        for field in list(m.lookups.keys()):
            lookup = m.lookups[field]
            if lookup.table not in tables:
                del m.lookups[field]

                # Make sure this didn't cause the operation to be invalid
                # by dropping a required field.
                if not describe[field]["nillable"]:
                    raise BulkDataException(
                        f"{m.sf_object}.{field} is a required field, but the target object "
                        f"{describe[field]['referenceTo']} was removed from the operation "
                        "due to missing permissions."
                    )


def _validate_table_references(
    mapping: Dict,
):
    tables = [step.table for step in mapping.values() if step.table]
    fail = False
    for m in mapping.values():
        for lookup in m.lookups.values():
            if lookup.table and lookup.table not in tables:
                fail = True
                logger.error(
                    f"The table {lookup.table}, specified for lookup {m.sf_object}.{lookup.name}, is not present in the mapping."
                )
                continue

    if fail:
        raise BulkDataException("Bad table references blocked the operation")


def _infer_and_validate_lookups(mapping: Dict, org_config: OrgConfig):
    sf_objects = [m.sf_object for m in mapping.values()]

    fail = False

    for idx, m in enumerate(mapping.values()):
        describe = CaseInsensitiveDict(
            {
                f["name"]: f
                for f in getattr(org_config.salesforce_client, m.sf_object).describe()[
                    "fields"
                ]
            }
        )

        for lookup in m.lookups.values():
            if lookup.after:
                # If configured by the user, skip.
                # TODO: do we need more validation here?
                continue

            field_describe = describe[lookup.name]
            target_objects = field_describe["referenceTo"]
            if len(target_objects) == 1:
                # This is a non-polymorphic lookup.
                try:
                    target_index = sf_objects.index(target_objects[0])
                except ValueError:
                    fail = True
                    logger.error(
                        f"The field {m.sf_object}.{lookup.name} looks up to {target_objects[0]}, which is not included in the operation"
                    )
                    continue

                if target_index > idx or target_index == idx:
                    # This is a non-polymorphic after step.
                    lookup.after = mapping.keys()[idx]
            else:
                # This is a polymorphic lookup.
                # Make sure that any lookup targets present in the operation precede this step.
                target_indices = [sf_objects.index(t) for t in target_objects]
                if not all([target_index < idx for target_index in target_indices]):
                    logger.error(
                        f"All included target objects ({','.join(target_objects)}) for the field {m.sf_object}.{lookup.name} "
                        f"must precede {m.sf_object} in the mapping."
                    )
                    fail = True
                    continue

    if fail:
        raise BulkDataException(
            "One or more relationship errors blocked the operation."
        )


def validate_and_inject_mapping(
    *,
    mapping: Dict,
    org_config: OrgConfig,
    namespace: str,
    data_operation: DataOperationType,
    inject_namespaces: bool,
    drop_missing: bool,
):
    # Validation and namespace injection
    should_continue = [
        m.validate_and_inject_namespace(
            org_config, namespace, data_operation, inject_namespaces, drop_missing
        )
        for m in mapping.values()
    ]

    if not drop_missing and not all(should_continue):
        raise BulkDataException("One or more permissions errors blocked the operation.")

    # Schema dropping
    if drop_missing:
        _drop_schema(mapping, org_config, should_continue)

    # Validate that `table` references, if present, are to included tables.
    _validate_table_references(mapping)

    # Synthesize `after` declarations and validate lookup references.
    _infer_and_validate_lookups(mapping, org_config)

    # If the org has person accounts enabled, add a field mapping to track "IsPersonAccount".
    # IsPersonAccount field values are used to properly load person account records.
    if (
        org_config.is_person_accounts_enabled
        and data_operation == DataOperationType.QUERY
    ):
        for step in mapping.values():
            if step.sf_object in ("Account", "Contact"):
                step.fields["IsPersonAccount"] = "IsPersonAccount"
