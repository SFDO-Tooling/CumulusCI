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
    parse_from_yaml,
    validate_and_inject_mapping,
)
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
                ),
                mock.call(
                    {"ns__Test__c": {"name": "ns__Test__c", "createable": True}},
                    ms.lookups,
                    mock.ANY,  # local function def
                    mock.ANY,  # local function def
                    False,
                    DataOperationType.INSERT,
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
                ),
                mock.call(
                    {"Field__c": {"name": "Field__c", "createable": True}},
                    {},
                    None,
                    None,
                    False,
                    DataOperationType.INSERT,
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
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=True,
        )

        assert "Insert Accounts" not in mapping
        assert "Insert Contacts" in mapping
        assert "AccountId" not in mapping["Insert Contacts"].lookups

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
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  lookups:\n    Id:\n      table: Account"
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
                    "Insert Contacts:\n  sf_object: contact\n  table: contact\n  fields:\n    - fIRSTnAME\n  lookups:\n    accountid:\n      table: account"
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
