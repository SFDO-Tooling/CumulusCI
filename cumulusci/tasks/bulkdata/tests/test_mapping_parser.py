import logging
from datetime import date
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import BulkDataException, YAMLParseException
from cumulusci.tasks.bulkdata.mapping_parser import (
    CaseInsensitiveDict,
    MappingLookup,
    MappingStep,
    ValidationError,
    _infer_and_validate_lookups,
    parse_from_yaml,
    validate_and_inject_mapping,
)
from cumulusci.tasks.bulkdata.select_utils import SelectStrategy
from cumulusci.tasks.bulkdata.step import DataApi, DataOperationType
from cumulusci.tests.util import DummyOrgConfig, mock_describe_calls


class TestMappingParser:
    def test_simple_parse(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        assert parse_from_yaml(base_path)

    def test_after(self):
        base_path = Path(__file__).parent / "mapping_after.yml"
        result = parse_from_yaml(base_path)

        step = result["Insert Accounts"]
        lookups = step["lookups"]
        assert lookups
        assert "after" in lookups["ParentId"]
        after_list = {
            lookup["after"] for lookup in lookups.values() if "after" in lookup
        }
        assert after_list

    def test_deprecation(self, caplog):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        caplog.set_level(logging.WARNING)

        parse_from_yaml(base_path)
        assert "record_type" in caplog.text

    def test_deprecation_override(self, caplog):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        caplog.set_level(logging.WARNING)
        with mock.patch(
            "cumulusci.tasks.bulkdata.mapping_parser.SHOULD_REPORT_RECORD_TYPE_DEPRECATION",
            False,
        ):
            mapping = parse_from_yaml(base_path)
            assert "record_type" not in caplog.text
            assert mapping["Insert Households"]["record_type"] == "HH_Account"

    def test_bad_mapping_syntax(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        with open(base_path, "r") as f:
            data = f.read().replace(":", ": abcd")
            with pytest.raises(
                YAMLParseException, match="An error occurred parsing yaml file .*"
            ):
                parse_from_yaml(StringIO(data))

    def test_bad_mapping_grammar(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        with open(base_path, "r") as f:
            data = f.read().replace("record_type", "xyzzy")
            with pytest.raises(ValidationError):
                parse_from_yaml(StringIO(data))

    def test_bad_mapping_id_mode(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        with open(base_path, "r") as f:
            data = f.read().replace("Name: name", "Id: sf_id")
            with pytest.raises(ValidationError):
                parse_from_yaml(StringIO(data))

    def test_bad_mapping_oid_as_pk(self):
        base_path = Path(__file__).parent / "mapping_v1.yml"
        with open(base_path, "r") as f:
            data = f.read().replace("api: bulk", "oid_as_pk: True`")
            with pytest.raises(ValidationError):
                parse_from_yaml(StringIO(data))

    def test_bad_mapping_batch_size(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        with open(base_path, "r") as f:
            data = f.read().replace("record_type: HH_Account", "batch_size: 50000")
            with pytest.raises(ValidationError):
                parse_from_yaml(StringIO(data))

    def test_ambiguous_mapping_batch_size_default(self, caplog):
        caplog.set_level(logging.WARNING)
        base_path = Path(__file__).parent / "mapping_vanilla_sf.yml"
        with open(base_path, "r") as f:
            data = f.read().replace("table: Opportunity", "batch_size: 150")
            data = data.replace("api: bulk", "")
            parse_from_yaml(StringIO(data))

        assert "If you set a `batch_size` you should also set" in caplog.text

    def test_bad_mapping_batch_size_default(self, caplog):
        caplog.set_level(logging.WARNING)
        base_path = Path(__file__).parent / "mapping_vanilla_sf.yml"
        with open(base_path, "r") as f:
            data = f.read().replace("table: Opportunity", "batch_size: 1000")
            data = f.read().replace("api: bulk", "")
            with pytest.raises(ValidationError):
                parse_from_yaml(StringIO(data))

    def test_default_table_to_sobject_name(self):
        base_path = Path(__file__).parent / "mapping_v3.yml"
        with open(base_path, "r") as f:
            data = f.read()
            ms = parse_from_yaml(StringIO(data))
            assert ms["Insert Accounts"].table == "Account"

    def test_fields_list_to_dict(self):
        base_path = Path(__file__).parent / "mapping_v3.yml"
        with open(base_path, "r") as f:
            data = f.read()
            ms = parse_from_yaml(StringIO(data))
            assert ms["Insert Accounts"].fields == {"Name": "Name"}
            assert ms["Insert Contacts"].fields == {
                "FirstName": "FirstName",
                "LastName": "LastName",
                "Email": "Email",
            }

    def test_fields_default_not_present(self):
        base_path = Path(__file__).parent / "mapping_v3.yml"
        with open(base_path, "r") as f:
            data = f.read()
            ms = parse_from_yaml(StringIO(data))
            assert ms["Insert Junction Objects"].fields == {}

    def test_fields_default_null(self):
        base_path = Path(__file__).parent / "mapping_v3.yml"
        with open(base_path, "r") as f:
            data = f.read()
            ms = parse_from_yaml(StringIO(data))
            assert ms["Insert Other Junction Objects"].fields == {}

    def test_load_from_bytes_stream(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        with open(base_path, "rb") as f:
            assert parse_from_yaml(f)

    def test_get_complete_field_map(self):
        m = MappingStep(
            sf_object="Account",
            fields=["Name", "AccountSite"],
            lookups={"ParentId": MappingLookup(table="Account")},
        )

        assert m.get_complete_field_map() == {
            "Name": "Name",
            "AccountSite": "AccountSite",
            "ParentId": "ParentId",
        }
        assert m.get_complete_field_map(include_id=True) == {
            "Id": "sf_id",
            "Name": "Name",
            "AccountSite": "AccountSite",
            "ParentId": "ParentId",
        }

    def test_get_relative_date_context(self):
        mapping = MappingStep(
            sf_object="Account",
            fields=["Some_Date__c", "Some_Datetime__c"],
            anchor_date="2020-07-01",
        )

        salesforce_client = mock.Mock()
        salesforce_client.Account.describe.return_value = {
            "fields": [
                {"name": "Some_Date__c", "type": "date"},
                {"name": "Some_Datetime__c", "type": "datetime"},
                {"name": "Some_Bool__c", "type": "boolean"},
            ]
        }

        assert mapping.get_relative_date_context(
            mapping.get_load_field_list(), salesforce_client
        ) == ([0], [1], date.today())

    def test_get_relative_date_e2e(self):
        base_path = Path(__file__).parent / "mapping_v1.yml"
        mapping = parse_from_yaml(base_path)
        salesforce_client = mock.Mock()
        salesforce_client.Contact.describe.return_value = {
            "fields": [
                {"name": "Some_Date__c", "type": "date"},
                {"name": "Some_Datetime__c", "type": "datetime"},
                {"name": "Some_Bool__c", "type": "boolean"},
            ]
        }
        contacts_mapping = mapping["Insert Contacts"]
        contacts_mapping.fields.update(
            {"Some_Date__c": "Some_Date__c", "Some_Datetime__c": "Some_Datetime__c"}
        )
        assert contacts_mapping.get_relative_date_context(
            contacts_mapping.get_load_field_list(), salesforce_client
        ) == (
            [3],
            [4],
            date.today(),
        )

    def test_select_options__success(self):
        base_path = Path(__file__).parent / "mapping_select.yml"
        result = parse_from_yaml(base_path)

        step = result["Select Accounts"]
        select_options = step.select_options
        assert select_options
        assert select_options.strategy == SelectStrategy.SIMILARITY
        assert select_options.filter == "WHEN Name in ('Sample Account')"
        assert select_options.priority_fields

    def test_select_options__invalid_strategy(self):
        base_path = Path(__file__).parent / "mapping_select_invalid_strategy.yml"
        with pytest.raises(ValueError) as e:
            parse_from_yaml(base_path)
        assert "Invalid strategy value: invalid_strategy" in str(e.value)

    def test_select_options__invalid_threshold__non_float(self):
        base_path = (
            Path(__file__).parent / "mapping_select_invalid_threshold__non_float.yml"
        )
        with pytest.raises(ValueError) as e:
            parse_from_yaml(base_path)
        assert "value is not a valid float" in str(e.value)

    def test_select_options__invalid_threshold__invalid_strategy(self):
        base_path = (
            Path(__file__).parent
            / "mapping_select_invalid_threshold__invalid_strategy.yml"
        )
        with pytest.raises(ValueError) as e:
            parse_from_yaml(base_path)
        assert (
            "If a threshold is specified, the strategy must be set to 'similarity'."
            in str(e.value)
        )

    def test_select_options__invalid_threshold__invalid_number(self):
        base_path = (
            Path(__file__).parent
            / "mapping_select_invalid_threshold__invalid_number.yml"
        )
        with pytest.raises(ValueError) as e:
            parse_from_yaml(base_path)
        assert "Threshold must be between 0 and 1, got 1.5" in str(e.value)

    def test_select_options__missing_priority_fields(self):
        base_path = Path(__file__).parent / "mapping_select_missing_priority_fields.yml"
        with pytest.raises(ValueError) as e:
            parse_from_yaml(base_path)
        print(str(e.value))
        assert (
            "Priority fields {'Email'} are not present in 'fields' or 'lookups'"
            in str(e.value)
        )

    def test_select_options__no_priority_fields(self):
        base_path = Path(__file__).parent / "mapping_select_no_priority_fields.yml"
        result = parse_from_yaml(base_path)

        step = result["Select Accounts"]
        select_options = step.select_options
        assert select_options.priority_fields == {}

    # Start of FLS/Namespace Injection Unit Tests

    def test_is_injectable(self):
        assert MappingStep._is_injectable("Test__c")
        assert not MappingStep._is_injectable("npsp__Test__c")
        assert not MappingStep._is_injectable("Account")

    def test_get_permission_types(self):
        ms = MappingStep(
            sf_object="Account", fields=["Name"], action=DataOperationType.INSERT
        )
        assert ms._get_required_permission_types(DataOperationType.INSERT) == (
            "createable",
        )
        assert ms._get_required_permission_types(DataOperationType.QUERY) == (
            "queryable",
        )

        ms = MappingStep(
            sf_object="Account", fields=["Name"], action=DataOperationType.UPDATE
        )
        assert ms._get_required_permission_types(DataOperationType.INSERT) == (
            "updateable",
        )

        ms = MappingStep(
            sf_object="Account",
            fields=["Name", "Extid__c"],
            action=DataOperationType.UPSERT,
            update_key="Extid__c",
        )
        assert ms._get_required_permission_types(DataOperationType.UPSERT) == (
            "updateable",
            "createable",
        )

    def test_check_field_permission(self):
        ms = MappingStep(
            sf_object="Account", fields=["Name"], action=DataOperationType.INSERT
        )

        assert ms._check_field_permission(
            {"Name": {"createable": True}}, "Name", DataOperationType.INSERT
        )

        assert ms._check_field_permission(
            {"Name": {"createable": True}}, "Name", DataOperationType.QUERY
        )

        ms = MappingStep(
            sf_object="Account", fields=["Name"], action=DataOperationType.UPDATE
        )

        assert not ms._check_field_permission(
            {"Name": {"updateable": False}}, "Name", DataOperationType.INSERT
        )

        assert not ms._check_field_permission(
            {"Name": {"updateable": False}}, "Website", DataOperationType.INSERT
        )

    def test_validate_field_dict__fls_checks(self):
        ms = MappingStep(
            sf_object="Account",
            fields=["Id", "Name", "Website"],
            action=DataOperationType.INSERT,
        )

        assert ms._validate_field_dict(
            describe=CaseInsensitiveDict(
                {"Name": {"createable": True}, "Website": {"createable": True}}
            ),
            field_dict=ms.fields_,
            inject=None,
            strip=None,
            drop_missing=False,
            data_operation_type=DataOperationType.INSERT,
        )

        assert not ms._validate_field_dict(
            describe=CaseInsensitiveDict(
                {"Name": {"createable": True}, "Website": {"createable": False}}
            ),
            field_dict=ms.fields_,
            inject=None,
            strip=None,
            drop_missing=False,
            data_operation_type=DataOperationType.INSERT,
        )

    def test_validate_field_dict__injection(self):
        ms = MappingStep(
            sf_object="Account",
            fields=["Id", "Name", "Test__c"],
            action=DataOperationType.INSERT,
        )

        assert ms._validate_field_dict(
            describe=CaseInsensitiveDict(
                {"Name": {"createable": True}, "npsp__Test__c": {"createable": True}}
            ),
            field_dict=ms.fields_,
            inject=lambda field: f"npsp__{field}",
            strip=None,
            drop_missing=False,
            data_operation_type=DataOperationType.INSERT,
        )

        assert ms.fields_ == {"Id": "Id", "Name": "Name", "npsp__Test__c": "Test__c"}

    def test_validate_fields_required(self):
        ms = MappingStep(
            sf_object="Account",
            fields=["Id", "Name", "Test__c"],
            action=DataOperationType.INSERT,
        )
        fields_describe = CaseInsensitiveDict(
            {
                "Name": {
                    "createable": True,
                    "nillable": False,
                    "defaultedOnCreate": False,
                    "defaultValue": None,
                },
                "npsp__Test__c": {
                    "createable": True,
                    "nillable": False,
                    "defaultedOnCreate": False,
                    "defaultValue": None,
                },
            }
        )
        ms._validate_field_dict(
            describe=fields_describe,
            field_dict=ms.fields_,
            inject=lambda field: f"npsp__{field}",
            strip=None,
            drop_missing=False,
            data_operation_type=DataOperationType.INSERT,
        )
        assert ms.fields_ == {"Id": "Id", "Name": "Name", "npsp__Test__c": "Test__c"}
        assert ms.check_required(fields_describe)

        def test_validate_fields_required_missing(self):
            ms = MappingStep(
                sf_object="Account",
                fields=["Test__c"],
                action=DataOperationType.INSERT,
            )
            fields_describe = CaseInsensitiveDict(
                {
                    "Name": {
                        "createable": True,
                        "nillable": False,
                        "defaultedOnCreate": False,
                        "defaultValue": None,
                    },
                    "Test__c": {
                        "createable": True,
                        "nillable": False,
                        "defaultedOnCreate": False,
                        "defaultValue": None,
                    },
                }
            )
            assert ms.fields_ == {"Test__c": "Test__c"}
            assert not ms.check_required(fields_describe)

    def test_validate_field_dict__injection_duplicate_fields(self):
        ms = MappingStep(
            sf_object="Account",
            fields=["Id", "Name", "Test__c"],
            action=DataOperationType.INSERT,
        )

        assert ms._validate_field_dict(
            describe=CaseInsensitiveDict(
                {
                    "Name": {"createable": True},
                    "npsp__Test__c": {"createable": True},
                    "Test__c": {"createable": True},
                }
            ),
            field_dict=ms.fields_,
            inject=lambda field: f"npsp__{field}",
            strip=None,
            drop_missing=False,
            data_operation_type=DataOperationType.INSERT,
        )

        assert ms.fields_ == {"Id": "Id", "Name": "Name", "Test__c": "Test__c"}

    def test_validate_field_dict__drop_missing(self):
        ms = MappingStep(
            sf_object="Account",
            fields=["Id", "Name", "Website"],
            action=DataOperationType.INSERT,
        )

        assert ms._validate_field_dict(
            describe=CaseInsensitiveDict(
                {"Name": {"createable": True}, "Website": {"createable": False}}
            ),
            field_dict=ms.fields_,
            inject=None,
            strip=None,
            drop_missing=True,
            data_operation_type=DataOperationType.INSERT,
        )

        assert ms.fields_ == {"Id": "Id", "Name": "Name"}

    def test_validate_sobject(self):
        ms = MappingStep(
            sf_object="Account", fields=["Name"], action=DataOperationType.INSERT
        )

        assert ms._validate_sobject(
            CaseInsensitiveDict({"Account": {"createable": True}}),
            None,
            None,
            DataOperationType.INSERT,
        )

        assert ms._validate_sobject(
            CaseInsensitiveDict({"Account": {"queryable": True}}),
            None,
            None,
            DataOperationType.QUERY,
        )

        ms = MappingStep(
            sf_object="Account", fields=["Name"], action=DataOperationType.UPDATE
        )

        assert not ms._validate_sobject(
            CaseInsensitiveDict({"Account": {"updateable": False}}),
            None,
            None,
            DataOperationType.INSERT,
        )

    def test_validate_sobject__injection(self):
        ms = MappingStep(
            sf_object="Test__c", fields=["Name"], action=DataOperationType.INSERT
        )

        assert ms._validate_sobject(
            CaseInsensitiveDict({"npsp__Test__c": {"createable": True}}),
            inject=lambda obj: f"npsp__{obj}",
            strip=None,
            data_operation_type=DataOperationType.INSERT,
        )
        assert ms.sf_object == "npsp__Test__c"

    def test_validate_sobject__stripping(self):
        ms = MappingStep(
            sf_object="foo__Test__c", fields=["Name"], action=DataOperationType.INSERT
        )

        assert ms._validate_sobject(
            CaseInsensitiveDict({"Test__c": {"createable": True}}),
            inject=None,
            strip=lambda obj: obj[len("foo__") :],
            data_operation_type=DataOperationType.INSERT,
        )
        assert ms.sf_object == "Test__c"

    def test_validate_sobject__injection_duplicate(self):
        ms = MappingStep(
            sf_object="Test__c", fields=["Name"], action=DataOperationType.INSERT
        )

        assert ms._validate_sobject(
            CaseInsensitiveDict(
                {"npsp__Test__c": {"createable": True}, "Test__c": {"createable": True}}
            ),
            lambda obj: f"npsp__{obj}",
            None,
            DataOperationType.INSERT,
        )
        assert ms.sf_object == "Test__c"

    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_sobject",
        return_value=True,
    )
    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_field_dict",
        return_value=True,
    )
    def test_validate_and_inject_namespace__injection_fields(
        self, mock_field, mock_sobject
    ):
        ms = parse_from_yaml(
            StringIO(
                """Insert Accounts:
                  sf_object: Account
                  table: Account
                  fields:
                    - Test__c"""
            )
        )["Insert Accounts"]

        salesforce_client = mock.Mock()
        salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Account", "createable": True}]
        }
        salesforce_client.Account.describe.return_value = {
            "fields": [{"name": "ns__Test__c", "createable": True}]
        }

        assert ms.validate_and_inject_namespace(
            salesforce_client, "ns", DataOperationType.INSERT, inject_namespaces=True
        )

        ms._validate_sobject.assert_called_once_with(
            CaseInsensitiveDict({"Account": {"name": "Account", "createable": True}}),
            mock.ANY,  # This is a function def
            mock.ANY,
            DataOperationType.INSERT,
            None,  # validation_result
        )

        ms._validate_field_dict.assert_has_calls(
            [
                mock.call(
                    CaseInsensitiveDict(
                        {"ns__Test__c": {"name": "ns__Test__c", "createable": True}}
                    ),
                    ms.fields,
                    mock.ANY,  # local function def
                    mock.ANY,  # local function def
                    False,
                    DataOperationType.INSERT,
                    None,
                ),
                mock.call(
                    {"ns__Test__c": {"name": "ns__Test__c", "createable": True}},
                    ms.lookups,
                    mock.ANY,  # local function def
                    mock.ANY,  # local function def
                    False,
                    DataOperationType.INSERT,
                    None,
                ),
            ]
        )

    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_sobject",
        return_value=True,
    )
    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_field_dict",
        return_value=True,
    )
    def test_validate_and_inject_namespace__injection_lookups(
        self, mock_field, mock_sobject
    ):
        ms = parse_from_yaml(
            StringIO(
                """Insert Accounts:
                  sf_object: Account
                  table: Account
                  fields:
                    - Name
                  lookups:
                    Lookup__c:
                        table: Stuff"""
            )
        )["Insert Accounts"]

        salesforce_client = mock.Mock()
        salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Account", "createable": True}]
        }
        salesforce_client.Account.describe.return_value = {
            "fields": [
                {"name": "Name", "createable": True},
                {"name": "ns__Lookup__c", "updateable": False, "createable": True},
            ]
        }

        assert ms.validate_and_inject_namespace(
            salesforce_client, "ns", DataOperationType.INSERT, inject_namespaces=True
        )

        ms._validate_sobject.assert_called_once_with(
            CaseInsensitiveDict({"Account": {"name": "Account", "createable": True}}),
            mock.ANY,  # local function def
            mock.ANY,
            DataOperationType.INSERT,
            None,
        )

        ms._validate_field_dict.assert_has_calls(
            [
                mock.call(
                    {
                        "Name": {"name": "Name", "createable": True},
                        "ns__Lookup__c": {
                            "name": "ns__Lookup__c",
                            "updateable": False,
                            "createable": True,
                        },
                    },
                    ms.fields,
                    mock.ANY,  # local function def.
                    mock.ANY,  # local function def.
                    False,
                    DataOperationType.INSERT,
                    None,
                ),
                mock.call(
                    {
                        "Name": {"name": "Name", "createable": True},
                        "ns__Lookup__c": {
                            "name": "ns__Lookup__c",
                            "updateable": False,
                            "createable": True,
                        },
                    },
                    ms.lookups,
                    mock.ANY,  # local function def.
                    mock.ANY,  # local function def.
                    False,
                    DataOperationType.INSERT,
                    None,
                ),
            ]
        )

    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_sobject",
        return_value=True,
    )
    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_field_dict",
        return_value=True,
    )
    def test_validate_and_inject_namespace__fls(self, mock_field, mock_sobject):
        ms = MappingStep(
            sf_object="Test__c", fields=["Field__c"], action=DataOperationType.INSERT
        )

        salesforce_client = mock.Mock()
        salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Test__c", "createable": True}]
        }
        salesforce_client.Test__c.describe.return_value = {
            "fields": [{"name": "Field__c", "createable": True}]
        }
        assert ms.validate_and_inject_namespace(
            salesforce_client, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            CaseInsensitiveDict({"Test__c": {"name": "Test__c", "createable": True}}),
            None,
            None,
            DataOperationType.INSERT,
            None,
        )

        ms._validate_field_dict.assert_has_calls(
            [
                mock.call(
                    {"Field__c": {"name": "Field__c", "createable": True}},
                    {"Field__c": "Field__c"},
                    None,
                    None,
                    False,
                    DataOperationType.INSERT,
                    None,
                ),
                mock.call(
                    {"Field__c": {"name": "Field__c", "createable": True}},
                    {},
                    None,
                    None,
                    False,
                    DataOperationType.INSERT,
                    None,
                ),
            ]
        )

    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_sobject",
        return_value=False,
    )
    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_field_dict",
        return_value=True,
    )
    def test_validate_and_inject_namespace__fls_sobject_failure(
        self, mock_field, mock_sobject
    ):
        ms = MappingStep(
            sf_object="Test__c", fields=["Name"], action=DataOperationType.INSERT
        )

        salesforce_client = mock.Mock()
        salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Test__c", "createable": False}]
        }
        salesforce_client.Test__c.describe.return_value = {
            "fields": [{"name": "Name", "createable": True}]
        }
        assert not ms.validate_and_inject_namespace(
            salesforce_client, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Test__c": {"name": "Test__c", "createable": False}},
            None,
            None,
            DataOperationType.INSERT,
            None,
        )

        ms._validate_field_dict.assert_not_called()

    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_sobject",
        return_value=True,
    )
    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_field_dict",
        return_value=False,
    )
    def test_validate_and_inject_namespace__fls_fields_failure(
        self, mock_field, mock_sobject
    ):
        ms = MappingStep(
            sf_object="Test__c", fields=["Name"], action=DataOperationType.INSERT
        )

        salesforce_client = mock.Mock()
        salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Test__c", "createable": True}]
        }
        salesforce_client.Test__c.describe.return_value = {
            "fields": [{"name": "Name", "createable": False}]
        }
        assert not ms.validate_and_inject_namespace(
            salesforce_client, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Test__c": {"name": "Test__c", "createable": True}},
            None,
            None,
            DataOperationType.INSERT,
            None,
        )

        ms._validate_field_dict.assert_has_calls(
            [
                mock.call(
                    {"Name": {"name": "Name", "createable": False}},
                    {"Name": "Name"},
                    None,
                    None,
                    False,
                    DataOperationType.INSERT,
                    None,
                )
            ]
        )

    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_sobject",
        return_value=True,
    )
    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_field_dict",
        side_effect=[True, False],
    )
    def test_validate_and_inject_namespace__fls_lookups_failure(
        self, mock_field, mock_sobject
    ):
        ms = parse_from_yaml(
            StringIO(
                """Insert Accounts:
                  sf_object: Account
                  table: Account
                  fields:
                    - Name
                  lookups:
                    Lookup__c:
                        table: Stuff"""
            )
        )["Insert Accounts"]

        salesforce_client = mock.Mock()
        salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Account", "createable": True}]
        }
        salesforce_client.Account.describe.return_value = {
            "fields": [
                {"name": "Name", "createable": True},
                {"name": "Lookup__c", "updateable": True, "createable": False},
            ]
        }
        assert not ms.validate_and_inject_namespace(
            salesforce_client, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Account": {"name": "Account", "createable": True}},
            None,
            None,
            DataOperationType.INSERT,
            None,
        )

        ms._validate_field_dict.assert_has_calls(
            [
                mock.call(
                    {
                        "Name": {"name": "Name", "createable": True},
                        "Lookup__c": {
                            "name": "Lookup__c",
                            "updateable": True,
                            "createable": False,
                        },
                    },
                    {"Name": "Name"},
                    None,
                    None,
                    False,
                    DataOperationType.INSERT,
                    None,
                ),
                mock.call(
                    {
                        "Name": {"name": "Name", "createable": True},
                        "Lookup__c": {
                            "name": "Lookup__c",
                            "updateable": True,
                            "createable": False,
                        },
                    },
                    ms.lookups,
                    None,
                    None,
                    False,
                    DataOperationType.INSERT,
                    None,
                ),
            ]
        )

    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_sobject",
        return_value=True,
    )
    @mock.patch(
        "cumulusci.tasks.bulkdata.mapping_parser.MappingStep._validate_field_dict",
        side_effect=[True, False],
    )
    def test_validate_and_inject_namespace__fls_lookups_update_failure(
        self, mock_field, mock_sobject
    ):
        ms = parse_from_yaml(
            StringIO(
                """Insert Accounts:
                  sf_object: Account
                  table: Account
                  fields:
                    - Name
                  lookups:
                    Lookup__c:
                        table: Stuff
                        after: Insert Stuff"""
            )
        )["Insert Accounts"]

        salesforce_client = mock.Mock()
        salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Account", "createable": True}]
        }
        salesforce_client.Account.describe.return_value = {
            "fields": [
                {"name": "Name", "createable": True},
                {"name": "Lookup__c", "updateable": False, "createable": True},
            ]
        }
        assert not ms.validate_and_inject_namespace(
            salesforce_client, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Account": {"name": "Account", "createable": True}},
            None,
            None,
            DataOperationType.INSERT,
            None,
        )

        ms._validate_field_dict.assert_has_calls(
            [
                mock.call(
                    {
                        "Name": {"name": "Name", "createable": True},
                        "Lookup__c": {
                            "name": "Lookup__c",
                            "updateable": False,
                            "createable": True,
                        },
                    },
                    {"Name": "Name"},
                    None,
                    None,
                    False,
                    DataOperationType.INSERT,
                    None,
                ),
                mock.call(
                    {
                        "Name": {"name": "Name", "createable": True},
                        "Lookup__c": {
                            "name": "Lookup__c",
                            "updateable": False,
                            "createable": True,
                        },
                    },
                    ms.lookups,
                    None,
                    None,
                    False,
                    DataOperationType.INSERT,
                    None,
                ),
            ]
        )

    # Start of FLS/Namespace Injection Integration Tests

    @responses.activate
    def test_validate_and_inject_mapping_enforces_fls(self):
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                "Insert Accounts:\n  sf_object: Account\n  table: Account\n  fields:\n    - Nonsense__c"
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        with pytest.raises(BulkDataException):
            validate_and_inject_mapping(
                mapping=mapping,
                sf=org_config.salesforce_client,
                namespace=None,
                data_operation=DataOperationType.INSERT,
                inject_namespaces=False,
                drop_missing=False,
            )

    @responses.activate
    def test_validate_and_inject_mapping_removes_steps_with_drop_missing(self):
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                "Insert Accounts:\n  sf_object: NotAccount\n  table: Account\n  fields:\n    - Nonsense__c"
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=True,
        )

        assert "Insert Accounts" not in mapping

    @responses.activate
    def test_validate_and_inject_mapping_removes_lookups_with_drop_missing(self):
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Accounts:\n  sf_object: NotAccount\n  table: Account\n  fields:\n    - Nonsense__c\n"
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  fields:\n    - LastName\n  lookups:\n    AccountId:\n      table: Account"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=True,
        )

        assert "Insert Accounts" not in mapping
        assert "Insert Contacts" in mapping
        assert "AccountId" not in mapping["Insert Contacts"].lookups

    @responses.activate
    def test_validate_and_inject_mapping_removes_lookups_with_drop_missing__polymorphic_partial_present(
        self,
    ):
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Accounts:\n  sf_object: NotAccount\n  table: Account\n  fields:\n    - Nonsense__c\n"
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  lookups:\n    AccountId:\n      table: Account\n"
                    "Insert Events:\n  sf_object: Event\n  table: Event\n  lookups:\n    WhoId:\n      table:\n        - Contact\n        - Lead"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.QUERY,
            inject_namespaces=False,
            drop_missing=True,
        )

        assert "Insert Accounts" not in mapping
        assert "Insert Contacts" in mapping
        assert "Insert Events" in mapping
        assert "AccountId" not in mapping["Insert Contacts"].lookups
        assert "WhoId" in mapping["Insert Events"].lookups

    @responses.activate
    def test_validate_and_inject_mapping_removes_lookups_with_drop_missing__polymorphic_none_present(
        self,
    ):
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Contacts:\n  sf_object: NotContact\n  table: NotContact\n  fields:\n    - LastName\n"
                    "Insert Leads:\n  sf_object: NotLead\n  table: NotLead\n  fields:\n    - LastName\n    - Company\n"
                    "Insert Events:\n  sf_object: Event\n  table: Event\n  lookups:\n    WhoId:\n      table:\n        - Contact\n        - Lead"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.QUERY,
            inject_namespaces=False,
            drop_missing=True,
        )

        assert "Insert Contacts" not in mapping
        assert "Insert Leads" not in mapping
        assert "Insert Events" in mapping
        assert "WhoId" not in mapping["Insert Events"].lookups

    @responses.activate
    def test_validate_and_inject_mapping_throws_exception_required_lookup_dropped(self):
        mock_describe_calls()

        # This test uses a bit of gimmickry to validate exception behavior on dropping a required lookup.
        # Since mapping_parser identifies target objects via the `table` clause rather than the actual schema,
        # which makes us resilient to polymorphic lookups, we'll pretend the non-nillable `Id` field is a lookup.
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Accounts:\n  sf_object: NotAccount\n  table: Account\n  fields:\n    - Nonsense__c\n"
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  fields:\n    - LastName\n  lookups:\n    Id:\n      table: Account"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        with pytest.raises(BulkDataException):
            validate_and_inject_mapping(
                mapping=mapping,
                sf=org_config.salesforce_client,
                namespace=None,
                data_operation=DataOperationType.INSERT,
                inject_namespaces=False,
                drop_missing=True,
            )

    @responses.activate
    def test_validate_and_inject_mapping_throws_exception_required_fields_missing(
        self, caplog
    ):
        caplog.set_level(logging.ERROR)
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Accounts:\n  sf_object: Account\n  table: Account\n  fields:\n    - ns__Description__c\n"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        # Should raise BulkDataException when drop_missing=False
        with pytest.raises(
            BulkDataException,
            match="One or more schema or permissions errors blocked the operation",
        ):
            validate_and_inject_mapping(
                mapping=mapping,
                sf=org_config.salesforce_client,
                namespace="",
                data_operation=DataOperationType.INSERT,
                inject_namespaces=False,
                drop_missing=False,
            )

        # Verify the error was logged
        expected_error_message = (
            "One or more required fields are missing for loading on Account :{'Name'}"
        )
        error_logs = [
            record.message for record in caplog.records if record.levelname == "ERROR"
        ]
        assert any(expected_error_message in error_log for error_log in error_logs)

    @responses.activate
    def test_validate_and_inject_mapping_allows_missing_required_fields_with_drop_missing(
        self, caplog
    ):
        """Test that drop_missing=True allows missing required fields (with warning)."""
        caplog.set_level(logging.ERROR)
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Accounts:\n  sf_object: Account\n  table: Account\n  fields:\n    - ns__Description__c\n"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        # Should NOT raise exception when drop_missing=True, even with missing required fields
        validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace="",
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=True,
        )

        # Verify the error was still logged as a warning
        expected_error_message = (
            "One or more required fields are missing for loading on Account :{'Name'}"
        )
        error_logs = [
            record.message for record in caplog.records if record.levelname == "ERROR"
        ]
        assert any(expected_error_message in error_log for error_log in error_logs)

    @responses.activate
    def test_validate_and_inject_mapping_injects_namespaces(self):
        mock_describe_calls()
        # Note: ns__Description__c is a mock field added to our stored, mock describes (in JSON)
        ms = parse_from_yaml(
            StringIO(
                """Insert Accounts:
                  sf_object: Account
                  table: Account
                  fields:
                    - Description__c"""
            )
        )["Insert Accounts"]
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        assert ms.validate_and_inject_namespace(
            org_config.salesforce_client,
            "ns",
            DataOperationType.INSERT,
            inject_namespaces=True,
        )

        assert list(ms.fields.keys()) == ["ns__Description__c"]

    @responses.activate
    def test_validate_and_inject_mapping_injects_namespaces__validates_lookup(self):
        """Test to verify that with namespace inject, we validate lookups correctly"""
        mock_describe_calls()
        # Note: ns__Description__c is a mock field added to our stored, mock describes (in JSON)
        mapping = parse_from_yaml(
            StringIO(
                """Insert Accounts:
                  sf_object: Account
                  table: Account
                  fields:
                    - Description__c
                  lookups:
                    LinkedAccount__c:
                      table: Account"""
            )
        )
        ms = mapping["Insert Accounts"]
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        assert ms.validate_and_inject_namespace(
            org_config.salesforce_client,
            "ns",
            DataOperationType.INSERT,
            inject_namespaces=True,
        )
        # Here we verify that the field ns__LinkedAccount__c does lookup
        # to sobject Account inside of describe
        _infer_and_validate_lookups(mapping, org_config.salesforce_client)
        assert list(ms.lookups.keys()) == ["ns__LinkedAccount__c"]

    @responses.activate
    def test_validate_and_inject_mapping_removes_namespaces(self):
        mock_describe_calls()
        # Note: History__c is a mock field added to our stored, mock describes (in JSON)
        ms = parse_from_yaml(
            StringIO(
                """Insert Accounts:
                  sf_object: Account
                  table: Account
                  fields:
                    - ns__History__c"""
            )
        )["Insert Accounts"]
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        assert ms.validate_and_inject_namespace(
            org_config.salesforce_client,
            "ns",
            DataOperationType.INSERT,
            inject_namespaces=True,
        )

        assert list(ms.fields.keys()) == ["History__c"]

    @responses.activate
    def test_validate_and_inject_mapping_queries_is_person_account_field(self):
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Accounts:\n  sf_object: Account\n  table: Account\n  fields:\n    - Description__c\n"
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  lookups:\n    AccountId:\n      table: Account"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.QUERY,
            inject_namespaces=False,
            drop_missing=True,
            org_has_person_accounts_enabled=True,
        )

        assert "Insert Accounts" in mapping
        assert "Insert Contacts" in mapping
        assert "IsPersonAccount" in mapping["Insert Accounts"]["fields"]
        assert "IsPersonAccount" in mapping["Insert Contacts"]["fields"]


