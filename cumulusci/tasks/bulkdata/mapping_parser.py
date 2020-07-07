from typing import Dict, List, Union, IO, Optional, Any, Callable
from logging import getLogger
from pathlib import Path

from pydantic import Field, validator, root_validator, ValidationError

from cumulusci.core.config.OrgConfig import OrgConfig
from cumulusci.tasks.bulkdata.step import DataOperationType
from cumulusci.utils.yaml.model_parser import CCIDictModel
from cumulusci.utils import convert_to_snake_case

from typing_extensions import Literal

LOGGER_NAME = "MAPPING_LOADER"
logger = getLogger(LOGGER_NAME)


class MappingLookup(CCIDictModel):
    "Lookup relationship between two tables."
    table: str
    key_field: Optional[str] = None
    value_field: Optional[str] = None
    join_field: Optional[str] = None
    after: Optional[str] = None
    aliased_table: Optional[str] = None
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
    fields_: Optional[Union[Dict[str, str], List[str]]] = Field({}, alias="fields")
    lookups: Dict[str, MappingLookup] = {}
    static: Dict[str, str] = {}
    filters: List[str] = []
    action: str = "insert"
    oid_as_pk: bool = False  # this one should be discussed and probably deprecated
    record_type: Optional[str] = None  # should be discussed and probably deprecated
    bulk_mode: Optional[
        Literal["Serial", "Parallel"]
    ] = None  # default should come from task options
    sf_id_table: Optional[str] = None  # populated at runtime in extract.py
    record_type_table: Optional[str] = None  # populated at runtime in extract.py

    @validator("record_type")
    @classmethod
    def record_type_is_deprecated(cls, v):
        logger.warning(
            "record_type is deprecated. Just supply a RecordTypeId column declaration and it will be inferred"
        )
        return v

    @validator("oid_as_pk")
    @classmethod
    def oid_as_pk_is_deprecated(cls, v):
        logger.warning(
            "oid_as_pk is deprecated. Just supply an Id column declaration and it will be inferred."
        )
        return v

    @validator("fields_")
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

    def _is_injectable(self, element: str) -> bool:
        return element.count("__") == 1

    def _get_permission_type(self, operation: DataOperationType) -> str:
        if operation is DataOperationType.INSERT and self.action == "insert":
            return "createable"
        elif operation is DataOperationType.UPDATE or self.action == "update":
            return "updateable"
        elif operation is DataOperationType.QUERY:
            return "queryable"

    def _check_object_permission(
        self, global_describe: Dict, sobject: str, operation: DataOperationType
    ):
        perm = self._get_permission_type(operation)
        return sobject in global_describe and global_describe[sobject][perm]

    def _check_field_permission(
        self, describe: Dict, field: str, operation: DataOperationType
    ):
        perm = self._get_permission_type(operation)
        # Fields don't have "queryable" permission.
        access = describe[field].get(perm) or True
        return field in describe and access

    def _validate_field_dict(
        self,
        describe: Dict,
        field_dict: Dict[str, Any],
        inject: Optional[Callable[[str], str]],
        drop_missing: bool,
        data_operation_type: DataOperationType,
    ) -> bool:
        ret = True

        orig_fields = field_dict.copy()
        for f, entry in orig_fields.items():
            # Do we need to inject this field?
            if f == "Id":
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

            # Do we have the right permissions for this field, or do we need to drop it?
            if not self._check_field_permission(describe, f, data_operation_type):
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
        global_describe: Dict,
        inject: Optional[Callable[[str], str]],
        drop_missing: bool,
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

        # Validate our access to this sObject.
        if not self._check_object_permission(
            global_describe, self.sf_object, data_operation_type
        ):
            logger.warning(
                f"sObject {self.sf_object} is not present or does not have the correct permissions."
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

        else:
            inject = None

        global_describe = {
            entry["name"]: entry
            for entry in org_config.salesforce_client.describe()["sobjects"]
        }

        if not self._validate_sobject(global_describe, inject, drop_missing, operation):
            # Don't attempt to validate field permissions if the object doesn't exist.
            return False

        # Validate, inject, and drop (if configured) fields.
        # By this point, we know the attribute is valid.
        describe = getattr(org_config.salesforce_client, self.sf_object).describe()
        describe = {entry["name"]: entry for entry in describe["fields"]}

        if not self._validate_field_dict(
            describe, self.fields, inject, drop_missing, operation
        ):
            return False
        if not self._validate_field_dict(
            describe, self.lookups, inject, drop_missing, operation
        ):
            return False

        return True


class MappingSteps(CCIDictModel):
    "Mapping of named steps"
    __root__: Dict[str, MappingStep]

    @root_validator(pre=False)
    @classmethod
    def validate_mapping(cls, values):
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
