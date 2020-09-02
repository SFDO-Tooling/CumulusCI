import unittest
from unittest import mock
import responses
import yaml
from tempfile import TemporaryDirectory
from pathlib import Path
from contextlib import contextmanager

import pytest

from cumulusci.tasks.bulkdata import GenerateMapping
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.utils import temporary_dir
from cumulusci.tasks.bulkdata.tests.utils import _make_task

from cumulusci.utils.org_schema_models import SObject as SQLSObject, Field as SQLField


class FakeSchema:
    def __init__(self, models=None, describe_data=None):
        if isinstance(models, list):
            models = {model["name"] for model in models}
            print("List")
        elif models is None:
            assert describe_data is not None
            models = describe_data_2_fake_models(describe_data)
            print("desribe_data")
        self.models = models
        self.keys = self.models.keys
        self.items = self.models.items

    def __getitem__(self, name):
        return self.models[name]

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        pass


class FakeModelObject:
    def __init__(self, dct=None, **kwargs):
        self.__dict__.update(dct or kwargs)

    def __getitem__(self, name):
        return self.__dict__[name]

    def __iter__(self):
        return iter(self.__dict__.keys())

    # def _new_state_if_none(self, *args, **kwargs):
    #     return None

    def __setattr__(self, name, value):
        self.__dict__[name] = value


# class _SObject(FakeModelObject):
#     def __init__(self, name, fields, **kwargs):
#         if isinstance(fields, list):
#             fields = {field["name"]: field for field in fields}
#         FakeModelObject.__init__(
#             self, name=name, fields=fields, customSetting=False, **kwargs
#         )


def _SObject(name, fields, **kwargs):
    assert name
    if isinstance(fields, list):
        fields = {field["name"]: field for field in fields}
    return SQLSObject(name=name, fields=fields, **kwargs)


# class _Field(FakeModelObject):
#     def __init__(self, name: str, **kwargs):
#         FakeModelObject.__init__(self, name=name, **kwargs)


def _Field(name: str, dct=None, **kwargs):
    dct = dct or {}
    kwargs.update(kwargs)
    return SQLField(name=name, **kwargs)


def describe_data_2_fake_models(describe_data):
    def fields_2_fake_model(fields):
        return {field.name: field for field in fields}

    models = {
        name: _SObject(name, **{**m, "fields": fields_2_fake_model(m["fields"])})
        for name, m in describe_data.items()
    }
    return models