class TestMappingLookup:
    def test_get_lookup_key_field__no_model(self):
        lookup = MappingLookup(table="contact", name="AccountId")
        assert lookup.get_lookup_key_field() == "AccountId"

    def test_get_lookup_key_field__snake_case_model(self):
        class FakeModel:
            account_id = mock.MagicMock()

        lookup = MappingLookup(table="contact", name="AccountId")
        assert lookup.get_lookup_key_field(FakeModel()) == "account_id"

    def test_get_lookup_key_field__by_key_field(self):
        class FakeModel:
            foo = mock.MagicMock()

        lookup = MappingLookup(table="contact", key_field="foo", name="AccountId")
        assert lookup.get_lookup_key_field(FakeModel()) == "foo"

    def test_get_lookup_key_field__by_key_field_wrong_case(self):
        class FakeModel:
            account_id = mock.MagicMock()

        # we can correct mismatched mapping files if the mistake is just
        # old-fashioned SQL with new Mapping File
        lookup = MappingLookup(table="contact", key_field="AccountId", name="AccountId")
        assert lookup.get_lookup_key_field(FakeModel()) == "account_id"

    def test_get_lookup_key_field__mismatched_name(self):
        class FakeModel:
            account_id = mock.MagicMock()

        # some mistakes can't be fixed.
        lookup = MappingLookup(table="contact", key_field="Foo", name="Foo")

        with pytest.raises(KeyError):
            lookup.get_lookup_key_field(FakeModel())

    @responses.activate
    def test_validate_and_inject_mapping_works_case_insensitively(self):
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Accounts:\n  sf_object: account\n  table: account\n  fields:\n    - name\n"
                    "Insert Contacts:\n  sf_object: contact\n  table: contact\n  fields:\n    - LaSTnAME\n  lookups:\n    accountid:\n      table: account"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        assert mapping["Insert Accounts"].sf_object != "Account"
        assert mapping["Insert Accounts"].sf_object == "account"
        assert "name" in mapping["Insert Accounts"].fields
        assert "Name" not in mapping["Insert Accounts"].fields

        validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=False,
        )
        assert mapping["Insert Accounts"].sf_object == "Account"
        assert mapping["Insert Accounts"].sf_object != "account"
        assert "Name" in mapping["Insert Accounts"].fields
        assert "name" not in mapping["Insert Accounts"].fields

    @responses.activate
    def test_bulk_attributes(self):
        mapping = parse_from_yaml(
            StringIO(
                (
                    """Insert Accounts:
                        sf_object: account
                        table: account
                        api: rest
                        bulk_mode: Serial
                        batch_size: 50
                        fields:
                            - name"""
                )
            )
        )
        assert mapping["Insert Accounts"].api == DataApi.REST
        assert mapping["Insert Accounts"].bulk_mode == "Serial"
        assert mapping["Insert Accounts"].batch_size == 50

    def test_case_conversions(self):
        mapping = parse_from_yaml(
            StringIO(
                (
                    """Insert Accounts:
                        sf_object: account
                        table: account
                        api: ReST
                        bulk_mode: serial
                        action: INSerT
                        batch_size: 50
                        fields:
                            - name"""
                )
            )
        )
        assert mapping["Insert Accounts"].api == DataApi.REST
        assert mapping["Insert Accounts"].bulk_mode == "Serial"
        assert mapping["Insert Accounts"].action.value == "insert"
        assert mapping["Insert Accounts"].batch_size == 50

    def test_oid_as_pk__raises(self):
        with pytest.raises(ValueError):
            parse_from_yaml(
                StringIO(
                    (
                        """Insert Accounts:
                            sf_object: account
                            oid_as_pk: True
                            fields:
                                - name"""
                    )
                )
            )

    def test_oid_as_pk__false(self):
        result = parse_from_yaml(
            StringIO(
                (
                    """Insert Accounts:
                            sf_object: account
                            oid_as_pk: False
                            fields:
                                - name"""
                )
            )
        )
        assert result["Insert Accounts"].oid_as_pk is False


