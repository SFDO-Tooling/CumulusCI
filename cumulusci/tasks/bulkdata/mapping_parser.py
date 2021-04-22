from datetime import date
from typing import Dict, List, Union, IO, Optional, Any, Callable, Mapping
from logging import getLogger
from pathlib import Path
from enum import Enum

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
    table: str
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


SHOULD_REPORT_RECORD_TYPE_DEPRECATION = True


class BulkMode(Enum):
    serial = Serial = "Serial"
    parallel = Parallel = "Parallel"


ENUM_VALUES = {
    v.value.lower(): v.value
    for enum in [BulkMode, DataApi, DataOperationType]
    for v in enum.__members__.values()
}


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
    oid_as_pk: bool = False  # this one should be discussed and probably deprecated
    record_type: Optional[str] = None  # should be discussed and probably deprecated
    bulk_mode: Optional[
        Literal["Serial", "Parallel"]
    ] = None  # default should come from task options
    anchor_date: Optional[Union[str, date]] = None

    @validator("bulk_mode", "api", "action", pre=True)
    def case_normalize(cls, val):
        if isinstance(val, Enum):
            return val
        return ENUM_VALUES.get(val.lower())

    def get_oid_as_pk(self):
        """Returns True if using Salesforce Ids as primary keys."""
        return "Id" in self.fields

    def get_destination_record_type_table(self):
        """Returns the name of the record type table for the target org."""
        return f"{self.sf_object}_rt_target_mapping"

    def get_source_record_type_table(self):
        """Returns the name of the record type table for the source org."""
        return f"{self.sf_object}_rt_mapping"

    def get_sf_id_table(self):
        """Returns the name of the table for storing Salesforce Ids."""
        return f"{self.table}_sf_ids"

    def get_complete_field_map(self, include_id=False):
        """Return a field map that includes both `fields` and `lookups`.
        If include_id is True, add the Id field if not already present."""
        fields = {}

        if include_id and "Id" not in self.fields:
            fields["Id"] = "sf_id"

        fields.update(self.fields)
        fields.update(
            {
                lookup: self.lookups[lookup].get_lookup_key_field()
                for lookup in self.lookups
            }
        )

        return fields

    def get_fields_by_type(self, field_type: str, org_config: OrgConfig):
        describe = getattr(org_config.salesforce_client, self.sf_object).describe()
        describe = CaseInsensitiveDict(
            {entry["name"]: entry for entry in describe["fields"]}
        )

        return [f for f in describe if describe[f]["type"] == field_type]

    def get_load_field_list(self):
        """Build a flat list of columns for the given mapping,
        including fields, lookups, and statics."""
        lookups = self.lookups

        # Build the list of fields to import
        columns = []
        columns.extend(self.fields.keys())

        # Don't include lookups with an `after:` spec (dependent lookups)
        columns.extend([f for f in lookups if not lookups[f].after])
        columns.extend(self.static.keys())

        # If we're using Record Type mapping, `RecordTypeId` goes at the end.
        if "RecordTypeId" in columns:
            columns.remove("RecordTypeId")

        if self.action is DataOperationType.INSERT and "Id" in columns:
            columns.remove("Id")
        if self.record_type or "RecordTypeId" in self.fields:
            columns.append("RecordTypeId")

        return columns

    def get_relative_date_context(self, fields: List[str], org_config: OrgConfig):
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
        return v

    @validator("anchor_date")
    @classmethod
    def validate_anchor_date(cls, v):
        return iso_to_date(v)

    @validator("record_type")
    @classmethod
    def record_type_is_deprecated(cls, v):
        if SHOULD_REPORT_RECORD_TYPE_DEPRECATION:
            logger.warning(
                "record_type is deprecated. Just supply a RecordTypeId column declaration and it will be inferred"
            )
        return v

    @validator("oid_as_pk")
    @classmethod
    def oid_as_pk_is_deprecated(cls, v):
        raise ValueError(
            "oid_as_pk is no longer supported. Include the Id field if desired."
        )

    @validator("fields_", pre=True)
    @classmethod
    def standardize_fields_to_dict(cls, values):
        if values is None:
            values = {}
        if type(values) is list:
            return {elem: elem for elem in values}

        return values

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
        strip: Optional[Callable[[str], str]],
        drop_missing: bool,
        data_operation_type: DataOperationType,
    ) -> bool:
        ret = True

        def replace_if_necessary(dct, name, replacement):
            if name not in describe and replacement in describe:
                dct[replacement] = dct[name]
                del dct[name]
                return replacement
            else:
                return name

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

                f = replace_if_necessary(field_dict, f, inject(f))
            if strip:
                f = replace_if_necessary(field_dict, f, strip(f))

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
        strip: Optional[Callable[[str], str]],
        data_operation_type: DataOperationType,
    ) -> bool:
        # Determine whether we need to inject or strip our sObject.

        self.sf_object = (
            _inject_or_strip_name(self.sf_object, inject, global_describe)
            or _inject_or_strip_name(self.sf_object, strip, global_describe)
            or self.sf_object
        )

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

            def strip(element: str):
                parts = element.split("__")
                if len(parts) == 3 and parts[0] == namespace:
                    return parts[1] + "__" + parts[2]
                else:
                    return element

        else:
            inject = strip = None

        global_describe = CaseInsensitiveDict(
            {
                entry["name"]: entry
                for entry in org_config.salesforce_client.describe()["sobjects"]
            }
        )

        if not self._validate_sobject(global_describe, inject, strip, operation):
            # Don't attempt to validate field permissions if the object doesn't exist.
            return False

        # Validate, inject, and drop (if configured) fields.
        # By this point, we know the attribute is valid.
        describe = getattr(org_config.salesforce_client, self.sf_object).describe()
        describe = CaseInsensitiveDict(
            {entry["name"]: entry for entry in describe["fields"]}
        )

        if not self._validate_field_dict(
            describe, self.fields, inject, strip, drop_missing, operation
        ):
            return False

        if not self._validate_field_dict(
            describe, self.lookups, inject, strip, drop_missing, operation
        ):
            return False

        return True


