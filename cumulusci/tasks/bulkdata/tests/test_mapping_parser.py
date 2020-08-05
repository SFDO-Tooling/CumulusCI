from pathlib import Path
from io import StringIO
from unittest import mock
import logging
import pytest

import responses
from yaml import safe_load, dump, YAMLError

from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.mapping_parser import (
    MappingLookup,
    MappingStep,
    parse_from_yaml,
    validate_and_inject_mapping,
    ValidationError,
    CaseInsensitiveDict,
)
from cumulusci.tasks.bulkdata.step import DataOperationType
from cumulusci.tasks.bulkdata.tests.test_utils import mock_describe_calls
from cumulusci.tests.util import DummyOrgConfig


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

        with open(base_path) as f:
            raw_mapping = safe_load(f)
        raw_mapping["Insert Households"]["oid_as_pk"] = True

        parse_from_yaml(StringIO(dump(raw_mapping)))
        assert "oid_as_pk" in caplog.text

    def test_bad_mapping_syntax(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        with open(base_path, "r") as f:
            data = f.read().replace(":", ": abcd")
            with pytest.raises(YAMLError):
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

    # Start of FLS/Namespace Injection Unit Tests

    def test_is_injectable(self):
        assert MappingStep._is_injectable("Test__c")
        assert not MappingStep._is_injectable("npsp__Test__c")
        assert not MappingStep._is_injectable("Account")

    def test_get_permission_type(self):
        ms = MappingStep(sf_object="Account", fields=["Name"], action="insert")
        assert ms._get_permission_type(DataOperationType.INSERT) == "createable"
        assert ms._get_permission_type(DataOperationType.QUERY) == "queryable"

        ms = MappingStep(sf_object="Account", fields=["Name"], action="update")
        assert ms._get_permission_type(DataOperationType.INSERT) == "updateable"

    def test_check_field_permission(self):
        ms = MappingStep(sf_object="Account", fields=["Name"], action="insert")

        assert ms._check_field_permission(
            {"Name": {"createable": True}}, "Name", DataOperationType.INSERT
        )

        assert ms._check_field_permission(
            {"Name": {"createable": True}}, "Name", DataOperationType.QUERY
        )

        ms = MappingStep(sf_object="Account", fields=["Name"], action="update")

        assert not ms._check_field_permission(
            {"Name": {"updateable": False}}, "Name", DataOperationType.INSERT
        )

        assert not ms._check_field_permission(
            {"Name": {"updateable": False}}, "Website", DataOperationType.INSERT
        )

    def test_validate_field_dict__fls_checks(self):
        ms = MappingStep(
            sf_object="Account", fields=["Id", "Name", "Website"], action="insert"
        )

        assert ms._validate_field_dict(
            CaseInsensitiveDict(
                {"Name": {"createable": True}, "Website": {"createable": True}}
            ),
            ms.fields_,
            None,
            False,
            DataOperationType.INSERT,
        )

        assert not ms._validate_field_dict(
            CaseInsensitiveDict(
                {"Name": {"createable": True}, "Website": {"createable": False}}
            ),
            ms.fields_,
            None,
            False,
            DataOperationType.INSERT,
        )

    def test_validate_field_dict__injection(self):
        ms = MappingStep(
            sf_object="Account", fields=["Id", "Name", "Test__c"], action="insert"
        )

        assert ms._validate_field_dict(
            CaseInsensitiveDict(
                {"Name": {"createable": True}, "npsp__Test__c": {"createable": True}}
            ),
            ms.fields_,
            lambda field: f"npsp__{field}",
            False,
            DataOperationType.INSERT,
        )

        assert ms.fields_ == {"Id": "Id", "Name": "Name", "npsp__Test__c": "Test__c"}

    def test_validate_field_dict__injection_duplicate_fields(self):
        ms = MappingStep(
            sf_object="Account", fields=["Id", "Name", "Test__c"], action="insert"
        )

        assert ms._validate_field_dict(
            CaseInsensitiveDict(
                {
                    "Name": {"createable": True},
                    "npsp__Test__c": {"createable": True},
                    "Test__c": {"createable": True},
                }
            ),
            ms.fields_,
            lambda field: f"npsp__{field}",
            False,
            DataOperationType.INSERT,
        )

        assert ms.fields_ == {"Id": "Id", "Name": "Name", "Test__c": "Test__c"}

    def test_validate_field_dict__drop_missing(self):
        ms = MappingStep(
            sf_object="Account", fields=["Id", "Name", "Website"], action="insert"
        )

        assert ms._validate_field_dict(
            CaseInsensitiveDict(
                {"Name": {"createable": True}, "Website": {"createable": False}}
            ),
            ms.fields_,
            None,
            True,
            DataOperationType.INSERT,
        )

        assert ms.fields_ == {"Id": "Id", "Name": "Name"}

    def test_validate_sobject(self):
        ms = MappingStep(sf_object="Account", fields=["Name"], action="insert")

        assert ms._validate_sobject(
            CaseInsensitiveDict({"Account": {"createable": True}}),
            None,
            DataOperationType.INSERT,
        )

        assert ms._validate_sobject(
            CaseInsensitiveDict({"Account": {"queryable": True}}),
            None,
            DataOperationType.QUERY,
        )

        ms = MappingStep(sf_object="Account", fields=["Name"], action="update")

        assert not ms._validate_sobject(
            CaseInsensitiveDict({"Account": {"updateable": False}}),
            None,
            DataOperationType.INSERT,
        )

    def test_validate_sobject__injection(self):
        ms = MappingStep(sf_object="Test__c", fields=["Name"], action="insert")

        assert ms._validate_sobject(
            CaseInsensitiveDict({"npsp__Test__c": {"createable": True}}),
            lambda obj: f"npsp__{obj}",
            DataOperationType.INSERT,
        )
        assert ms.sf_object == "npsp__Test__c"

    def test_validate_sobject__injection_duplicate(self):
        ms = MappingStep(sf_object="Test__c", fields=["Name"], action="insert")

        assert ms._validate_sobject(
            CaseInsensitiveDict(
                {"npsp__Test__c": {"createable": True}, "Test__c": {"createable": True}}
            ),
            lambda obj: f"npsp__{obj}",
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

        org_config = mock.Mock()
        org_config.salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Account", "createable": True}]
        }
        org_config.salesforce_client.Account.describe.return_value = {
            "fields": [{"name": "ns__Test__c", "createable": True}]
        }

        assert ms.validate_and_inject_namespace(
            org_config, "ns", DataOperationType.INSERT, inject_namespaces=True
        )

        ms._validate_sobject.assert_called_once_with(
            CaseInsensitiveDict({"Account": {"name": "Account", "createable": True}}),
            mock.ANY,  # This is a function def
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
                    False,
                    DataOperationType.INSERT,
                ),
                mock.call(
                    {"ns__Test__c": {"name": "ns__Test__c", "createable": True}},
                    ms.lookups,
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

        org_config = mock.Mock()
        org_config.salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Account", "createable": True}]
        }
        org_config.salesforce_client.Account.describe.return_value = {
            "fields": [
                {"name": "Name", "createable": True},
                {"name": "ns__Lookup__c", "updateable": False, "createable": True},
            ]
        }

        assert ms.validate_and_inject_namespace(
            org_config, "ns", DataOperationType.INSERT, inject_namespaces=True
        )

        ms._validate_sobject.assert_called_once_with(
            CaseInsensitiveDict({"Account": {"name": "Account", "createable": True}}),
            mock.ANY,  # local function def
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
        ms = MappingStep(sf_object="Test__c", fields=["Field__c"], action="insert")

        org_config = mock.Mock()
        org_config.salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Test__c", "createable": True}]
        }
        org_config.salesforce_client.Test__c.describe.return_value = {
            "fields": [{"name": "Field__c", "createable": True}]
        }
        assert ms.validate_and_inject_namespace(
            org_config, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            CaseInsensitiveDict({"Test__c": {"name": "Test__c", "createable": True}}),
            None,
            DataOperationType.INSERT,
        )

        ms._validate_field_dict.assert_has_calls(
            [
                mock.call(
                    {"Field__c": {"name": "Field__c", "createable": True}},
                    {"Field__c": "Field__c"},
                    None,
                    False,
                    DataOperationType.INSERT,
                ),
                mock.call(
                    {"Field__c": {"name": "Field__c", "createable": True}},
                    {},
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
        ms = MappingStep(sf_object="Test__c", fields=["Name"], action="insert")

        org_config = mock.Mock()
        org_config.salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Test__c", "createable": False}]
        }
        org_config.salesforce_client.Test__c.describe.return_value = {
            "fields": [{"name": "Name", "createable": True}]
        }
        assert not ms.validate_and_inject_namespace(
            org_config, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Test__c": {"name": "Test__c", "createable": False}},
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
        ms = MappingStep(sf_object="Test__c", fields=["Name"], action="insert")

        org_config = mock.Mock()
        org_config.salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Test__c", "createable": True}]
        }
        org_config.salesforce_client.Test__c.describe.return_value = {
            "fields": [{"name": "Name", "createable": False}]
        }
        assert not ms.validate_and_inject_namespace(
            org_config, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Test__c": {"name": "Test__c", "createable": True}},
            None,
            DataOperationType.INSERT,
        )

        ms._validate_field_dict.assert_has_calls(
            [
                mock.call(
                    {"Name": {"name": "Name", "createable": False}},
                    {"Name": "Name"},
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

        org_config = mock.Mock()
        org_config.salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Account", "createable": True}]
        }
        org_config.salesforce_client.Account.describe.return_value = {
            "fields": [
                {"name": "Name", "createable": True},
                {"name": "Lookup__c", "updateable": True, "createable": False},
            ]
        }
        assert not ms.validate_and_inject_namespace(
            org_config, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Account": {"name": "Account", "createable": True}},
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

        org_config = mock.Mock()
        org_config.salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Account", "createable": True}]
        }
        org_config.salesforce_client.Account.describe.return_value = {
            "fields": [
                {"name": "Name", "createable": True},
                {"name": "Lookup__c", "updateable": False, "createable": True},
            ]
        }
        assert not ms.validate_and_inject_namespace(
            org_config, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Account": {"name": "Account", "createable": True}},
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
                org_config=org_config,
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
            org_config=org_config,
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
            org_config=org_config,
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
                org_config=org_config,
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
            org_config, "ns", DataOperationType.INSERT, inject_namespaces=True
        )

        assert list(ms.fields.keys()) == ["ns__Description__c"]

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
            org_config=org_config,
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
            org_config=org_config,
            namespace=None,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=False,
            drop_missing=False,
        )
        assert mapping["Insert Accounts"].sf_object == "Account"
        assert mapping["Insert Accounts"].sf_object != "account"
        assert "Name" in mapping["Insert Accounts"].fields
        assert "name" not in mapping["Insert Accounts"].fields
