import unittest

from cumulusci.tasks.datadictionary import GenerateDataDictionary
from cumulusci.tasks.salesforce.util import create_task
from cumulusci.tests.util import create_project_config
from distutils.version import LooseVersion
from unittest.mock import Mock, mock_open
import xml.etree.ElementTree as ET


class test_GenerateDataDictionary(unittest.TestCase):
    def test_set_version_with_props(self):
        task = create_task(GenerateDataDictionary)

        this_dict = {"version": LooseVersion("1.1")}
        task._set_version_with_props(this_dict, {"version": None})

        assert this_dict["version"] == LooseVersion("1.1")

        this_dict = {"version": LooseVersion("1.1")}
        task._set_version_with_props(this_dict, {"version": "1.2"})

        assert this_dict["version"] == LooseVersion("1.2")

        this_dict = {"version": LooseVersion("1.3")}
        task._set_version_with_props(this_dict, {"version": "1.2"})

        assert this_dict["version"] == LooseVersion("1.3")

    def test_version_from_tag_name(self):
        task = create_task(GenerateDataDictionary)
        project_config = create_project_config("TestRepo", "TestOwner")
        project_config.project__package__git__prefix_release = "release/"

        assert task._version_from_tag_name("release/1.1") == LooseVersion("1.1")

    def test_write_results(self):
        task = create_task(
            GenerateDataDictionary,
            {"object_path": "object.csv", "field_path": "fields.csv"},
        )

        task.schema = {
            "Account": {
                "fields": {"Test__c": {"version": LooseVersion("1.1"), "label": "Test"}}
            },
            "Child__c": {
                "fields": {
                    "Parent__c": {"version": LooseVersion("1.2"), "label": "Parent"}
                },
                "version": LooseVersion("1.0"),
            },
        }
        task._write_results()
        # FIXME: mock and assert

    def test_process_field_element__new(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Account__c</fullName>
    <label>Account</label>
</CustomField>
"""
        task._process_field_element("Test__c", ET.fromstring(xml_source), "1.1")

    def test_process_field_element__updated(self):
        pass