class TestUpsertKeyValidations:
    def test_upsert_key_wrong_type(self):
        with pytest.raises(ValidationError) as e:
            parse_from_yaml(
                StringIO(
                    (
                        """Insert Accounts:
                        sf_object: account
                        table: account
                        action: upsert
                        update_key: 11
                        fields:
                            - name"""
                    )
                )
            )
        assert "update_key" in str(e.value)

    def test_upsert_key_wrong_type__list_item(self):
        with pytest.raises(ValidationError) as e:
            parse_from_yaml(
                StringIO(
                    (
                        """Insert Accounts:
                        sf_object: account
                        table: account
                        action: upsert
                        update_key:
                            - 11
                        fields:
                            - name"""
                    )
                )
            )
        assert "update_key" in str(e.value)

    def test_upsert_key_list(self):
        mapping = parse_from_yaml(
            StringIO(
                (
                    """Insert Accounts:
                        sf_object: account
                        table: account
                        action: etl_upsert
                        update_key:
                            - FirstName
                            - LastName
                        fields:
                            - FirstName
                            - LastName """
                )
            )
        )
        assert mapping["Insert Accounts"]["update_key"] == (
            "FirstName",
            "LastName",
        ), mapping["Insert Accounts"]["update_key"]

    def test_get_extract_field_list(self):
        """Test to ensure Id comes first, lookups come
        last and order of mappings do not change"""
        m = MappingStep(
            sf_object="Account",
            fields=["Name", "RecordTypeId", "AccountSite"],
            lookups={"ParentId": MappingLookup(table="Account")},
        )

        assert m.get_extract_field_list() == [
            "Id",
            "Name",
            "RecordTypeId",
            "AccountSite",
            "ParentId",
        ]

    @responses.activate
    def test_infer_and_validate_lookups__table_doesnt_exist(self, caplog):
        caplog.set_level(logging.ERROR)
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  lookups:\n    AccountId:\n      table: Account"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        expected_error_message = "The table Account does not exist in the mapping file"

        with pytest.raises(BulkDataException) as e:
            _infer_and_validate_lookups(
                mapping=mapping, sf=org_config.salesforce_client
            )
            assert "One or more relationship errors blocked the operation" in str(
                e.value
            )
        error_logs = [
            record.message for record in caplog.records if record.levelname == "ERROR"
        ]
        assert any(expected_error_message in error_log for error_log in error_logs)

    @responses.activate
    def test_infer_and_validate_lookups__incorrect_order(self, caplog):
        caplog.set_level(logging.ERROR)
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Account:\n"
                    "  sf_object: Account\n"
                    "  table: Account\n"
                    "  fields:\n"
                    "    - Description__c\n"
                    "Insert Events:\n"
                    "  sf_object: Event\n"
                    "  table: Event\n"
                    "  lookups:\n"
                    "    WhatId:\n"
                    "      table:\n"
                    "        - Opportunity\n"
                    "        - Account\n"
                    "Insert Opportunity:\n"
                    "  sf_object: Opportunity\n"
                    "  table: Opportunity\n"
                    "  fields:\n"
                    "    - Description__c\n"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        expected_error_message = "All included target objects (Opportunity,Account) for the field Event.WhatId must precede Event in the mapping."

        with pytest.raises(BulkDataException) as e:
            _infer_and_validate_lookups(
                mapping=mapping, sf=org_config.salesforce_client
            )
            assert "One or more relationship errors blocked the operation" in str(
                e.value
            )
        error_logs = [
            record.message for record in caplog.records if record.levelname == "ERROR"
        ]
        assert any(expected_error_message in error_log for error_log in error_logs)

    @responses.activate
    def test_infer_and_validate_lookups__after(self):
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Accounts:\n  sf_object: Account\n  table: Account\n  lookups:\n    ParentId:\n      table: Account\n"
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  lookups:\n    AccountId:\n      table: Account"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )
        _infer_and_validate_lookups(mapping=mapping, sf=org_config.salesforce_client)
        assert mapping["Insert Accounts"].lookups["ParentId"].after == "Insert Accounts"
        assert mapping["Insert Contacts"].lookups["AccountId"].after is None

    @responses.activate
    def test_infer_and_validate_lookups__invalid_reference(self, caplog):
        caplog.set_level(logging.ERROR)
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Events:\n  sf_object: Event\n  table: Event\n  fields:\n    - Description__c\n"
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  lookups:\n    AccountId:\n      table: Event"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        expected_error_message = "The lookup Event is not a valid lookup"

        with pytest.raises(BulkDataException) as e:
            _infer_and_validate_lookups(
                mapping=mapping, sf=org_config.salesforce_client
            )
            assert "One or more relationship errors blocked the operation" in str(
                e.value
            )
        error_logs = [
            record.message for record in caplog.records if record.levelname == "ERROR"
        ]
        assert any(expected_error_message in error_log for error_log in error_logs)


