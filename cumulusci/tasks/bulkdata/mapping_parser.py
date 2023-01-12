import typing as T
from datetime import date
from enum import Enum
from functools import lru_cache
from logging import getLogger
from pathlib import Path
from typing import IO, Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

from pydantic import Field, ValidationError, root_validator, validator
from requests.structures import CaseInsensitiveDict as RequestsCaseInsensitiveDict
from simple_salesforce import Salesforce
from typing_extensions import Literal

from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.dates import iso_to_date
from cumulusci.tasks.bulkdata.step import DataApi, DataOperationType
from cumulusci.utils import convert_to_snake_case
from cumulusci.utils.yaml.model_parser import CCIDictModel

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

    class Config:
        # name is an injected field (from the parent dict)
        # so don't try to serialize it as part of the model
        fields = {"name": {"exclude": True}}


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
    batch_size: int = None
    oid_as_pk: bool = False  # this one should be discussed and probably deprecated
    record_type: Optional[str] = None  # should be discussed and probably deprecated
    bulk_mode: Optional[
        Literal["Serial", "Parallel"]
    ] = None  # default should come from task options
    anchor_date: Optional[Union[str, date]] = None
    soql_filter: Optional[str] = None  # soql_filter property
    update_key: T.Union[str, T.Tuple[str, ...]] = ()  # only for upserts

    @validator("bulk_mode", "api", "action", pre=True)
    def case_normalize(cls, val):
        if isinstance(val, Enum):
            return val
        if val is not None:
            return ENUM_VALUES.get(val.lower())

    @validator("update_key", pre=True)
    def split_update_key(cls, val):
        if isinstance(val, (list, tuple)):
            assert all(isinstance(v, str) for v in val), "All keys should be strings"
            return tuple(v.strip() for v in val)
        if isinstance(val, str):
            return tuple(v.strip() for v in val.split(","))
        else:
            assert isinstance(
                val, (str, list, tuple)
            ), "`update_key` should be a field name or list of field names."
            assert False, "Should be unreachable"  # pragma: no cover

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

    def get_fields_by_type(self, field_type: str, sf: Salesforce):
        describe = getattr(sf, self.sf_object).describe()
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

    def get_relative_date_context(self, fields: List[str], sf: Salesforce):
        date_fields = [
            fields.index(f)
            for f in self.get_fields_by_type("date", sf)
            if f in self.fields
        ]
        date_time_fields = [
            fields.index(f)
            for f in self.get_fields_by_type("datetime", sf)
            if f in self.fields
        ]

        return (date_fields, date_time_fields, date.today())

    @validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v, values):
        if values["api"] == DataApi.REST:
            assert 0 < v <= 200, "Max 200 batch_size for REST loads"
        elif values["api"] == DataApi.BULK:
            assert 0 < v <= 10_000, "Max 10,000 batch_size for bulk or smart loads"
        elif values["api"] == DataApi.SMART and v is not None:
            assert 0 < v < 200, "Max 200 batch_size for Smart loads"
            logger.warning(
                "If you set a `batch_size` you should also set an `api` to `rest` or `bulk`. "
                "`batch_size` means different things for `rest` and `bulk`. "
                "Please see the documentation for further details. "
                "https://cumulusci.readthedocs.io/en/latest/data.html#api-selection"
            )
        else:  # pragma: no cover
            # should not happen
            assert f"Unknown API {values['api']}"
        return v

    @validator("anchor_date")
    @classmethod
    def validate_anchor_date(cls, v):
        if v is not None:
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
        if v:
            raise ValueError(
                "oid_as_pk is no longer supported. Include the Id field if desired."
            )
        return v

    @validator("fields_", pre=True)
    @classmethod
    def standardize_fields_to_dict(cls, values):
        if values is None:
            values = {}
        if type(values) is list:
            values = {elem: elem for elem in values}

        return CaseInsensitiveDict(values)

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
        for name, lookup in v.get("lookups", {}).items():
            lookup.name = name
        return v

    @root_validator
    @classmethod
    def validate_update_key_and_upsert(cls, v):
        """Check that update_key and action are synchronized"""
        update_key = v.get("update_key")
        action = v.get("action")

        if action == DataOperationType.UPSERT:
            assert update_key, "'update_key' must always be supplied for upsert."
            assert (
                len(update_key) == 1
            ), "simple upserts can only support one field at a time."
        elif action in (DataOperationType.ETL_UPSERT, DataOperationType.SMART_UPSERT):
            assert update_key, "'update_key' must always be supplied for upsert."
        else:
            assert not update_key, "Update key should only be specified for upserts"

        if update_key:
            for key in update_key:
                assert key.lower() in (
                    f.lower() for f in v["fields_"]
                ), f"`update_key`: {key} not found in `fields``"

        return v

    @staticmethod
    def _is_injectable(element: str) -> bool:
        return element.count("__") == 1

    def _get_required_permission_types(
        self, operation: DataOperationType
    ) -> T.Tuple[str]:
        """Return a tuple of the permission types required to execute an operation"""
        if operation is DataOperationType.QUERY:
            return ("queryable",)
        if (
            operation is DataOperationType.INSERT
            and self.action is DataOperationType.UPDATE
        ):
            return ("updateable",)
        if operation in (
            DataOperationType.UPSERT,
            DataOperationType.ETL_UPSERT,
        ) or self.action in (DataOperationType.UPSERT, DataOperationType.ETL_UPSERT):
            return ("updateable", "createable")

        return ("createable",)

    def _check_object_permission(
        self, global_describe: Mapping, sobject: str, operation: DataOperationType
    ):
        assert sobject in global_describe
        perms = self._get_required_permission_types(operation)
        return all(global_describe[sobject][perm] for perm in perms)

    def _check_field_permission(
        self, describe: Mapping, field: str, operation: DataOperationType
    ):
        perms = self._get_required_permission_types(operation)
        # Fields don't have "queryable" permission.
        return field in describe and all(
            # To discuss: is this different than `describe[field].get(perm, True)`
            describe[field].get(perm) if perm in describe[field] else True
            for perm in perms
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
        special_names = {"id": "Id", "ispersonaccount": "IsPersonAccount"}
        for f, entry in orig_fields.items():
            # Do we need to inject this field?
            if f.lower() in special_names:
                del field_dict[f]
                canonical_name = special_names[f.lower()]
                field_dict[canonical_name] = entry
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
            relevant_operation = (
                data_operation_type if not is_after_lookup else DataOperationType.UPDATE
            )

            error_in_f = False

            if f not in describe:
                logger.warning(
                    f"Field {self.sf_object}.{f} does not exist or is not visible to the current user."
                )
                error_in_f = True
            elif not self._check_field_permission(
                describe,
                f,
                relevant_operation,
            ):
                relevant_permissions = self._get_required_permission_types(
                    relevant_operation
                )
                logger.warning(
                    f"Field {self.sf_object}.{f} does not have the correct permissions "
                    + f"{relevant_permissions} for this operation."
                )
                error_in_f = True

            if error_in_f:
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
        sf: Salesforce,
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
            {entry["name"]: entry for entry in sf.describe()["sobjects"]}
        )

        if not self._validate_sobject(global_describe, inject, strip, operation):
            # Don't attempt to validate field permissions if the object doesn't exist.
            return False

        # Validate, inject, and drop (if configured) fields.
        # By this point, we know the attribute is valid.
        describe = self.describe_data(sf)

        fields_correct = self._validate_field_dict(
            describe, self.fields, inject, strip, drop_missing, operation
        )

        lookups_correct = self._validate_field_dict(
            describe, self.lookups, inject, strip, drop_missing, operation
        )

        if not (fields_correct and lookups_correct):
            return False

        # inject namespaces into the update_key
        if self.update_key:
            assert isinstance(self.update_key, Tuple)
            update_keys = {k: k for k in self.update_key}
            if not self._validate_field_dict(
                describe,
                update_keys,
                inject,
                strip,
                drop_missing=False,
                data_operation_type=operation,
            ):
                return False
            self.update_key = tuple(update_keys.keys())

        return True

    def describe_data(self, sf: Salesforce):
        return describe_data(self.sf_object, sf)

    def dict(self, by_alias=True, exclude_defaults=True, **kwargs):
        out = super().dict(
            by_alias=by_alias, exclude_defaults=exclude_defaults, **kwargs
        )
        if fields := out.get("fields"):
            keys = list(fields.keys())
            if keys == list(fields.values()):
                out["fields"] = keys
        return out


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
    sf: Salesforce,
    namespace: str,
    data_operation: DataOperationType,
    inject_namespaces: bool,
    drop_missing: bool,
    org_has_person_accounts_enabled: bool = False,
):
    should_continue = [
        m.validate_and_inject_namespace(
            sf, namespace, data_operation, inject_namespaces, drop_missing
        )
        for m in mapping.values()
    ]

    if not drop_missing and not all(should_continue):
        raise BulkDataException(
            "One or more schema or permissions errors blocked the operation.\n"
            "If you would like to attempt the load regardless, you can specify "
            "'--drop_missing_schema True' on the command."
        )

    if drop_missing:
        # Drop any steps with sObjects that are not present.
        for (include, step_name) in zip(should_continue, list(mapping.keys())):
            if not include:
                del mapping[step_name]

        # Remove any remaining lookups to dropped objects.
        for m in mapping.values():
            describe = getattr(sf, m.sf_object).describe()
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


@lru_cache(maxsize=50)
def describe_data(obj: str, sf: Salesforce):
    describe = getattr(sf, obj).describe()
    return CaseInsensitiveDict({entry["name"]: entry for entry in describe["fields"]})
