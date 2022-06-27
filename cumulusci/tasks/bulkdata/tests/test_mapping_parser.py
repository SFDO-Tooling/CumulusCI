import logging
import typing as T
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
from cumulusci.tests.util import (
    DummyOrgConfig,
    fake_get_org_schema,
    mock_describe_calls,
)
from cumulusci.utils import inject_namespace


@mock.patch("cumulusci.tasks.bulkdata.load.get_org_schema", fake_get_org_schema)
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

    def test_validate_and_inject_field_dict__fls_checks(self):
        ms = MappingStep(
            sf_object="Account",
            fields=["Id", "Name", "Website"],
            action=DataOperationType.INSERT,
        )

        assert ms._validate_and_inject_field_dict(
            describe=CaseInsensitiveDict(
                {"Name": {"createable": True}, "Website": {"createable": True}}
            ),
            field_dict=ms.fields_,
            inject=None,
            strip=None,
            drop_missing=False,
            data_operation_type=DataOperationType.INSERT,
        )

        assert not ms._validate_and_inject_field_dict(
            describe=CaseInsensitiveDict(
                {"Name": {"createable": True}, "Website": {"createable": False}}
            ),
            field_dict=ms.fields_,
            inject=None,
            strip=None,
            drop_missing=False,
            data_operation_type=DataOperationType.INSERT,
        )

    def test_validate_and_inject_field_dict__injection(self):
        ms = MappingStep(
            sf_object="Account",
            fields=["Id", "Name", "Test__c"],
            action=DataOperationType.INSERT,
        )

        assert ms._validate_and_inject_field_dict(
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

    def test_validate_and_inject_field_dict__injection_duplicate_fields(self):
        ms = MappingStep(
            sf_object="Account",
            fields=["Id", "Name", "Test__c"],
            action=DataOperationType.INSERT,
        )

        assert ms._validate_and_inject_field_dict(
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

    def test_validate_and_inject_field_dict__drop_missing(self):
        ms = MappingStep(
            sf_object="Account",
            fields=["Id", "Name", "Website"],
            action=DataOperationType.INSERT,
        )

        assert ms._validate_and_inject_field_dict(
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

    def test_validate_and_inject_sobject(self):
        ms = MappingStep(
            sf_object="Account", fields=["Name"], action=DataOperationType.INSERT
        )

        assert ms._validate_and_inject_sobject(
            CaseInsensitiveDict({"Account": {"createable": True}}),
            None,
            None,
            DataOperationType.INSERT,
        )

        assert ms._validate_and_inject_sobject(
            CaseInsensitiveDict({"Account": {"queryable": True}}),
            None,
            None,
            DataOperationType.QUERY,
        )

        ms = MappingStep(
            sf_object="Account", fields=["Name"], action=DataOperationType.UPDATE
        )

        assert not ms._validate_and_inject_sobject(
            CaseInsensitiveDict({"Account": {"updateable": False}}),
            None,
            None,
            DataOperationType.INSERT,
        )

    def test_validate_and_inject_sobject__injection(self):
        ms = MappingStep(
            sf_object="Test__c", fields=["Name"], action=DataOperationType.INSERT
        )

        assert ms._validate_and_inject_sobject(
            CaseInsensitiveDict({"npsp__Test__c": {"createable": True}}),
            inject=lambda obj: f"npsp__{obj}",
            strip=None,
            data_operation_type=DataOperationType.INSERT,
        )
        assert ms.sf_object == "npsp__Test__c"

    def test_validate_and_inject_sobject__stripping(self):
        ms = MappingStep(
            sf_object="foo__Test__c", fields=["Name"], action=DataOperationType.INSERT
        )

        assert ms._validate_and_inject_sobject(
            CaseInsensitiveDict({"Test__c": {"createable": True}}),
            inject=None,
            strip=lambda obj: obj[len("foo__") :],
            data_operation_type=DataOperationType.INSERT,
        )
        assert ms.sf_object == "Test__c"

    def test_validate_and_inject_sobject__injection_duplicate(self):
        ms = MappingStep(
            sf_object="Test__c", fields=["Name"], action=DataOperationType.INSERT
        )

        assert ms._validate_and_inject_sobject(
            CaseInsensitiveDict(
                {"npsp__Test__c": {"createable": True}, "Test__c": {"createable": True}}
            ),
            lambda obj: f"npsp__{obj}",
            None,
            DataOperationType.INSERT,
        )
        assert ms.sf_object == "Test__c"

    def test_validate_and_inject_namespace__injection_fields(self):
        def get_mapping():
            return parse_from_yaml(
                StringIO(
                    """Insert Accounts:
                    sf_object: Account
                    table: Account
                    fields:
                        - Test__c"""
                )
            )["Insert Accounts"]

        ms = get_mapping()
        with fake_get_org_schema(
            obj_data=[
                {
                    "name": "Account",
                    "createable": True,
                    "fields": [{"name": "ns__Test__c", "createable": True}],
                }
            ]
        ) as org_schema:
            assert "Test__c" in ms["fields"]
            assert "ns__Test__c" not in ms["fields"]
            assert ms.validate_and_inject_namespace(
                org_schema, "ns", DataOperationType.INSERT, inject_namespaces=True
            )
            assert "Test__c" not in ms["fields"]
            assert "ns__Test__c" in ms["fields"]

        ms = get_mapping()
        with fake_get_org_schema(
            obj_data=[
                {
                    "name": "Account",
                    "createable": True,
                    "fields": [{"name": "ns__Test__c", "createable": False}],
                }
            ]
        ) as org_schema:
            assert not ms.validate_and_inject_namespace(
                org_schema, "ns", DataOperationType.INSERT, inject_namespaces=True
            )

        with fake_get_org_schema(
            obj_data=[
                {"name": "Account", "createable": True, "fields": []},
            ]
        ) as org_schema:
            assert not ms.validate_and_inject_namespace(
                org_schema, "ns", DataOperationType.INSERT, inject_namespaces=True
            )

    def test_validate_and_inject_namespace__injection_lookups(
        self,
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

        objs = [
            {
                "name": "Account",
                "createable": True,
                "fields": [
                    {"name": "Name", "createable": True},
                    {"name": "ns__Lookup__c", "updateable": False, "createable": True},
                ],
            }
        ]
        with fake_get_org_schema(objs) as schema:
            assert ms.validate_and_inject_namespace(
                schema,
                "ns",
                DataOperationType.INSERT,
                inject_namespaces=True,
            )
        assert "ns__Lookup__c" in ms.lookups
        assert "Lookup__c" not in ms.lookups

    # def test_validate_and_inject_namespace__fls(self):
    #     ms = MappingStep(
    #         sf_object="Test__c", fields=["Field__c"], action=DataOperationType.INSERT
    #     )

    #     objs = [
    #         {
    #             "name": "Test__c",
    #             "createable": True,
    #             "fields": [{"name": "Field__c", "createable": True}],
    #         }
    #     ]

    #     with fake_get_org_schema(objs) as schema:
    #         assert ms.validate_and_inject_namespace(
    #             schema, "ns", DataOperationType.INSERT
    #         )

    #     assert "Field__c" in ms.fields
    #     assert "ns__Field__c" not in ms.fields

    def test_validate_and_inject_namespace__fls(self):
        ms = MappingStep(
            sf_object="Test__c",
            fields=["Field__c"],
            action=DataOperationType.INSERT,
        )
        objs = [
            {
                "name": "Test__c",
                "createable": True,
                "fields": [{"name": "Field__c", "createable": True}],
            }
        ]

        self._expect_validate_and_inject_namespace(ms=ms, objs=objs)
        assert "Field__c" in ms.fields
        assert "ns__Field__c" not in ms.fields
        assert ms.sf_object == "Test__c"  # no ns injection requested

    @staticmethod
    def _expect_validate_and_inject_namespace(
        ms: MappingStep,
        objs: T.Sequence[dict] = None,  # use global defaults
        namespace: str = "ns",
        action: DataOperationType = DataOperationType.INSERT,
        inject_namespaces=False,
    ):
        with fake_get_org_schema(objs) as schema:
            res = ms.validate_and_inject_namespace(
                schema, namespace, action, inject_namespaces=inject_namespaces
            )

        return res

    def test_validate_and_inject_namespace__fls_sobject_failure(self):
        ms = MappingStep(
            sf_object="Test__c", fields=["Name"], action=DataOperationType.INSERT
        )

        valid = self._expect_validate_and_inject_namespace(
            ms=ms,
            objs=[
                {
                    "name": "Test__c",
                    "createable": False,
                    "fields": [{"name": "Name", "createable": True}],
                }
            ],
        )
        assert not valid
        assert ms.sf_object == "Test__c"  # no namespace injection requested
        assert "Name" in ms.fields

    def test_validate_and_inject_namespace__fls_fields_failure(self):
        ms = MappingStep(
            sf_object="Test__c", fields=["Name"], action=DataOperationType.INSERT
        )
        valid = self._expect_validate_and_inject_namespace(
            ms=ms,
            objs=[
                {
                    "name": "Test__c",
                    "createable": True,
                    "fields": [{"name": "Name", "createable": False}],
                }
            ],
        )
        assert not valid
        assert ms.sf_object == "Test__c"  # no namespace injection requested
        assert "Name" in ms.fields

    def test_validate_and_inject_namespace__fls_lookups_failure(self):
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

        valid = self._expect_validate_and_inject_namespace(
            ms=ms,
            objs=[
                {
                    "name": "Account",
                    "createable": True,
                    "fields": [
                        {"name": "Name", "createable": True},
                        {"name": "Lookup__c", "updateable": True, "createable": False},
                    ],
                }
            ],
        )
        assert not valid
        assert "Name" in ms.fields

    def test_validate_and_inject_namespace__fls_lookups_update_failure(self):
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

        objs = [
            {
                "name": "Account",
                "createable": True,
                "fields": [
                    {"name": "Name", "createable": True},
                    {
                        "name": "Lookup__c",
                        "updateable": False,
                        "createable": True,
                    },
                ],
            }
        ]
        validated = self._expect_validate_and_inject_namespace(ms=ms, objs=objs)

        assert not validated

    # Start of FLS/Namespace Injection Integration Tests

    @responses.activate
    def test_validate_and_inject_mapping_enforces_fls(self):
        mapping = parse_from_yaml(
            StringIO(
                "Insert Accounts:\n  sf_object: Account\n  table: Account\n  fields:\n    - Nonsense__c"
            )
        )
        with fake_get_org_schema(obj_data=None) as schema, pytest.raises(
            BulkDataException
        ):
            validate_and_inject_mapping(
                mapping=mapping,
                org_schema=schema,
                namespace=None,
                data_operation=DataOperationType.INSERT,
                inject_namespaces=False,
                drop_missing=False,
            )

    @responses.activate
    def test_validate_and_inject_mapping_removes_steps_with_drop_missing(self):
        mapping = parse_from_yaml(
            StringIO(
                "Insert Accounts:\n  sf_object: NotAccount\n  table: Account\n  fields:\n    - Nonsense__c"
            )
        )

        with fake_get_org_schema() as org_schema:
            validate_and_inject_mapping(
                mapping=mapping,
                org_schema=org_schema,
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

        with fake_get_org_schema() as org_schema:
            validate_and_inject_mapping(
                mapping=mapping,
                org_schema=org_schema,
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

        with pytest.raises(BulkDataException), fake_get_org_schema() as org_schema:
            validate_and_inject_mapping(
                mapping=mapping,
                org_schema=org_schema,
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

        self._expect_validate_and_inject_namespace(ms, inject_namespaces=True)

        assert list(ms.fields.keys()) == ["ns__Description__c"]

    @responses.activate
    def test_validate_and_inject_mapping_removes_namespaces(self):
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

        objs = [
            {
                "name": "Account",
                "createable": True,
                "fields": [{"name": "History__c", "createable": True}],
            }
        ]

        assert self._expect_validate_and_inject_namespace(
            ms=ms,
            objs=objs,
            inject_namespaces=True,
        )

        assert list(ms.fields.keys()) == ["History__c"]

    @responses.activate
    def test_validate_and_inject_mapping_queries_is_person_account_field(self):
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Accounts:\n  sf_object: Account\n  table: Account\n  fields:\n    - Description__c\n"
                    "Insert Contacts:\n  sf_object: Contact\n  table: Contact\n  lookups:\n    AccountId:\n      table: Account"
                )
            )
        )

        with fake_get_org_schema() as org_schema:
            validate_and_inject_mapping(
                mapping=mapping,
                org_schema=org_schema,
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
        mapping = parse_from_yaml(
            StringIO(
                (
                    "Insert Accounts:\n  sf_object: account\n  table: account\n  fields:\n    - name\n"
                    "Insert Contacts:\n  sf_object: contact\n  table: contact\n  fields:\n    - fIRSTnAME\n  lookups:\n    accountid:\n      table: account"
                )
            )
        )

        assert mapping["Insert Accounts"].sf_object != "Account"
        assert mapping["Insert Accounts"].sf_object == "account"
        assert "name" in mapping["Insert Accounts"].fields
        assert "Name" not in mapping["Insert Accounts"].fields

        with fake_get_org_schema() as org_schema:
            validate_and_inject_mapping(
                mapping=mapping,
                org_schema=org_schema,
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