class TestMappingGenerator(unittest.TestCase):
    def test_defaults_options(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        self.assertEqual([], t.options["ignore"])
        self.assertEqual("", t.options["namespace_prefix"])
        self.assertEqual("ask", t.options["break_cycles"])
        self.assertEqual([], t.options["include"])

    def test_postfixes_underscores_to_namespace(self):
        t = _make_task(
            GenerateMapping, {"options": {"namespace_prefix": "t", "path": "t"}}
        )

        self.assertEqual("t__", t.options["namespace_prefix"])

    def test_splits_ignore_string(self):
        t = _make_task(
            GenerateMapping, {"options": {"ignore": "Account, Contact", "path": "t"}}
        )

        self.assertEqual(["Account", "Contact"], t.options["ignore"])

    def test_accepts_ignore_list(self):
        t = _make_task(
            GenerateMapping,
            {"options": {"ignore": ["Account", "Contact"], "path": "t"}},
        )

        self.assertEqual(["Account", "Contact"], t.options["ignore"])

    def test_accepts_include_list(self):
        t = _make_task(
            GenerateMapping, {"options": {"include": ["Foo", "Bar"], "path": "t"}}
        )

        self.assertEqual(["Foo", "Bar"], t.options["include"])

    @responses.activate
    def test_checks_include_list(self):
        t = _make_task(
            GenerateMapping, {"options": {"include": ["Foo", "Bar"], "path": "t"}}
        )
        t.project_config.project__package__api_version = "45.0"

        with self._prepare_describe_mock(t, {}):
            t._init_task()

        with pytest.raises(TaskOptionsError):
            t._collect_objects({})

    def test_is_any_custom_api_name(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        self.assertTrue(t._is_any_custom_api_name("Custom__c"))
        self.assertFalse(t._is_any_custom_api_name("Standard"))

    def test_is_our_custom_api_name(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        self.assertTrue(t._is_our_custom_api_name("Custom__c"))
        self.assertFalse(t._is_our_custom_api_name("Standard"))
        self.assertFalse(t._is_our_custom_api_name("t__Custom__c"))
        self.assertFalse(t._is_our_custom_api_name("f__Custom__c"))

        t.options["namespace_prefix"] = "t__"
        self.assertTrue(t._is_our_custom_api_name("Custom__c"))
        self.assertTrue(t._is_our_custom_api_name("t__Custom__c"))
        self.assertFalse(t._is_our_custom_api_name("f__Custom__c"))

    def test_is_core_field(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        self.assertTrue(t._is_core_field("Name"))
        self.assertFalse(t._is_core_field("Custom__c"))

    def test_is_object_mappable(self):
        t = _make_task(GenerateMapping, {"options": {"ignore": "Account", "path": "t"}})

        self.assertTrue(
            t._is_object_mappable({"name": "Contact", "customSetting": False})
        )
        self.assertFalse(
            t._is_object_mappable({"name": "Account", "customSetting": False})
        )
        self.assertFalse(
            t._is_object_mappable(
                {"name": "Contact__ChangeEvent", "customSetting": False}
            )
        )
        self.assertFalse(
            t._is_object_mappable({"name": "Custom__c", "customSetting": True})
        )

    def test_is_field_mappable(self):
        t = _make_task(
            GenerateMapping, {"options": {"ignore": "Account.ParentId", "path": "t"}}
        )

        t.mapping_objects = ["Account", "Contact"]

        self.assertTrue(
            t._is_field_mappable(
                "Account",
                {"name": "Name", "type": "string", "label": "Name", "createable": True},
            )
        )
        self.assertFalse(
            t._is_field_mappable(
                "Account",
                {"name": "Name", "type": "base64", "label": "Name", "createable": True},
            )
        )
        self.assertFalse(
            t._is_field_mappable(
                "Account",
                {
                    "name": "Name",
                    "type": "string",
                    "label": "Name (Deprecated)",
                    "createable": True,
                },
            )
        )
        self.assertFalse(
            t._is_field_mappable(
                "Account",
                {
                    "name": "ParentId",
                    "type": "reference",
                    "label": "Parent",
                    "createable": True,
                    "referenceTo": ["Account"],
                },
            )
        )
        self.assertFalse(
            t._is_field_mappable(
                "Account",
                {
                    "name": "Name",
                    "type": "string",
                    "label": "Name",
                    "createable": False,
                },
            )
        )
        self.assertFalse(
            t._is_field_mappable(
                "Contact",
                {
                    "name": "OwnerId",
                    "type": "reference",
                    "label": "Owner",
                    "createable": True,
                    "referenceTo": ["User", "Group"],
                },
            )
        )

    def test_has_our_custom_fields(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})
        sobject = _SObject("Blah", [_Field(name="CustomObject__c")])
        self.assertTrue(t._has_our_custom_fields(sobject))
        self.assertTrue(
            t._has_our_custom_fields(
                _SObject("Blah", [_Field("Custom__c"), _Field("Standard")])
            )
        )
        self.assertFalse(
            t._has_our_custom_fields(_SObject("Blah", [_Field("Standard")]))
        )
        self.assertFalse(t._has_our_custom_fields(_SObject("Blah", [])))

    def test_is_lookup_to_included_object(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account"]

        self.assertTrue(
            t._is_lookup_to_included_object(
                {"type": "reference", "referenceTo": ["Account"]}
            )
        )
        self.assertFalse(
            t._is_lookup_to_included_object(
                {"type": "reference", "referenceTo": ["Contact"]}
            )
        )
        self.assertFalse(
            t._is_lookup_to_included_object(
                {"type": "reference", "referenceTo": ["Account", "Contact"]}
            )
        )

    @contextmanager
    def _prepare_describe_mock(self, task, describe_data):
        with mock.patch(
            "cumulusci.tasks.bulkdata.generate_mapping.get_org_schema",
            lambda *args, **kwargs: fake_schema,
        ):
            fake_schema = FakeSchema(describe_data=describe_data)
            yield fake_schema

    def _mock_field(self, name, field_type="string", **kwargs):
        field_data = {
            "name": name,
            "type": field_type,
            "createable": True,
            "nillable": True,
            "label": name,
        }
        field_data.update(kwargs)
        return _Field(**field_data)

    @responses.activate
    def test_run_task(self):
        t = _make_task(GenerateMapping, {"options": {"path": "mapping.yaml"}})
        t.project_config.project__package__api_version = "45.0"
        describe_data = {
            "Parent": {
                "fields": [self._mock_field("Id"), self._mock_field("Custom__c")]
            },
            "Child__c": {
                "fields": [
                    self._mock_field("Id"),
                    self._mock_field(
                        "Account__c",
                        field_type="reference",
                        referenceTo=["Parent"],
                        relationshipOrder=None,
                    ),
                ]
            },
        }

        with temporary_dir(), self._prepare_describe_mock(t, describe_data):
            t()

            with open("mapping.yaml", "r") as fh:
                content = yaml.safe_load(fh)

            self.assertEqual(["Insert Parent", "Insert Child__c"], list(content.keys()))
            self.assertEqual("Parent", t.mapping["Insert Parent"]["sf_object"])
            self.assertEqual(["Custom__c"], t.mapping["Insert Parent"]["fields"])

            self.assertEqual("Child__c", t.mapping["Insert Child__c"]["sf_object"])
            assert "fields" not in t.mapping["Insert Child__c"]
            self.assertEqual(
                ["Account__c"], list(t.mapping["Insert Child__c"]["lookups"].keys())
            )
            self.assertEqual(
                "Parent", t.mapping["Insert Child__c"]["lookups"]["Account__c"]["table"]
            )

    @responses.activate
    def test_collect_objects__simple_custom_objects(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})
        t.project_config.project__package__api_version = "45.0"

        describe_data = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "Contact": {"fields": [self._mock_field("Name")]},
            "Custom__c": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "User": {"fields": [self._mock_field("Name")]},
        }

        with self._prepare_describe_mock(t, describe_data) as schema:
            t._init_task()
            t._collect_objects(schema)

        self.assertEqual(set(["Account", "Custom__c"]), set(t.mapping_objects))

    @responses.activate
    def test_collect_objects__force_include_objects(self):
        t = _make_task(
            GenerateMapping, {"options": {"path": "t", "include": ["Contact", "User"]}}
        )
        t.project_config.project__package__api_version = "45.0"

        describe_data = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "Contact": {"fields": [self._mock_field("Name")]},
            "Custom__c": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "User": {"fields": [self._mock_field("Name")]},
        }

        with self._prepare_describe_mock(t, describe_data) as schema:
            t._init_task()
            t._collect_objects(schema)

        self.assertEqual(
            set(["Account", "Custom__c", "Contact", "User"]), set(t.mapping_objects)
        )

    @responses.activate
    def test_collect_objects__force_include_objects__already_included(self):
        t = _make_task(
            GenerateMapping,
            {"options": {"path": "t", "include": ["Contact", "Custom__c"]}},
        )
        t.project_config.project__package__api_version = "45.0"

        describe_data = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "Contact": {"fields": [self._mock_field("Name")]},
            "Custom__c": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "User": {"fields": [self._mock_field("Name")]},
        }

        with self._prepare_describe_mock(t, describe_data) as schema:
            t._init_task()
            t._collect_objects(schema)
        assert len(t.mapping_objects) == 3

        self.assertEqual(
            set(["Account", "Custom__c", "Contact"]), set(t.mapping_objects)
        )

    @responses.activate
    def test_collect_objects__custom_lookup_fields(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})
        t.project_config.project__package__api_version = "45.0"

        describe_data = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "Contact": {"fields": [self._mock_field("Name")]},
            "Custom__c": {
                "fields": [
                    self._mock_field("Name"),
                    self._mock_field("Custom__c"),
                    self._mock_field(
                        "Lookup__c",
                        field_type="reference",
                        relationshipOrder=None,
                        referenceTo=["Contact"],
                    ),
                ]
            },
        }

        with self._prepare_describe_mock(t, describe_data) as schema:
            t._init_task()
            t._collect_objects(schema)

        self.assertEqual(
            set(["Account", "Custom__c", "Contact"]), set(t.mapping_objects)
        )

    @responses.activate
    def test_collect_objects__master_detail_fields(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})
        t.project_config.project__package__api_version = "45.0"

        describe_data = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "Opportunity": {"fields": [self._mock_field("Name")]},
            "OpportunityLineItem": {
                "fields": [
                    self._mock_field("Name"),
                    self._mock_field("Custom__c"),
                    self._mock_field(
                        "OpportunityId",
                        field_type="reference",
                        relationshipOrder=1,
                        referenceTo=["Opportunity"],
                    ),
                ]
            },
        }

        with self._prepare_describe_mock(t, describe_data) as schema:
            t._init_task()
            t._collect_objects(schema)

        self.assertEqual(
            set(["Account", "OpportunityLineItem", "Opportunity"]),
            set(t.mapping_objects),
        )

    @responses.activate
    def test_collect_objects__duplicate_references(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})
        t.project_config.project__package__api_version = "45.0"

        describe_data = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "Opportunity": {"fields": [self._mock_field("Name")]},
            "OpportunityLineItem": {
                "fields": [
                    self._mock_field("Name"),
                    self._mock_field("Custom__c"),
                    self._mock_field(
                        "OpportunityId",
                        field_type="reference",
                        relationshipOrder=1,
                        referenceTo=["Opportunity"],
                    ),
                    self._mock_field(
                        "CustomLookup__c",
                        field_type="reference",
                        relationshipOrder=None,
                        referenceTo=["Opportunity"],
                    ),
                ]
            },
        }

        with self._prepare_describe_mock(t, describe_data) as schema:
            t._init_task()
            t._collect_objects(schema)

        self.assertEqual(
            set(["Account", "OpportunityLineItem", "Opportunity"]),
            set(t.mapping_objects),
        )

    def test_build_schema(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account", "Opportunity", "Child__c"]
        stage_name = self._mock_field("StageName", {"nillable": False})

        describe_data = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Industry")]
            },
            "Opportunity": {"fields": [self._mock_field("Name"), stage_name]},
            "Child__c": {
                "fields": [
                    self._mock_field("Name"),
                    self._mock_field("Test__c"),
                    self._mock_field("Attachment__c", field_type="base64"),
                ]
            },
        }
        with self._prepare_describe_mock(t, describe_data) as org_schema:
            t._build_schema(org_schema)
        self.maxDiff = None
        self.assertEqual(
            {
                "Account": {"Name": self._mock_field("Name")},
                "Opportunity": {
                    "Name": self._mock_field("Name"),
                    "StageName": stage_name,
                },
                "Child__c": {
                    "Name": self._mock_field("Name"),
                    "Test__c": self._mock_field("Test__c"),
                },
            },
            t.simple_schema,
        )

    def test_build_schema__tracks_references(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account", "Opportunity"]
        describe_data = {
            "Account": {"fields": [self._mock_field("Name")]},
            "Opportunity": {
                "fields": [
                    self._mock_field("Name"),
                    self._mock_field(
                        "AccountId",
                        field_type="reference",
                        referenceTo=["Account"],
                        relationshipOrder=1,
                    ),
                ]
            },
        }
        with self._prepare_describe_mock(t, describe_data) as org_schema:
            t._build_schema(org_schema)

        self.assertEqual(
            {
                "Opportunity": {
                    "Account": {"AccountId": _Field("AccountId", nillable=True)}
                }
            },
            dict(t.refs),
        )

    def test_build_schema__includes_recordtypeid(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account", "Opportunity"]
        describe_data = {
            "Account": {"fields": [self._mock_field("Name")]},
            "Opportunity": {
                "fields": [
                    self._mock_field("Name"),
                    self._mock_field(
                        "AccountId",
                        field_type="reference",
                        referenceTo=["Account"],
                        relationshipOrder=1,
                    ),
                    self._mock_field("RecordTypeId"),
                ],
                "recordTypeInfos": [{"Name": "Master"}, {"Name": "Donation"}],
            },
        }
        with self._prepare_describe_mock(t, describe_data) as org_schema:
            t._build_schema(org_schema)
        self.assertIn("RecordTypeId", t.simple_schema["Opportunity"])
        self.assertNotIn("RecordTypeId", t.simple_schema["Account"])

    @mock.patch("click.prompt")
    def test_build_mapping(self, prompt):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})
        prompt.return_value = "Account"

        t.simple_schema = {
            "Account": {
                "Name": self._mock_field("Name"),
                "Dependent__c": self._mock_field(
                    "Dependent__c", field_type="reference", referenceTo=["Child__c"]
                ),
            },
            "Child__c": {
                "Name": self._mock_field("Name"),
                "Account__c": self._mock_field(
                    "Account__c", field_type="reference", referenceTo=["Account"]
                ),
                "Self__c": self._mock_field(
                    "Self__c", field_type="reference", referenceTo=["Child__c"]
                ),
            },
        }
        t.refs = {
            "Child__c": {
                "Account": {"Account__c": _Field("Account__c", {"nillable": True})}
            },
            "Account": {
                "Child__c": {"Dependent__c": _Field("Dependent__c", {"nillable": True})}
            },
        }

        t._build_mapping()
        self.assertEqual(["Insert Account", "Insert Child__c"], list(t.mapping.keys()))
        self.assertEqual("Account", t.mapping["Insert Account"]["sf_object"])
        self.assertEqual(["Name"], t.mapping["Insert Account"]["fields"])
        self.assertEqual(
            ["Dependent__c"], list(t.mapping["Insert Account"]["lookups"].keys())
        )
        self.assertEqual(
            "Child__c", t.mapping["Insert Account"]["lookups"]["Dependent__c"]["table"]
        )

        self.assertEqual("Child__c", t.mapping["Insert Child__c"]["sf_object"])
        self.assertEqual(["Name"], t.mapping["Insert Child__c"]["fields"])
        self.assertEqual(
            ["Account__c", "Self__c"],
            list(t.mapping["Insert Child__c"]["lookups"].keys()),
        )
        self.assertEqual(
            "Account", t.mapping["Insert Child__c"]["lookups"]["Account__c"]["table"]
        )
        self.assertEqual(
            "Child__c", t.mapping["Insert Child__c"]["lookups"]["Self__c"]["table"]
        )

    @mock.patch("click.prompt")
    def test_build_mapping__strip_namespace(self, prompt):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})
        t.project_config.project__package__namespace = "ns"
        prompt.return_value = "ns__Parent__c"

        t.simple_schema = {
            "ns__Parent__c": {
                "Name": self._mock_field("Name"),
                "ns__Dependent__c": self._mock_field(
                    "ns__Dependent__c",
                    field_type="reference",
                    referenceTo=["ns__Child__c"],
                ),
            },
            "ns__Child__c": {
                "Name": self._mock_field("Name"),
                "ns__Parent__c": self._mock_field(
                    "ns__Parent__c",
                    field_type="reference",
                    referenceTo=["ns__Parent__c"],
                ),
                "ns__Self__c": self._mock_field(
                    "ns__Self__c", field_type="reference", referenceTo=["ns__Child__c"]
                ),
            },
        }
        t.refs = {
            "ns__Child__c": {
                "ns__Parent__c": {
                    "ns__Parent__c": _Field("ns__Parent__c", {"nillable": False})
                }
            },
            "ns__Parent__c": {
                "ns__Child__c": {
                    "ns__Dependent__c": _Field("ns__Dependent__c", {"nillable": True})
                }
            },
        }

        t._build_mapping()
        self.assertEqual(
            ["Insert Parent__c", "Insert Child__c"], list(t.mapping.keys())
        )
        self.assertEqual("Parent__c", t.mapping["Insert Parent__c"]["sf_object"])
        self.assertEqual(["Name"], t.mapping["Insert Parent__c"]["fields"])
        self.assertEqual(
            ["Dependent__c"], list(t.mapping["Insert Parent__c"]["lookups"].keys())
        )
        self.assertEqual(
            "Child__c",
            t.mapping["Insert Parent__c"]["lookups"]["Dependent__c"]["table"],
        )

        self.assertEqual("Child__c", t.mapping["Insert Child__c"]["sf_object"])
        self.assertEqual(["Name"], t.mapping["Insert Child__c"]["fields"])
        self.assertEqual(
            ["Parent__c", "Self__c"],
            list(t.mapping["Insert Child__c"]["lookups"].keys()),
        )
        self.assertEqual(
            "Parent__c", t.mapping["Insert Child__c"]["lookups"]["Parent__c"]["table"]
        )
        self.assertEqual(
            "Child__c", t.mapping["Insert Child__c"]["lookups"]["Self__c"]["table"]
        )

    @mock.patch("click.prompt")
    def test_build_mapping__no_strip_namespace_if_dup_component(self, prompt):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})
        t.project_config.project__package__namespace = "ns"
        prompt.return_value = "ns__Parent__c"

        t.simple_schema = {
            "ns__Parent__c": {"Name": self._mock_field("Name")},
            "ns__Child__c": {
                "Name": self._mock_field("Name"),
                "Test__c": self._mock_field("Test__c"),
                "ns__Test__c": self._mock_field("ns__Test__c"),
                "ns__Parent__c": self._mock_field(
                    "ns__Parent__c",
                    field_type="reference",
                    referenceTo=["ns__Parent__c"],
                ),
                "Parent__c": self._mock_field(
                    "Parent__c", field_type="reference", referenceTo=["ns__Child__c"]
                ),
            },
            "Child__c": {"Name": self._mock_field("Name")},
        }
        t.refs = {
            "ns__Child__c": {
                "ns__Parent__c": {"ns__Parent__c": _Field("ns__Parent__c", {})}
            }
        }

        t._build_mapping()

        self.assertEqual(
            set(["Insert Parent__c", "Insert ns__Child__c", "Insert Child__c"]),
            set(t.mapping.keys()),
        )

        self.assertEqual("ns__Child__c", t.mapping["Insert ns__Child__c"]["sf_object"])
        self.assertEqual(
            ["Name", "Test__c", "ns__Test__c"],
            t.mapping["Insert ns__Child__c"]["fields"],
        )
        self.assertEqual(
            set(["ns__Parent__c", "Parent__c"]),
            set(t.mapping["Insert ns__Child__c"]["lookups"].keys()),
        )
        self.assertEqual(
            "Parent__c",
            t.mapping["Insert ns__Child__c"]["lookups"]["ns__Parent__c"]["table"],
        )
        self.assertEqual(
            "ns__Child__c",
            t.mapping["Insert ns__Child__c"]["lookups"]["Parent__c"]["table"],
        )

        self.assertEqual("Child__c", t.mapping["Insert Child__c"]["sf_object"])
        self.assertEqual(["Name"], t.mapping["Insert Child__c"]["fields"])

    def test_build_mapping__warns_polymorphic_lookups(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account", "Contact", "Custom__c"]
        t.simple_schema = {
            "Account": {"Name": self._mock_field("Name")},
            "Contact": {"Name": self._mock_field("Name")},
            "Custom__c": {
                "Name": self._mock_field("Name"),
                "PolyLookup__c": self._mock_field(
                    "PolyLookup__c",
                    field_type="reference",
                    referenceTo=["Account", "Contact"],
                ),
            },
        }
        t.refs = {
            "Custom__c": {
                "Account": {"PolyLookup__c": _Field("PolyLookup__c", {})},
                "Contact": {"PolyLookup__c": _Field("PolyLookup__c", {})},
            }
        }
        t.logger = mock.Mock()

        t._build_mapping()
        t.logger.warning.assert_called_once_with(
            "Field Custom__c.PolyLookup__c is a polymorphic lookup, which is not supported"
        )

    def test_split_dependencies__no_cycles(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        stack = t._split_dependencies(
            ["Account", "Contact", "Opportunity", "Custom__c"],
            {
                "Contact": {"Account": {"AccountId": _Field("AccountId", {})}},
                "Opportunity": {
                    "Account": {"AccountId": _Field("AccountId", {})},
                    "Contact": {"Primary_Contact__c": _Field("Primary_Contact__c", {})},
                },
                "Custom__c": {
                    "Account": {"Account__c": _Field("Account__c", {})},
                    "Contact": {"Contact__c": _Field("Contact__c", {})},
                    "Opportunity": {"Opp__c": _Field("Opp__c", {})},
                },
            },
        )

        self.assertEqual(["Account", "Contact", "Opportunity", "Custom__c"], stack)

    @mock.patch("click.prompt")
    def test_split_dependencies__interviews_for_cycles(self, prompt):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        prompt.return_value = "Account"

        self.assertEqual(
            ["Custom__c", "Account", "Contact", "Opportunity"],
            t._split_dependencies(
                ["Account", "Contact", "Opportunity", "Custom__c"],
                {
                    "Account": {
                        "Contact": {
                            "Primary_Contact__c": _Field(
                                "Primary_Contact__c", {"nillable": True}
                            )
                        }
                    },
                    "Contact": {
                        "Account": {
                            "AccountId": _Field("AccountId", {"nillable": True})
                        }
                    },
                    "Opportunity": {
                        "Account": {
                            "AccountId": _Field("AccountId", {"nillable": True})
                        },
                        "Contact": {
                            "Primary_Contact__c": _Field(
                                "Primary_Contact__c", {"nillable": True}
                            )
                        },
                    },
                },
            ),
        )

    @mock.patch("click.prompt")
    @mock.patch("random.choice")
    def test_split_dependencies__auto_pick_cycles_priortize_Account(
        self, choice, prompt
    ):
        t = _make_task(
            GenerateMapping, {"options": {"path": "t", "break_cycles": "auto"}}
        )

        prompt.side_effect = AssertionError("Shouldn't be called")
        choice.side_effect = AssertionError("Shouldn't be called")
        split_dependencies = t._split_dependencies(
            ["Account", "Contact", "Opportunity", "Custom__c"],
            {
                "Account": {
                    "Contact": {
                        "Primary_Contact__c": _Field(
                            "Primary_Contact__c", {"nillable": False}
                        )
                    }
                },
                "Contact": {
                    "Account": {"AccountId": _Field("AccountId", {"nillable": False})}
                },
                "Opportunity": {
                    "Account": {"AccountId": _Field("AccountId", {"nillable": False})},
                    "Contact": {
                        "Primary_Contact__c": _Field(
                            "Primary_Contact__c", {"nillable": False}
                        )
                    },
                },
            },
        )

        self.assertEqual(
            ["Custom__c", "Account", "Contact", "Opportunity"], split_dependencies
        )
        assert not choice.mock_calls

    @mock.patch("click.prompt")
    def test_split_dependencies__auto_pick_cycles_randomly(self, prompt):
        t = _make_task(
            GenerateMapping, {"options": {"path": "t", "break_cycles": "auto"}}
        )

        prompt.side_effect = AssertionError("Shouldn't be called")
        split_dependencies = t._split_dependencies(
            ["Account", "Contact", "Opportunity", "Custom__c"],
            {
                "Account": {
                    "Custom__c": {
                        "Non_Nillable_Custom__c": _Field(
                            "Non_Nillable_Custom__c", {"nillable": False}
                        )
                    }
                },
                "Custom__c": {
                    "Account": {"AccountId": _Field("AccountId", {"nillable": False})}
                },
            },
        )

        self.assertEqual(
            ["Contact", "Opportunity", "Account", "Custom__c"], split_dependencies
        )

    @mock.patch("click.prompt")
    @mock.patch("random.choice")
    def test_split_dependencies__auto_pick_cycles_by_relationship_type(
        self, random_choice, prompt
    ):
        t = _make_task(
            GenerateMapping, {"options": {"path": "t", "break_cycles": "auto"}}
        )

        prompt.side_effect = AssertionError("Shouldn't be called")
        random_choice.side_effect = AssertionError("Shouldn't be called")

        split_dependencies = t._split_dependencies(
            ["AccountLike__c", "ContactLike__c", "OpportunityLike__c", "Custom__c"],
            {
                # Primary_Contact__c is not nillable, so ContactLike__c must be loaded before
                # AccountLike__c despite the cycle
                "AccountLike__c": {
                    "ContactLike__c": {
                        "Primary_Contact__c": _Field(
                            "Primary_Contact__c", nillable=False
                        )
                    }
                },
                "ContactLike__c": {
                    "AccountLike__c": {
                        "AccountId": _Field("AccountLike__c", nillable=True)
                    }
                },
                "OpportunityLike__c": {
                    "AccountLike__c": {
                        "AccountId": _Field("AccountLike__c", nillable=True)
                    },
                    "ContactLike__c": {
                        "Primary_Contact__c": _Field("AccountLike__c", nillable=True)
                    },
                },
            },
        )

        self.assertEqual(
            ["Custom__c", "ContactLike__c", "AccountLike__c", "OpportunityLike__c"],
            split_dependencies,
        )
        random_choice.assert_not_called()

    @mock.patch("click.prompt")
    def test_split_dependencies__auto_pick_cycles(self, prompt):
        t = _make_task(
            GenerateMapping, {"options": {"path": "t", "break_cycles": "auto"}}
        )

        prompt.return_value = AssertionError("Shouldn't be called")

        self.assertEqual(
            set(["Custom__c", "Account", "Contact", "Opportunity"]),
            set(
                t._split_dependencies(
                    ["Account", "Contact", "Opportunity", "Custom__c"],
                    {
                        "Account": {
                            "Contact": {
                                "Primary_Contact__c": _Field(
                                    "Primary_Contact__c", {"nillable": True}
                                )
                            }
                        },
                        "Contact": {
                            "Account": {
                                "AccountId": _Field("AccountId", {"nillable": True})
                            }
                        },
                        "Opportunity": {
                            "Account": {
                                "AccountId": _Field("AccountId", {"nillable": True})
                            },
                            "Contact": {
                                "Primary_Contact__c": _Field(
                                    "Primary_Contact__c", {"nillable": True}
                                )
                            },
                        },
                    },
                )
            ),
        )

    @mock.patch("click.prompt")
    def test_split_dependencies__ask_pick_cycles(self, prompt):
        t = _make_task(
            GenerateMapping, {"options": {"path": "t", "break_cycles": "ask"}}
        )
        prompt.return_value = "Custom__c"

        self.assertEqual(
            set(["Custom__c", "Account", "Contact", "Opportunity"]),
            set(
                t._split_dependencies(
                    ["Account", "Contact", "Opportunity", "Custom__c"],
                    {
                        "Account": {
                            "Custom__c": {
                                "Custom__c": _Field("Custom__c", {"nillable": False})
                            }
                        },
                        "Custom__c": {
                            "Account": {
                                "Account__c": _Field("Account__c", {"nillable": False})
                            }
                        },
                    },
                )
            ),
        )

        prompt.assert_called_once()
        assert prompt.mock_calls

    def test_options_error(self):
        with pytest.raises(TaskOptionsError):
            _make_task(
                GenerateMapping, {"options": {"path": "t", "break_cycles": "foo"}}
            )


@pytest.mark.integration_test()
class TestIntegrationGenerateMapping:
    @pytest.mark.vcr()
    def test_simple_generate(self, create_task):
        "Generate a mapping against a provided org."
        with TemporaryDirectory() as t:
            tempfile = Path(t) / "tempfile.mapping.yml"

            task = create_task(GenerateMapping, {"path": tempfile})
            assert not Path(tempfile).exists()
            task()
            assert Path(tempfile).exists()

    @pytest.mark.vcr()
    def test_generate_with_cycles(self, create_task):
        "Generate a mapping that necessarily includes some reference cycles"
        with TemporaryDirectory() as t:
            tempfile = Path(t) / "tempfile.mapping.yml"

            task = create_task(
                GenerateMapping,
                {
                    "path": tempfile,
                    "include": [
                        "Account",
                        "Contact",
                        "Opportunity",
                        "OpportunityContactRole",
                    ],
                },
            )
            assert not Path(tempfile).exists()
            task()
            assert Path(tempfile).exists()

    @pytest.mark.vcr()
    def test_big_generate(self, create_task, sf):
        "Generate a large mapping that includes every reachable object"
        with TemporaryDirectory() as t:
            tempfile = Path(t) / "tempfile.mapping.yml"

            every_obj = [obj["name"] for obj in sf.describe()["sobjects"]]

            task = create_task(
                GenerateMapping, {"path": tempfile, "include": every_obj}
            )
            assert not Path(tempfile).exists()
            task()
            assert Path(tempfile).exists()