class MappingSteps(CCIDictModel):
    "Mapping of named steps"
    __root__: Dict[str, MappingStep]

    @root_validator(pre=False)
    @classmethod
    def validate_and_inject_mapping(cls, values):
        if values:
            oids = ["Id" in s.fields_ for s in values["__root__"].values()]
            assert all(oids) or not any(
                oids
            ), "Id must be mapped in all steps or in no steps."

        return values


ValidationError = ValidationError  # export Pydantic's Validation Error under an alias


def parse_from_yaml(source: Union[str, Path, IO]) -> Dict:
    "Parse from a path, url, path-like or file-like"
    return MappingSteps.parse_from_yaml(source)


def validate_and_inject_mapping(
    *,
    mapping: Dict,
    org_config: OrgConfig,
    namespace: str,
    data_operation: DataOperationType,
    inject_namespaces: bool,
    drop_missing: bool,
    org_has_person_accounts_enabled: bool = False,
):
    should_continue = [
        m.validate_and_inject_namespace(
            org_config, namespace, data_operation, inject_namespaces, drop_missing
        )
        for m in mapping.values()
    ]

    if not drop_missing and not all(should_continue):
        raise BulkDataException(
            "One or more schema or permissions errors blocked the operation.\n"
            "If you would like to attempt the load regardless, you can specify "
            "'-o drop_missing_schema True' on the command."
        )

    if drop_missing:
        # Drop any steps with sObjects that are not present.
        for (include, step_name) in zip(should_continue, list(mapping.keys())):
            if not include:
                del mapping[step_name]

        # Remove any remaining lookups to dropped objects.
        for m in mapping.values():
            describe = getattr(org_config.salesforce_client, m.sf_object).describe()
            describe = {entry["name"]: entry for entry in describe["fields"]}

            for field in list(m.lookups.keys()):
                lookup = m.lookups[field]
                if lookup.table not in [step.table for step in mapping.values()]:
                    del m.lookups[field]

                    # Make sure this didn't cause the operation to be invalid
                    # by dropping a required field.
                    if not describe[field]["nillable"]:
                        raise BulkDataException(
                            f"{m.sf_object}.{field} is a required field, but the target object "
                            f"{describe[field]['referenceTo']} was removed from the operation "
                            "due to missing permissions."
                        )

    # If the org has person accounts enable, add a field mapping to track "IsPersonAccount".
    # IsPersonAccount field values are used to properly load person account records.
    if org_has_person_accounts_enabled and data_operation == DataOperationType.QUERY:
        for step in mapping.values():
            if step["sf_object"] in ("Account", "Contact"):
                step["fields"]["IsPersonAccount"] = "IsPersonAccount"


def _inject_or_strip_name(name, transform, global_describe):
    if not transform:
        return None
    new_name = transform(name)

    if name == new_name:
        return None

    if name in global_describe and new_name in global_describe:
        logger.warning(
            f"Both {name} and {new_name} are present in the target org. Using {name}."
        )
        return None

    if name not in global_describe and new_name in global_describe:
        return new_name

    return None
