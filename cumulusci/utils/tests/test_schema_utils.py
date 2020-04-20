import json

from cumulusci.utils.schema_utils import Schema


class MockSF:
    def describe(self):
        return {
            "encoding": "UTF-8",
            "maxBatchSize": 200,
            "sobjects": [
                {"activateable": False, "createable": True, "name": "Account"},
                {"activateable": False, "createable": True, "name": "Contact"},
                {"activateable": False, "createable": True, "name": "BFG"},
            ],
        }

    def restful(self, path, method):
        return {
            "actionOverrides": [],
            "activateable": "OVERRIDDEN",
            "fields": [
                {
                    "aggregatable": True,
                    "name": "Id",
                    "nameField": False,
                    "namePointing": False,
                    "nillable": False,
                },
                {
                    "aggregatable": False,
                    "name": "IsDeleted",
                    "nameField": False,
                    "namePointing": False,
                    "nillable": False,
                },
            ],
        }


class TestDescribeOrg:
    def test_compression(self):
        desc = Schema.from_api(MockSF())
        assert len(desc.sobjects) == 3
        assert "createable" in desc["Account"].properties
        assert "createable" not in desc["Account"].properties.non_default_properties

        assert "aggregatable" in desc["Account"]["Id"].properties
        assert "aggregatable" in desc["Account"]["Id"].properties.non_default_properties
        assert "aggregatable" in desc["Account"]["IsDeleted"].properties
        assert (
            "aggregatable"
            not in desc["Account"]["IsDeleted"].properties.non_default_properties
        )

        assert len(desc["Account"].properties.non_default_properties) == 1
        assert (
            desc["Account"].properties.non_default_properties["activateable"]
            == "OVERRIDDEN"
        )

    def test_filtering(self):
        desc = Schema.from_api(
            MockSF(), ["Account", "Contact"], ["IsDeleted"], ["nillable", "nameField"]
        )
        assert "BFG" not in desc.sobjects
        assert len(desc.sobjects) == 2
        assert (
            len(desc["Account"].properties) == 0
        )  # no extra properties due to filtering
        assert not len(desc["Account"].properties.non_default_properties)
        assert "IsDeleted" in desc["Account"].fields
        assert "IsDeleted" in desc["Account"]

        assert "Id" not in desc["Account"].fields
        assert desc["Account"]["IsDeleted"].properties["nillable"] is False
        assert desc["Account"]["IsDeleted"].nillable is False
        assert (
            "name" not in desc["Account"]["IsDeleted"].properties.non_default_properties
        )
        assert "name" not in desc["Account"]["IsDeleted"].properties
        assert "activateable" not in desc["Account"].properties

        assert set(desc["Account"]["IsDeleted"].properties.keys()) == set(
            ["nillable", "nameField"]
        )

    def test_json(self):
        desc = Schema.from_api(MockSF())

        as_dict = desc.to_dict()
        assert set(as_dict.keys()) == set(
            ["sobjects", "sobject_property_defaults", "field_property_defaults"]
        )

        assert set(as_dict["sobjects"].keys()) == set(["Account", "BFG", "Contact"])

        assert set(as_dict["sobjects"]["Account"]["fields"].keys()) == set(
            ["Id", "IsDeleted"]
        )

        assert set(as_dict["sobjects"]["Account"]["properties"].keys()) == set(
            ["activateable"]
        )

    def test_json_roundtrip(self):
        desc = Schema.from_api(MockSF())
        data = json.dumps(desc.to_dict())
        assert "Account" in data
        assert "aggregatable" in data
        schema = Schema.from_dict(desc.to_dict())
        assert schema.to_dict() == desc.to_dict()
