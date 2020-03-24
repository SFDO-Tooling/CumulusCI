from pathlib import Path
import logging
from io import StringIO
import os
from unittest import mock
from pprint import pformat

import pytest

from yaml import safe_load, dump, YAMLError

from cumulusci.tasks.bulkdata.bulkdata_mapping import (
    parse_from_yaml,
    ValidationError,
    MappingLookup,
)


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
        after_list = {l["after"] for l in lookups.values() if "after" in l}
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

    def test_bad_mapping_grammer(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        with open(base_path, "r") as f:
            data = f.read().replace("record_type", "xyzzy")
            with pytest.raises(ValidationError):
                parse_from_yaml(StringIO(data))

    def test_load_from_bytes_stream(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        with open(base_path, "rb") as f:
            assert parse_from_yaml(f)

    def test_expand_mapping_creates_after_steps(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "mapping_after.yml")

        mapping = parse_from_yaml(mapping_path)

        mocked_account = mock.MagicMock()
        mocked_account.__table__ = mock.MagicMock()
        mocked_account.__table__.primary_key = mock.MagicMock()
        mocked_account.__table__.primary_key.columns = mock.MagicMock()
        mocked_account.__table__.primary_key.columns.keys = mock.MagicMock(
            return_value=["sf_id"]
        )

        mapping._expand_mapping(
            {"contacts": mocked_account, "accounts": mocked_account}
        )

        assert mapping.after_steps["Insert Opportunities"] == {}
        assert [
            "Update Account Dependencies After Insert Contacts",
            "Update Contact Dependencies After Insert Contacts",
        ] == list(mapping.after_steps["Insert Contacts"].keys())

        lookups = {}
        lookups["Id"] = {"table": "accounts", "key_field": "sf_id"}
        lookups["Primary_Contact__c"] = MappingLookup(table="contacts")
        after_steps = mapping.after_steps["Insert Contacts"][
            "Update Account Dependencies After Insert Contacts"
        ]

        expected_after_steps = {
            "sf_object": "Account",
            "action": "update",
            "table": "accounts",
            "lookups": lookups,
            "fields": {},
        }

        assert expected_after_steps == after_steps, pformat(
            (expected_after_steps, after_steps)
        )

        lookups = {}
        lookups["Id"] = {"table": "contacts", "key_field": "sf_id"}
        lookups["ReportsToId"] = MappingLookup(table="contacts")
        assert (
            {
                "sf_object": "Contact",
                "action": "update",
                "table": "contacts",
                "fields": {},
                "lookups": lookups,
            }
            == mapping.after_steps["Insert Contacts"][
                "Update Contact Dependencies After Insert Contacts"
            ]
        )

        assert ["Update Account Dependencies After Insert Accounts"] == list(
            mapping.after_steps["Insert Accounts"].keys()
        )
        lookups = {}
        lookups["Id"] = {"table": "accounts", "key_field": "sf_id"}
        lookups["ParentId"] = MappingLookup(table="accounts")
        assert (
            {
                "sf_object": "Account",
                "action": "update",
                "table": "accounts",
                "fields": {},
                "lookups": lookups,
            }
            == mapping.after_steps["Insert Accounts"][
                "Update Account Dependencies After Insert Accounts"
            ]
        )