class TestValidationResult:
    """Tests for ValidationResult class"""

    def test_validation_result_initialization(self):
        """Test ValidationResult initializes with empty lists"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        result = ValidationResult()
        assert result.errors == []
        assert result.warnings == []
        assert not result.has_errors()

    def test_validation_result_add_error(self, caplog):
        """Test adding errors to ValidationResult"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        caplog.set_level(logging.ERROR)
        result = ValidationResult()

        result.add_error("Test error 1")
        result.add_error("Test error 2")

        assert len(result.errors) == 2
        assert "Test error 1" in result.errors
        assert "Test error 2" in result.errors
        assert result.has_errors()

        # Verify errors are also logged
        assert "Test error 1" in caplog.text
        assert "Test error 2" in caplog.text

    def test_validation_result_add_warning(self, caplog):
        """Test adding warnings to ValidationResult"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        caplog.set_level(logging.WARNING)
        result = ValidationResult()

        result.add_warning("Test warning 1")
        result.add_warning("Test warning 2")

        assert len(result.warnings) == 2
        assert "Test warning 1" in result.warnings
        assert "Test warning 2" in result.warnings
        assert not result.has_errors()  # Warnings don't count as errors

        # Verify warnings are also logged
        assert "Test warning 1" in caplog.text
        assert "Test warning 2" in caplog.text

    def test_validation_result_mixed_errors_and_warnings(self):
        """Test ValidationResult with both errors and warnings"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        result = ValidationResult()

        result.add_warning("Warning message")
        result.add_error("Error message")
        result.add_warning("Another warning")

        assert len(result.errors) == 1
        assert len(result.warnings) == 2
        assert result.has_errors()


