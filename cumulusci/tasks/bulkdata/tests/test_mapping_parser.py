from pathlib import Path
from io import StringIO
from unittest import mock
import logging
import pytest

from yaml import safe_load, dump, YAMLError

from cumulusci.tasks.bulkdata.mapping_parser import MappingLookup, MappingStep
from cumulusci.tasks.bulkdata.mapping_parser import parse_from_yaml, ValidationError
from cumulusci.tasks.bulkdata.step import DataOperationType


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
            {"Name": {"createable": True}, "Website": {"createable": True}},
            ms.fields_,
            None,
            False,
            DataOperationType.INSERT,
        )

        assert not ms._validate_field_dict(
            {"Name": {"createable": True}, "Website": {"createable": False}},
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
            {"Name": {"createable": True}, "npsp__Test__c": {"createable": True}},
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
            {
                "Name": {"createable": True},
                "npsp__Test__c": {"createable": True},
                "Test__c": {"createable": True},
            },
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
            {"Name": {"createable": True}, "Website": {"createable": False}},
            ms.fields_,
            None,
            True,
            DataOperationType.INSERT,
        )

        assert ms.fields_ == {"Id": "Id", "Name": "Name"}

    def test_validate_sobject(self):
        ms = MappingStep(sf_object="Account", fields=["Name"], action="insert")

        assert ms._validate_sobject(
            {"Account": {"createable": True}}, None, DataOperationType.INSERT
        )

        assert ms._validate_sobject(
            {"Account": {"queryable": True}}, None, DataOperationType.QUERY
        )

        ms = MappingStep(sf_object="Account", fields=["Name"], action="update")

        assert not ms._validate_sobject(
            {"Account": {"updateable": False}}, None, DataOperationType.INSERT
        )

    def test_validate_sobject__injection(self):
        ms = MappingStep(sf_object="Test__c", fields=["Name"], action="insert")

        assert ms._validate_sobject(
            {"npsp__Test__c": {"createable": True}},
            lambda obj: f"npsp__{obj}",
            DataOperationType.INSERT,
        )
        assert ms.sf_object == "npsp__Test__c"

    def test_validate_sobject__injection_duplicate(self):
        ms = MappingStep(sf_object="Test__c", fields=["Name"], action="insert")

        assert ms._validate_sobject(
            {"npsp__Test__c": {"createable": True}, "Test__c": {"createable": True}},
            lambda obj: f"npsp__{obj}",
            DataOperationType.INSERT,
        )
        assert ms.sf_object == "Test__c"

    def test_validate_and_inject_namespace__base(self):
        ms = MappingStep(sf_object="Test__c", fields=["Name"], action="insert")

        org_config = mock.Mock()
        org_config.salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Test__c"}]
        }
        org_config.salesforce_client.Test__c.describe.return_value = {
            "fields": [{"name": "Name"}]
        }
        type(ms)._validate_sobject = mock.Mock(return_value=True)
        type(ms)._validate_field_dict = mock.Mock(return_value=True)
        assert ms.validate_and_inject_namespace(
            org_config, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Test__c": {"name": "Test__c"}}, None, DataOperationType.INSERT
        )

        ms._validate_field_dict.assert_has_calls(
            [
                mock.call(
                    {"Name": {"name": "Name"}},
                    {"Name": "Name"},
                    None,
                    False,
                    DataOperationType.INSERT,
                ),
                mock.call(
                    {"Name": {"name": "Name"}},
                    {},
                    None,
                    False,
                    DataOperationType.INSERT,
                ),
            ]
        )

    def test_validate_and_inject_namespace__sobject_failure(self):
        ms = MappingStep(sf_object="Test__c", fields=["Name"], action="insert")

        org_config = mock.Mock()
        org_config.salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Test__c"}]
        }
        org_config.salesforce_client.Test__c.describe.return_value = {
            "fields": [{"name": "Name"}]
        }
        type(ms)._validate_sobject = mock.Mock(return_value=False)
        type(ms)._validate_field_dict = mock.Mock(return_value=False)
        assert not ms.validate_and_inject_namespace(
            org_config, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Test__c": {"name": "Test__c"}}, None, DataOperationType.INSERT
        )

        ms._validate_field_dict.assert_not_called()

    def test_validate_and_inject_namespace__fields_failure(self):
        ms = MappingStep(sf_object="Test__c", fields=["Name"], action="insert")

        org_config = mock.Mock()
        org_config.salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Test__c"}]
        }
        org_config.salesforce_client.Test__c.describe.return_value = {
            "fields": [{"name": "Name"}]
        }
        type(ms)._validate_sobject = mock.Mock(return_value=True)
        type(ms)._validate_field_dict = mock.Mock(return_value=False)
        assert not ms.validate_and_inject_namespace(
            org_config, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Test__c": {"name": "Test__c"}}, None, DataOperationType.INSERT
        )

        ms._validate_field_dict.assert_has_calls(
            [
                mock.call(
                    {"Name": {"name": "Name"}},
                    {"Name": "Name"},
                    None,
                    False,
                    DataOperationType.INSERT,
                )
            ]
        )

    def test_validate_and_inject_namespace__lookups_failure(self):
        ms = MappingStep(sf_object="Test__c", fields=["Name"], action="insert")

        org_config = mock.Mock()
        org_config.salesforce_client.describe.return_value = {
            "sobjects": [{"name": "Test__c"}]
        }
        org_config.salesforce_client.Test__c.describe.return_value = {
            "fields": [{"name": "Name"}]
        }
        type(ms)._validate_sobject = mock.Mock(return_value=True)
        type(ms)._validate_field_dict = mock.Mock(side_effect=[True, False])
        assert not ms.validate_and_inject_namespace(
            org_config, "ns", DataOperationType.INSERT
        )

        ms._validate_sobject.assert_called_once_with(
            {"Test__c": {"name": "Test__c"}}, None, DataOperationType.INSERT
        )

        ms._validate_field_dict.assert_has_calls(
            [
                mock.call(
                    {"Name": {"name": "Name"}},
                    {"Name": "Name"},
                    None,
                    False,
                    DataOperationType.INSERT,
                ),
                mock.call(
                    {"Name": {"name": "Name"}},
                    {},
                    None,
                    False,
                    DataOperationType.INSERT,
                ),
            ]
        )


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
