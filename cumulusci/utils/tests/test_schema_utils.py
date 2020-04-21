import json

from cumulusci.utils.schema_utils import Schema


class MockSF:
    def describe(self):
        return {
            "encoding": "UTF-8",
            "maxBatchSize": 200,
            "sobjects": [
                {"createable": False, "deletable": True, "name": "Account"},
                {"createable": False, "deletable": True, "name": "Contact"},
                {"createable": False, "deletable": True, "name": "BFG"},
            ],
        }

    @staticmethod
    def restful(sobj, method):
        return {
            "actionOverrides": [],
            "createable": "OVERRIDDEN",
            "deletable": False,
            "name": sobj,
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

    class Account:
        @staticmethod
        def describe():
            return MockSF.restful("Account", "GET")

    class Contact:
        @staticmethod
        def describe():
            return MockSF.restful("Contact", "GET")

    class BFG:
        @staticmethod
        def describe():
            return MockSF.restful("BFG", "GET")


class TestDescribeOrg:
    def test_compression(self):
        desc = Schema.from_api(MockSF())
        assert len(desc.sobjects) == 3
        assert desc["Account"].properties["createable"] == "OVERRIDDEN"
        assert desc["Account"].properties.non_default_properties.keys() == {
            "createable",
            "fields",
            "name",
        }

        assert "deleteable" not in desc["Account"].properties

        assert "aggregatable" in desc["Account"]["Id"].properties
        assert "aggregatable" in desc["Account"]["Id"].properties.non_default_properties
        assert "aggregatable" in desc["Account"]["IsDeleted"].properties
        assert (
            "aggregatable"
            not in desc["Account"]["IsDeleted"].properties.non_default_properties
        )

        assert (
            desc["Account"].properties.non_default_properties["createable"]
            == "OVERRIDDEN"
        )
        assert desc["Account"]["Id"].properties["aggregatable"] is True
        assert desc["Account"]["Id"].aggregatable is True

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
        assert schema["Account"]["IsDeleted"].properties["nillable"] == "OVERRIDDEN"
        assert schema["Account"]["IsDeleted"].nillable == "OVERRIDDEN"
        assert "isSubtype" not in schema["Account"].properties

        assert set(schema["Account"]["IsDeleted"].properties.keys()) == set(
            ["nillable", "nameField", "createable", "name"],
        )
        assert schema.to_dict() == {
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
            ["sobjects", "sobject_property_defaults", "field_property_defaults"]
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