class TestValidateOnlyMode:
    """Tests for validate_only mode in validate_and_inject_mapping"""

    @responses.activate
    def test_validate_only_returns_validation_result(self):
        """Test that validate_only=True returns ValidationResult"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                "Insert Accounts:\n  sf_object: Account\n  table: Account\n  fields:\n    - Name"
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        result = validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=False,
            validate_only=True,
        )

        assert result is not None
        assert isinstance(result, ValidationResult)
        assert not result.has_errors()

    @responses.activate
    def test_validate_only_false_returns_none(self):
        """Test that validate_only=False returns None"""
        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                "Insert Accounts:\n  sf_object: Account\n  table: Account\n  fields:\n    - Name"
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        result = validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=False,
            validate_only=False,
        )

        assert result is None

    @responses.activate
    def test_validate_only_collects_missing_field_errors(self):
        """Test that validate_only collects missing field errors"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                "Insert Accounts:\n  sf_object: Account\n  table: Account\n  fields:\n    - Nonsense__c"
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        result = validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=False,
            validate_only=True,
        )

        assert result is not None
        assert isinstance(result, ValidationResult)
        assert result.has_errors()
        # Should have errors about missing field
        assert any("Nonsense__c" in error for error in result.errors)

    @responses.activate
    def test_validate_only_collects_missing_required_field_errors(self):
        """Test that validate_only collects missing required field errors"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                "Insert Accounts:\n  sf_object: Account\n  table: Account\n  fields:\n    - Description"
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        result = validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=False,
            validate_only=True,
        )

        assert result is not None
        assert isinstance(result, ValidationResult)
        assert result.has_errors()
        # Should have error about missing required field 'Name'
        assert any("required fields" in error.lower() for error in result.errors)
        assert any("Name" in error for error in result.errors)

    @responses.activate
    def test_validate_only_early_return_on_sobject_error(self):
        """Test that validate_only returns early when sObject doesn't exist"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                "Insert Invalid:\n  sf_object: InvalidObject__c\n  table: InvalidObject\n  fields:\n    - Name"
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        result = validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=False,
            validate_only=True,
        )

        assert result is not None
        assert isinstance(result, ValidationResult)
        assert result.has_errors()
        # Should have error about missing object
        assert any("InvalidObject__c" in error for error in result.errors)

    @responses.activate
    def test_validate_only_collects_lookup_errors(self):
        """Test that validate_only collects lookup validation errors"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  fields:\n    - LastName\n  lookups:\n    AccountId:\n      table: Account"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        result = validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=False,
            validate_only=True,
        )

        assert result is not None
        assert isinstance(result, ValidationResult)
        assert result.has_errors()
        # Should have error about missing Account table
        assert any(
            "Account" in error and "does not exist" in error for error in result.errors
        )

    @responses.activate
    def test_validate_only_without_load_skips_lookup_validation(self):
        """Test that validate_only skips lookup validation for QUERY operations"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mock_describe_calls()
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  fields:\n    - LastName\n  lookups:\n    AccountId:\n      table: Account"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        result = validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.QUERY,  # Not a load operation
            inject_namespaces=False,
            drop_missing=False,
            validate_only=True,
        )

        assert result is not None
        assert isinstance(result, ValidationResult)
        # Should not have lookup validation errors since it's a QUERY
        assert not any(
            "Account" in error and "does not exist" in error for error in result.errors
        )


