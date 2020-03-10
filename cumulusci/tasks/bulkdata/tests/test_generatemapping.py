import json
import unittest
from unittest import mock
import responses
import yaml

from cumulusci.tasks.bulkdata import GenerateMapping
from cumulusci.utils import temporary_dir
from cumulusci.tasks.bulkdata.tests.utils import _make_task


class TestMappingGenerator(unittest.TestCase):
    def test_defaults_options(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        self.assertEqual([], t.options["ignore"])
        self.assertEqual("", t.options["namespace_prefix"])

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

        self.assertTrue(t._is_core_field("Id"))
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

        self.assertTrue(t._has_our_custom_fields({"fields": [{"name": "Custom__c"}]}))
        self.assertTrue(
            t._has_our_custom_fields(
                {"fields": [{"name": "Custom__c"}, {"name": "Standard"}]}
            )
        )
        self.assertFalse(t._has_our_custom_fields({"fields": [{"name": "Standard"}]}))
        self.assertFalse(t._has_our_custom_fields({"fields": []}))

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

    def _prepare_describe_mock(self, task, describe_data):
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v45.0/sobjects",
            body=json.dumps(
                {
                    "sobjects": [
                        {"name": s, "customSetting": False} for s in describe_data
                    ]
                }
            ),
            status=200,
        )
        for s in describe_data:
            body = {"name": s, "customSetting": False}
            body.update(describe_data[s])
            responses.add(
                method="GET",
                url=f"{task.org_config.instance_url}/services/data/v45.0/sobjects/{s}/describe",
                body=json.dumps(body),
                status=200,
            )

    def _mock_field(self, name, field_type="string", **kwargs):
        field_data = {
            "name": name,
            "type": field_type,
            "createable": True,
            "nillable": True,
            "label": name,
        }
        field_data.update(kwargs)
        return field_data

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

        self._prepare_describe_mock(t, describe_data)
        with temporary_dir():
            t()

            with open("mapping.yaml", "r") as fh:
                content = yaml.safe_load(fh)

            self.assertEqual(["Insert Parent", "Insert Child__c"], list(content.keys()))
            self.assertEqual("Parent", t.mapping["Insert Parent"]["sf_object"])
            self.assertEqual("Parent", t.mapping["Insert Parent"]["table"])
            self.assertEqual(
                ["Id", "Custom__c"], list(t.mapping["Insert Parent"]["fields"].keys())
            )
            self.assertEqual("sf_id", t.mapping["Insert Parent"]["fields"]["Id"])
            self.assertEqual(
                "Custom__c", t.mapping["Insert Parent"]["fields"]["Custom__c"]
            )

            self.assertEqual("Child__c", t.mapping["Insert Child__c"]["sf_object"])
            self.assertEqual("Child__c", t.mapping["Insert Child__c"]["table"])
            self.assertEqual(
                ["Id"], list(t.mapping["Insert Child__c"]["fields"].keys())
            )
            self.assertEqual(
                ["Account__c"], list(t.mapping["Insert Child__c"]["lookups"].keys())
            )
            self.assertEqual("sf_id", t.mapping["Insert Child__c"]["fields"]["Id"])
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
        }

        self._prepare_describe_mock(t, describe_data)
        t._init_task()
        t._collect_objects()

        self.assertEqual(set(["Account", "Custom__c"]), set(t.mapping_objects))

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

        self._prepare_describe_mock(t, describe_data)
        t._init_task()
        t._collect_objects()

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

        self._prepare_describe_mock(t, describe_data)
        t._init_task()
        t._collect_objects()

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

        self._prepare_describe_mock(t, describe_data)
        t._init_task()
        t._collect_objects()

        self.assertEqual(
            set(["Account", "OpportunityLineItem", "Opportunity"]),
            set(t.mapping_objects),
        )

    def test_build_schema(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account", "Opportunity", "Child__c"]
        stage_name = self._mock_field("StageName")
        stage_name["nillable"] = False
        t.describes = {
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

        t._build_schema()
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
            t.schema,
        )

    def test_build_schema__tracks_references(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account", "Opportunity"]
        t.describes = {
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

        t._build_schema()
        self.assertEqual({"Opportunity": {"Account": set(["AccountId"])}}, t.refs)

    def test_build_schema__includes_recordtypeid(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account", "Opportunity"]
        t.describes = {
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

        t._build_schema()
        self.assertIn("RecordTypeId", t.schema["Opportunity"])
        self.assertNotIn("RecordTypeId", t.schema["Account"])

    @mock.patch("click.prompt")
    def test_build_mapping(self, prompt):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})
        prompt.return_value = "Account"

        t.schema = {
            "Account": {
                "Id": self._mock_field("Id"),
                "Name": self._mock_field("Name"),
                "Dependent__c": self._mock_field(
                    "Dependent__c", field_type="reference", referenceTo=["Child__c"]
                ),
            },
            "Child__c": {
                "Id": self._mock_field("Id"),
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
            "Child__c": {"Account": set(["Account__c"])},
            "Account": {"Child__c": set(["Dependent__c"])},
        }

        t._build_mapping()
        self.assertEqual(["Insert Account", "Insert Child__c"], list(t.mapping.keys()))
        self.assertEqual("Account", t.mapping["Insert Account"]["sf_object"])
        self.assertEqual("Account", t.mapping["Insert Account"]["table"])
        self.assertEqual(
            ["Id", "Name"], list(t.mapping["Insert Account"]["fields"].keys())
        )
        self.assertEqual("sf_id", t.mapping["Insert Account"]["fields"]["Id"])
        self.assertEqual("Name", t.mapping["Insert Account"]["fields"]["Name"])
        self.assertEqual(
            ["Dependent__c"], list(t.mapping["Insert Account"]["lookups"].keys())
        )
        self.assertEqual(
            "Child__c", t.mapping["Insert Account"]["lookups"]["Dependent__c"]["table"]
        )

        self.assertEqual("Child__c", t.mapping["Insert Child__c"]["sf_object"])
        self.assertEqual("Child__c", t.mapping["Insert Child__c"]["table"])
        self.assertEqual(
            ["Id", "Name"], list(t.mapping["Insert Child__c"]["fields"].keys())
        )
        self.assertEqual(
            ["Account__c", "Self__c"],
            list(t.mapping["Insert Child__c"]["lookups"].keys()),
        )
        self.assertEqual("sf_id", t.mapping["Insert Child__c"]["fields"]["Id"])
        self.assertEqual("Name", t.mapping["Insert Child__c"]["fields"]["Name"])
        self.assertEqual(
            "Account", t.mapping["Insert Child__c"]["lookups"]["Account__c"]["table"]
        )
        self.assertEqual(
            "Child__c", t.mapping["Insert Child__c"]["lookups"]["Self__c"]["table"]
        )

    def test_build_mapping__warns_polymorphic_lookups(self):
        t = _make_task(GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account", "Contact", "Custom__c"]
        t.schema = {
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
                "Account": set(["PolyLookup__c"]),
                "Contact": set(["PolyLookup__c"]),
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
            set(["Account", "Contact", "Opportunity", "Custom__c"]),
            {
                "Contact": {"Account": set(["AccountId"])},
                "Opportunity": {
                    "Account": set(["AccountId"]),
                    "Contact": set(["Primary_Contact__c"]),
                },
                "Custom__c": {
                    "Account": set(["Account__c"]),
                    "Contact": set(["Contact__c"]),
                    "Opportunity": set(["Opp__c"]),
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
                set(["Account", "Contact", "Opportunity", "Custom__c"]),
                {
                    "Account": {"Contact": set(["Primary_Contact__c"])},
                    "Contact": {"Account": set(["AccountId"])},
                    "Opportunity": {
                        "Account": set(["AccountId"]),
                        "Contact": set(["Primary_Contact__c"]),
                    },
                },
            ),
        )
