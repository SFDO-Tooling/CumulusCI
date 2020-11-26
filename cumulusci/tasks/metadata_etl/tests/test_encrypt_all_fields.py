from unittest import mock
from collections import defaultdict
import pytest
import responses

from cumulusci.tests.util import mock_salesforce_client, mock_describe_calls
from cumulusci.tasks.metadata_etl.encrypt_all_fields import EncryptAllFields
from cumulusci.utils.xml import metadata_tree


FAKE_OBJECT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>EncryptMe__c</fullName>
        <inlineHelpText>EncryptMe</inlineHelpText>
        <encryptionScheme>None</encryptionScheme>
        <type>Text</type>
    </fields>
    <fields>
        <fullName>NoEncryption__c</fullName>
        <inlineHelpText>NoEncryption</inlineHelpText>
        <encryptionScheme>None</encryptionScheme>
        <type>NotEncryptable</type>
    </fields>
    <fields>
        <fullName>Blocked__c</fullName>
        <inlineHelpText>Blocked</inlineHelpText>
        <encryptionScheme>None</encryptionScheme>
        <type>Text</type>
    </fields>
    <fields>
        <fullName>StandardAllowedField</fullName>
        <inlineHelpText>StandardAllowedField</inlineHelpText>
        <encryptionScheme>None</encryptionScheme>
        <type>Text</type>
    </fields>
    <fields>
        <fullName>StandardField</fullName>
        <inlineHelpText>StandardField</inlineHelpText>
        <encryptionScheme>None</encryptionScheme>
        <type>Text</type>
    </fields>
</CustomObject>
"""


class TestEncryptAllFields:
    @responses.activate
    def test_transform_entity(self, create_task_fixture):
        task = create_task_fixture(
            EncryptAllFields,
            {},
        )
        task.blocklist = {"MyObject": ["Blocked__c"]}
        task.fields_to_encrypt = defaultdict(list)
        task.standard_object_allowlist = {"MyObject": ["StandardAllowedField"]}

        sobject_xml = metadata_tree.fromstring(FAKE_OBJECT_XML)
        result = task._transform_entity(sobject_xml, "MyObject")

        custom_encrypted_field = result.find("fields", fullName="EncryptMe__c")
        custom_non_encrypted_field = result.find("fields", fullName="NoEncryption__c")
        custom_blocked_field = result.find("fields", fullName="Blocked__c")
        standard_allowed_field = result.find("fields", fullName="StandardAllowedField")
        standard_field = result.find("fields", fullName="StandardField")

        assert custom_encrypted_field is not None
        assert custom_encrypted_field.encryptionScheme.text == "ProbabilisticEncryption"
        assert custom_non_encrypted_field is not None
        assert custom_non_encrypted_field.encryptionScheme.text == "None"
        assert custom_blocked_field is not None
        assert custom_blocked_field.encryptionScheme.text == "None"
        assert standard_allowed_field is not None
        assert standard_allowed_field.encryptionScheme.text == "ProbabilisticEncryption"
        assert standard_field is not None
        assert standard_field.encryptionScheme.text == "None"
        assert task.fields_to_encrypt == {
            "MyObject": ["EncryptMe__c", "StandardAllowedField"]
        }

    @responses.activate
    def test_run_test(self, create_task_fixture):
        task = create_task_fixture(
            EncryptAllFields,
            {"blocklist_path": "unencryptable.yml", "timeout": "60"},
        )

        task.sf = mock.Mock()
        task.sf.describe.return_value = {
            "sobjects": [
                {"name": "Account", "customSetting": False},
                {"name": "MyStandardObjectWithCustomFields", "customSetting": False},
                {"name": "CustomObj__c", "customSetting": False},
                {"name": "CustomSetting__c", "customSetting": True},
            ]
        }
        task.sf.Account.describe.return_value = {
            "fields": [
                {"name": "Name"},
            ]
        }
        task.sf.MyStandardObjectWithCustomFields.describe.return_value = {
            "fields": [
                {"name": "StandardField"},
                {"name": "Custom__c"},
                {"name": "Blocked__c"},
            ]
        }
        task.sf.CustomObj__c.describe.return_value = {"fields": ["CustomCustom__c"]}
        task._retrieve = mock.Mock()
        task._deploy = mock.Mock()
        task._transform = mock.Mock()
        task._run_task()
        assert task.api_names == {
            "CustomObj__c",
            "MyStandardObjectWithCustomFields",
            "Account",
        }
        assert task.fields_to_encrypt == defaultdict(list)