class TestValidationResultParameter:
    """Tests for optional ValidationResult parameter in validation methods"""

    def test_check_required_with_validation_result(self):
        """Test check_required adds errors to ValidationResult when provided"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        ms = MappingStep(
            sf_object="Account",
            fields=["Description"],
            action=DataOperationType.INSERT,
        )
        fields_describe = CaseInsensitiveDict(
            {
                "Name": {
                    "createable": True,
                    "nillable": False,
                    "defaultedOnCreate": False,
                    "defaultValue": None,
                },
                "Description": {
                    "createable": True,
                    "nillable": True,
                    "defaultedOnCreate": False,
                    "defaultValue": None,
                },
            }
        )

        validation_result = ValidationResult()
        result = ms.check_required(fields_describe, validation_result)

        assert not result  # Should return False due to missing required field
        assert validation_result.has_errors()
        assert any(
            "required fields" in error.lower() for error in validation_result.errors
        )
        assert any("Name" in error for error in validation_result.errors)

    def test_check_required_without_validation_result_logs(self, caplog):
        """Test check_required logs errors when ValidationResult not provided"""
        caplog.set_level(logging.ERROR)
        ms = MappingStep(
            sf_object="Account",
            fields=["Description"],
            action=DataOperationType.INSERT,
        )
        fields_describe = CaseInsensitiveDict(
            {
                "Name": {
                    "createable": True,
                    "nillable": False,
                    "defaultedOnCreate": False,
                    "defaultValue": None,
                },
            }
        )

        result = ms.check_required(fields_describe, None)

        assert not result
        assert "required fields" in caplog.text.lower()
        assert "Name" in caplog.text

    def test_validate_sobject_with_validation_result(self):
        """Test _validate_sobject adds errors to ValidationResult"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        ms = MappingStep(
            sf_object="InvalidObject__c",
            fields=["Name"],
            action=DataOperationType.INSERT,
        )

        validation_result = ValidationResult()
        result = ms._validate_sobject(
            CaseInsensitiveDict({"Account": {"createable": True}}),
            None,
            None,
            DataOperationType.INSERT,
            validation_result,
        )

        assert not result
        assert validation_result.has_errors()
        assert any("InvalidObject__c" in error for error in validation_result.errors)

    def test_validate_field_dict_with_validation_result(self):
        """Test _validate_field_dict adds errors to ValidationResult"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        ms = MappingStep(
            sf_object="Account",
            fields=["Name", "NonexistentField__c"],
            action=DataOperationType.INSERT,
        )

        validation_result = ValidationResult()
        result = ms._validate_field_dict(
            describe=CaseInsensitiveDict({"Name": {"createable": True}}),
            field_dict=ms.fields_,
            inject=None,
            strip=None,
            drop_missing=False,
            data_operation_type=DataOperationType.INSERT,
            validation_result=validation_result,
        )

        assert not result
        assert validation_result.has_errors()
        assert any("NonexistentField__c" in error for error in validation_result.errors)

    def test_infer_and_validate_lookups_with_validation_result(self):
        """Test _infer_and_validate_lookups adds errors to ValidationResult"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mock_sf = mock.Mock()
        mock_sf.Contact.describe.return_value = {
            "fields": [
                {
                    "name": "AccountId",
                    "referenceTo": ["Account"],
                }
            ]
        }

        mapping = {
            "Insert Contacts": MappingStep(
                sf_object="Contact",
                table="Contact",
                fields=["LastName"],
                lookups={"AccountId": MappingLookup(table="Account", name="AccountId")},
            )
        }

        validation_result = ValidationResult()
        _infer_and_validate_lookups(mapping, mock_sf, validation_result)

        # Should have error about missing Account table
        assert validation_result.has_errors()
        assert any(
            "Account" in error and "does not exist" in error
            for error in validation_result.errors
        )

    def test_infer_and_validate_lookups_without_validation_result_raises(self):
        """Test _infer_and_validate_lookups raises exception when ValidationResult not provided"""
        mock_sf = mock.Mock()
        mock_sf.Contact.describe.return_value = {
            "fields": [
                {
                    "name": "AccountId",
                    "referenceTo": ["Account"],
                }
            ]
        }

        mapping = {
            "Insert Contacts": MappingStep(
                sf_object="Contact",
                table="Contact",
                fields=["LastName"],
                lookups={"AccountId": MappingLookup(table="Account", name="AccountId")},
            )
        }

        with pytest.raises(BulkDataException) as e:
            _infer_and_validate_lookups(mapping, mock_sf, None)

        assert "relationship errors" in str(e.value).lower()


