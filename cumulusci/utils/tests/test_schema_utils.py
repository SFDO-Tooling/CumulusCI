import json
from tempfile import TemporaryDirectory
from unittest.mock import patch
from pathlib import Path

import pytest

import responses
import yaml

from cumulusci.tests.util import DummyOrgConfig, DummyKeychain

from cumulusci.utils.org_schema import get_org_schema


class MockSObject:
    @classmethod
    def describe(cls):
        return {
            "actionOverrides": [],
            "createable": "OVERRIDDEN",
            "deletable": False,
            "name": cls.__name__,
            "fields": [
                {
                    "name": "Id",
                    "aggregatable": True,  # non-default
                    "nameField": False,
                    "namePointing": False,
                    "nillable": False,
                },
                {
                    "name": "IsDeleted",
                    "aggregatable": False,
                    "nameField": False,
                    "namePointing": False,
                    "nillable": "OVERRIDDEN",  # non-default
                },
            ],
        }


class MockSF:
    base_url = "https://innovation-page-2420-dev-ed.cs50.my.salesforce.com/"
    headers = {}

    def describe(self):
        return {
            "encoding": "UTF-8",
            "maxBatchSize": 200,
            "sobjects": [
                {"createable": False, "deletable": True, "name": "Account"},
                {"createable": False, "deletable": True, "name": "Contact"},
            ],
        }

    def restful(self, path, kwargs):
        if (path, kwargs) == (
            "tooling/query",
            {"q": "select Max(RevisionNum) from SourceMember"},
        ):
            return {"records": [{"expr0": 42}]}
        assert False, f"No matching restful call: {(path, kwargs)}"

    class Account(MockSObject):
        pass

    class Contact(MockSObject):
        pass

    class BFG(MockSObject):
        pass


class TestDescribeOrg:
    @pytest.mark.vcr(
        # record_mode="none",
        cassette="foobar"
    )  # don't refresh because true describe is too big
    def test_describe_to_sql(self, sf):
        responses.add(
            "POST",
            "https://innovation-page-2420-dev-ed.cs50.my.salesforce.com/composite",
            status=200,
            json={},
        )
        keychain = DummyKeychain()
        org_config = DummyOrgConfig(keychain=keychain)
        with TemporaryDirectory() as t, patch(
            "cumulusci.tests.util.DummyKeychain.project_cache_dir", Path(t)
        ):
            with get_org_schema(sf, org_config, force_recache=False) as desc:
                assert len(list(desc.sobjects)) == 4
                assert desc["Account"].createable == "True"
                assert desc["Account"].fields["Id"].aggregatable is True

    def test_filtering(self):
        desc = Schema.from_api(
            MockSF(),
            ["Account", "Contact"],
            ["IsDeleted"],
            ["nillable", "nameField", "createable", "deletable"],
        )
        self.shared_filter_tests(desc)

    def shared_filter_tests(self, schema):
        assert "BFG" not in schema.sobjects
        assert len(schema.sobjects) == 2
        assert set(schema["Account"].properties) == {
            "createable",
            "deletable",
            "fields",  # always included
            "name",  # always included
        }  # actionOverrides filtered out
        assert set(schema["Account"].properties.non_default_properties.keys()) == {
            "createable",
            "fields",
            "name",
        }
        assert "IsDeleted" in schema["Account"].fields
        assert "IsDeleted" in schema["Account"]

        assert "Id" not in schema["Account"].fields
        assert (
            schema["Account"].fields["IsDeleted"].properties["nillable"] == "OVERRIDDEN"
        )
        assert schema["Account"].fields["IsDeleted"].nillable == "OVERRIDDEN"
        assert "isSubtype" not in schema["Account"].properties

        assert set(schema["Account"].fields["IsDeleted"].properties.keys()) == set(
            ["nillable", "nameField", "createable", "name"],
        )
        assert schema.to_dict() == {
            "schema_revision": 42,
            "sobjects": [
                {
                    "createable": "OVERRIDDEN",
                    "name": "Account",
                    "fields": [{"name": "IsDeleted", "nillable": "OVERRIDDEN"}],
                },
                {
                    "createable": "OVERRIDDEN",
                    "name": "Contact",
                    "fields": [{"name": "IsDeleted", "nillable": "OVERRIDDEN"}],
                },
            ],
            "sobject_property_defaults": {"createable": False, "deletable": False},
            "field_property_defaults": {
                "createable": False,
                "name": None,
                "nameField": False,
                "nillable": True,
            },
        }

    def test_json(self):
        desc = Schema.from_api(MockSF())

        as_dict = desc.to_dict()
        assert set(as_dict.keys()) == set(
            [
                "sobjects",
                "schema_revision",
                "sobject_property_defaults",
                "field_property_defaults",
            ]
        )

        assert set(obj["name"] for obj in as_dict["sobjects"]) == {
            "Account",
            "BFG",
            "Contact",
        }

        assert set(f["name"] for f in as_dict["sobjects"][0]["fields"]) == {
            "Id",
            "IsDeleted",
        }

        assert set(as_dict["sobjects"][0].keys()) == {
            "createable",
            "name",
            "fields",
            "name",
        }

    def test_json_roundtrip(self):
        desc = Schema.from_api(MockSF())
        data = json.dumps(desc.to_dict())
        assert "Account" in data
        assert "aggregatable" in data
        schema = Schema.from_dict(desc.to_dict())
        assert schema.to_dict() == desc.to_dict()

    def test_filtering_from_roundtrip(self):
        desc = Schema.from_api(MockSF())
        schema = Schema.from_dict(
            desc.to_dict(),
            ["Account", "Contact"],
            ["IsDeleted"],
            ["nillable", "nameField", "createable", "deletable"],
        )
        self.shared_filter_tests(schema)


def reduce_data(filename):
    """A function for reducing Casettes of Describes() to the bare minimum

    Note that the deep_describe infrastructure uses threads and may not
    always play nicely with vcr. It may take some experimentation and cutting
    and pasting to get a decent vcr cassette to use as the input of this
    function."""
    relevant_objs = ["Account", "Contact", "Opportunity", "Campaign"]
    data = yaml.safe_load(open(filename))

    for interaction in data["interactions"]:
        url = interaction["request"].get("uri")
        print(url)
        if url and url.endswith("composite"):
            reduce_composite(interaction)
        elif url:
            print(url)
            assert url.endswith("sobjects"), url
            reduce_describe(interaction, relevant_objs)

    yaml.safe_dump(data, open(filename + ".out.yaml", "w"))


def reduce_composite(interaction):
    results = json.loads(interaction["response"]["body"]["string"])["compositeResponse"]
    sobjs = [result["body"] for result in results]
    for sobj in sobjs:
        sobj["fields"] = sobj["fields"][0:1]
        for key in ["urls", "childRelationships", "recordTypeInfos", "supportedScopes"]:
            if sobj.get(key):
                del sobj[key]

    interaction["response"]["body"]["string"] = json.dumps(
        {"compositeResponse": results}
    )


def reduce_describe(interaction, relevant_objs):
    sobjs = json.loads(interaction["response"]["body"]["string"])["sobjects"]
    results = []
    for sobj in sobjs:
        if sobj["name"] not in relevant_objs:
            print(sobj["name"], end=" ")
            continue
        for key in ["urls", "childRelationships", "recordTypeInfos", "supportedScopes"]:
            if sobj.get(key):
                del sobj[key]
        results.append(sobj)

    interaction["response"]["body"]["string"] = json.dumps({"sobjects": results})
