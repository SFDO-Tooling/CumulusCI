import json

from cumulusci.utils.schema_utils import Schema
from cumulusci.utils.integration_testing.caching import caching_proxy

SHOULD_CACHE = True


class TestDescribeEverything:
    def test_describe_everything(self, sf):
        with caching_proxy(SHOULD_CACHE):
            schema = Schema.from_api(sf)
            objects = schema.sobjects
            assert len(objects) > 600
            assert "Account" in objects
            assert "WorkOrder" in objects
            assert "WorkTypeHistory" in objects
            assert "Role" in objects["AccountContactRole"].fields
            assert objects["AccountContactRole"].properties["retrieveable"]
            assert objects["AccountContactRole"].retrieveable
            assert "calculated" in objects["AccountContactRole"].fields["Id"].properties
            assert objects["AccountContactRole"]["Id"].calculated is False
            assert "fields" not in objects["AccountContactRole"].properties

            assert len(schema.field_property_defaults) > 50
            assert len(schema.sobject_property_defaults) > 35
            assert (
                objects["AccountContactRole"].namedLayoutInfos
                == schema.sobject_property_defaults["namedLayoutInfos"]
            )
            assert len(objects["AccountContactRole"].properties.keys()) > 20

            assert (
                len(
                    objects[
                        "AccountContactRole"
                    ].properties.non_default_properties.keys()
                )
                < 20
            )
            assert (
                len(objects["AccountContactRole"].fields["Id"].properties.keys()) > 50
            )
            assert (
                len(
                    objects["AccountContactRole"]
                    .fields["Id"]
                    .properties.non_default_properties.keys()
                )
                < 20
            )
            assert json.dumps(schema.to_dict())

    def test_describe_filtered(self, sf):
        with caching_proxy(SHOULD_CACHE):
            schema = Schema.from_api(
                sf,
                ["Account", "WorkTypeHistory"],
                ["Name", "Id"],
                ["name", "type", "fields"],
            )
            objects = schema.sobjects
            assert set(obj.name for obj in objects.values()) == set(
                ["Account", "WorkTypeHistory"]
            )
            for obj in objects.values():
                assert "Id" in obj.fields.keys()
                for fieldname, field in obj.fields.items():
                    assert fieldname in ["Name", "Id"]
                    for prop in field.properties.keys():
                        assert prop in ["name", "type", "fields"]
            assert objects["Account"].name == "Account"
            assert objects["Account"].fields["Name"].name == "Name"


class TestDescribeEverythingTask:
    def test_describe_everything_task(self):
        pass