class TestValidationResultCoverage:
    """Additional tests to achieve full coverage of ValidationResult code paths"""

    def test_validate_field_dict_duplicate_field_with_validation_result(self):
        """Test _validate_field_dict with duplicate fields (injected and original) using ValidationResult"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        ms = MappingStep(
            sf_object="Account",
            fields=["Test__c"],
            action=DataOperationType.INSERT,
        )

        validation_result = ValidationResult()
        # Both Test__c and ns__Test__c exist in describe
        result = ms._validate_field_dict(
            describe=CaseInsensitiveDict(
                {"Test__c": {"createable": True}, "ns__Test__c": {"createable": True}}
            ),
            field_dict=ms.fields_,
            inject=lambda field: f"ns__{field}",
            strip=None,
            drop_missing=False,
            data_operation_type=DataOperationType.INSERT,
            validation_result=validation_result,
        )

        assert result
        # Should have warning about both fields being present
        assert any(
            "Both" in warning and "Test__c" in warning
            for warning in validation_result.warnings
        )

    def test_validate_field_dict_permission_error_with_validation_result(self):
        """Test _validate_field_dict with field permission errors using ValidationResult"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        ms = MappingStep(
            sf_object="Account",
            fields=["Name"],
            action=DataOperationType.INSERT,
        )

        validation_result = ValidationResult()
        result = ms._validate_field_dict(
            describe=CaseInsensitiveDict({"Name": {"createable": False}}),
            field_dict=ms.fields_,
            inject=None,
            strip=None,
            drop_missing=False,
            data_operation_type=DataOperationType.INSERT,
            validation_result=validation_result,
        )

        assert not result
        assert validation_result.has_errors()
        # Should have error about incorrect permissions
        assert any(
            "does not have the correct permissions" in error
            for error in validation_result.errors
        )

    def test_validate_sobject_permission_error_with_validation_result(self):
        """Test _validate_sobject with permission errors using ValidationResult"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        ms = MappingStep(
            sf_object="Account",
            fields=["Name"],
            action=DataOperationType.INSERT,
        )

        validation_result = ValidationResult()
        result = ms._validate_sobject(
            CaseInsensitiveDict({"Account": {"createable": False}}),
            None,
            None,
            DataOperationType.INSERT,
            validation_result,
        )

        assert not result
        assert validation_result.has_errors()
        # Should have error about incorrect permissions
        assert any(
            "does not have the correct permissions" in error
            for error in validation_result.errors
        )

    def test_infer_and_validate_lookups_invalid_reference_with_validation_result(self):
        """Test _infer_and_validate_lookups with invalid reference using ValidationResult"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mock_sf = mock.Mock()
        # Mock Event.describe
        mock_sf.Event.describe.return_value = {
            "fields": [
                {
                    "name": "Description",
                    "referenceTo": [],
                }
            ]
        }
        # Mock Contact.describe
        mock_sf.Contact.describe.return_value = {
            "fields": [
                {
                    "name": "AccountId",
                    "referenceTo": ["Account"],  # Only Account is valid
                }
            ]
        }

        mapping = {
            "Insert Events": MappingStep(
                sf_object="Event",
                table="Event",
                fields=["Description"],
            ),
            "Insert Contacts": MappingStep(
                sf_object="Contact",
                table="Contact",
                fields=["LastName"],
                lookups={
                    "AccountId": MappingLookup(table="Event", name="AccountId")
                },  # Invalid - Event is not a valid lookup
            ),
        }

        validation_result = ValidationResult()
        _infer_and_validate_lookups(mapping, mock_sf, validation_result)

        # Should have error about invalid lookup
        assert validation_result.has_errors()
        assert any(
            "is not a valid lookup" in error for error in validation_result.errors
        )

    def test_infer_and_validate_lookups_polymorphic_incorrect_order_with_validation_result(
        self,
    ):
        """Test _infer_and_validate_lookups with polymorphic lookups in incorrect order using ValidationResult"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mock_sf = mock.Mock()
        # Mock Account.describe
        mock_sf.Account.describe.return_value = {
            "fields": [
                {
                    "name": "Name",
                    "referenceTo": [],
                }
            ]
        }
        # Mock Event.describe
        mock_sf.Event.describe.return_value = {
            "fields": [
                {
                    "name": "WhatId",
                    "referenceTo": ["Account", "Opportunity"],
                }
            ]
        }
        # Mock Opportunity.describe
        mock_sf.Opportunity.describe.return_value = {
            "fields": [
                {
                    "name": "Name",
                    "referenceTo": [],
                }
            ]
        }

        # Event comes before Opportunity, but WhatId references both Account and Opportunity
        mapping = {
            "Insert Account": MappingStep(
                sf_object="Account",
                table="Account",
                fields=["Name"],
            ),
            "Insert Events": MappingStep(
                sf_object="Event",
                table="Event",
                fields=["Description"],
                lookups={
                    "WhatId": MappingLookup(
                        table=["Account", "Opportunity"], name="WhatId"
                    )
                },
            ),
            "Insert Opportunity": MappingStep(
                sf_object="Opportunity",
                table="Opportunity",
                fields=["Name"],
            ),
        }

        validation_result = ValidationResult()
        _infer_and_validate_lookups(mapping, mock_sf, validation_result)

        # Should have error about incorrect order
        assert validation_result.has_errors()
        assert any("must precede" in error for error in validation_result.errors)

    @responses.activate
    def test_validate_and_inject_mapping_required_lookup_dropped_with_validate_only(
        self,
    ):
        """Test validate_and_inject_mapping when a required lookup is dropped in validate_only mode"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mock_describe_calls()
        # Using Id field as a required lookup (it's non-nillable)
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Accounts:\n  sf_object: NotAccount\n  table: Account\n  fields:\n    - Nonsense__c\n"
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  fields:\n    - LastName\n  lookups:\n    Id:\n      table: Account"
                )
            )
        )
        org_config = DummyOrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )

        result = validate_and_inject_mapping(
            mapping=mapping,
            sf=org_config.salesforce_client,
            namespace=None,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=True,
            validate_only=True,
        )

        assert result is not None
        assert isinstance(result, ValidationResult)
        assert result.has_errors()
        # Should have error about required field being dropped
        assert any("is a required field" in error for error in result.errors)
