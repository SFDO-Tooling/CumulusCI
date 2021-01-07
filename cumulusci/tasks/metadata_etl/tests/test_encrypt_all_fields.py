from unittest import mock
from collections import defaultdict
from datetime import datetime, timedelta
import pytest
import responses
import logging

from cumulusci.tests.util import mock_salesforce_client, mock_describe_calls
from cumulusci.tasks.metadata_etl.encrypt_all_fields import EncryptAllFields
from cumulusci.utils.xml import metadata_tree
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError


FAKE_OBJECT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <nameField>
        <label>Name</label>
        <type>Text</type>
        <encryptionScheme>None</encryptionScheme>
    </nameField>
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

FAKE_OBJECT_XML_DETERMINISTIC_ORG = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <nameField>
        <label>Name</label>
        <type>Text</type>
        <encryptionScheme>DeterministicEncryption</encryptionScheme>
    </nameField>
    <fields>
        <fullName>EncryptMe__c</fullName>
        <inlineHelpText>EncryptMe</inlineHelpText>
        <encryptionScheme>DeterministicEncryption</encryptionScheme>
        <type>Text</type>
    </fields>
</CustomObject>
"""


class TestEncryptAllFields:
    def test_init_options(self, create_task_fixture):
        task = create_task_fixture(
            EncryptAllFields,
            {"blocklist_path": "custom.yml", "timeout": "80"},
        )
        assert task.blocklist_path == "custom.yml"
        assert task.options["timeout"] == 80

    def test_init_options_defaults(self, create_task_fixture):
        task = create_task_fixture(
            EncryptAllFields,
            {},
        )
        assert task.blocklist_path == "unencryptable.yml"
        assert task.options["timeout"] == 60

    def test_standard_allowlist(self, create_task_fixture):
        task = create_task_fixture(
            EncryptAllFields,
            {},
        )
        task.standard_object_allowlist = {"Account": ["Name"]}
        assert task._is_in_standard_object_allowlist("Account", "Name")
        assert not task._is_in_standard_object_allowlist("Account", "Id")
        assert not task._is_in_standard_object_allowlist("Contact", "Phone")

    def test_blocklist(self, create_task_fixture):
        task = create_task_fixture(
            EncryptAllFields,
            {},
        )
        task.blocklist = {"CustomObj__c": ["Blocked__c"]}
        assert task._is_in_blocklist("CustomObj__c", "Blocked__c")
        assert not task._is_in_blocklist("CustomObj__c", "EncryptMe__c")
        assert not task._is_in_blocklist("OtherCustomObj__c", "EncryptMeToo__c")

    def test_encrypt_field(self, create_task_fixture):
        task = create_task_fixture(
            EncryptAllFields,
            {},
        )

        sobject_xml = metadata_tree.fromstring(FAKE_OBJECT_XML)
        for field in sobject_xml.findall("fields"):
            task.encrypt_field(field)
            assert field.encryptionScheme.text == "ProbabilisticEncryption"

    def test_encrypt_field_deterministic(self, create_task_fixture):
        task = create_task_fixture(
            EncryptAllFields,
            {},
        )

        sobject_xml = metadata_tree.fromstring(FAKE_OBJECT_XML_DETERMINISTIC_ORG)
        with pytest.raises(CumulusCIException) as err:
            for field in sobject_xml.findall("fields"):
                task.encrypt_field(field)
        assert "This org is already using DeterministicEncryption." in str(err.value)

    @responses.activate
    @mock.patch("os.path.isfile")
    def test_bad_blocklist_path(self, isfile, create_task_fixture):
        isfile.return_value = False
        with pytest.raises(TaskOptionsError) as err:
            task = create_task_fixture(EncryptAllFields, {"blocklist_path": "garbage"})
            task._set_api_names = mock.Mock()
            task.api_names = {"Account", "Contact"}
            task._retrieve = mock.Mock()
            task._deploy = mock.Mock()
            task._transform = mock.Mock()
            task._set_blocklist()
        assert "No blocklist found at garbage" in str(err.value)

    @mock.patch("os.path.isfile")
    def test_no_blocklist_file(self, isfile, create_task_fixture, caplog):
        caplog.set_level(logging.INFO)
        isfile.return_value = False
        task = create_task_fixture(EncryptAllFields, {})
        task._set_blocklist()
        assert (
            "No blocklist found at unencryptable.yml. Attempting to encrypt all fields."
            in caplog.text
        )

    @mock.patch("os.path.isfile")
    def test_good_blocklist_path(self, isfile, create_task_fixture, caplog):
        caplog.set_level(logging.INFO)
        isfile.return_value = True
        read_data = "test:"
        mock_open = mock.mock_open(read_data=read_data)
        with mock.patch("builtins.open", mock_open):
            task = create_task_fixture(EncryptAllFields, {"blocklist_path": "goodpath"})
            task._set_blocklist()
        assert task.blocklist == {"test": None}
        assert "Using blocklist provided at goodpath" in caplog.text

    @responses.activate
    def test_run_task(self, create_task_fixture):
        task = create_task_fixture(
            EncryptAllFields,
            {"blocklist_path": "unencryptable.yml", "timeout": "60"},
        )

        task.sf = mock.Mock()
        task.sf.describe.return_value = {
            "sobjects": [
                {"name": "Account", "customSetting": False, "queryable":True, "deprecatedAndHidden":False},
                {"name": "MyStandardObjectWithCustomFields", "customSetting": False, "queryable":True, "deprecatedAndHidden":False},
                {"name": "CustomObj__c", "customSetting": False, "queryable":True, "deprecatedAndHidden":False},
                {"name": "CustomSetting__c", "customSetting": True, "queryable":True, "deprecatedAndHidden":False},
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
        task.sf.CustomObj__c.describe.return_value = {
            "fields": [{"name": "CustomCustom__c"}]
        }
        task._retrieve = mock.Mock()
        task._deploy = mock.Mock()
        task._transform = mock.Mock()
        task._set_blocklist = mock.Mock()
        task.blocklist = {}
        task._run_task()
        assert task.api_names == {
            "CustomObj__c",
            "MyStandardObjectWithCustomFields",
            "Account",
        }
        assert task.fields_to_encrypt == defaultdict(list)

    @responses.activate
    def test_transform_entity(self, create_task_fixture):
        task = create_task_fixture(
            EncryptAllFields,
            {},
        )
        task.blocklist = {"MyObject__c": ["Blocked__c"]}
        task.fields_to_encrypt = defaultdict(list)
        task.standard_object_allowlist = {"MyObject__c": ["StandardAllowedField"]}

        sobject_xml = metadata_tree.fromstring(FAKE_OBJECT_XML)
        result = task._transform_entity(sobject_xml, "MyObject__c")

        custom_encrypted_field = result.find("fields", fullName="EncryptMe__c")
        custom_non_encrypted_field = result.find("fields", fullName="NoEncryption__c")
        custom_blocked_field = result.find("fields", fullName="Blocked__c")
        standard_allowed_field = result.find("fields", fullName="StandardAllowedField")
        standard_field = result.find("fields", fullName="StandardField")
        name_field = result.find("nameField", label="Name")

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
        assert name_field is not None
        assert name_field.encryptionScheme.text == "ProbabilisticEncryption"
        assert task.fields_to_encrypt == {
            "MyObject__c": ["Name", "EncryptMe__c", "StandardAllowedField"]
        }

    @responses.activate
    def test_poll_success(self, create_task_fixture, caplog):
        caplog.set_level(logging.INFO)
        task = create_task_fixture(
            EncryptAllFields,
            {"blocklist_path": "unencryptable.yml", "timeout": "60"},
        )

        task.sf = mock.Mock()
        task.sf.describe.return_value = {
            "sobjects": [
                {"name": "Account"},
                {"name": "MyStandardObjectWithCustomFields"},
                {"name": "CustomObj__c"},
            ]
        }
        task.sf.Account.describe.return_value = {
            "fields": [
                {"name": "Name", "filterable": False},
            ]
        }
        task.sf.MyStandardObjectWithCustomFields.describe.return_value = {
            "fields": [
                {"name": "StandardField", "filterable": True},
                {"name": "Custom__c", "filterable": False},
            ]
        }
        task.sf.CustomObj__c.describe.return_value = {
            "fields": [{"name": "CustomCustom__c", "filterable": False}]
        }

        task.fields_to_encrypt = {
            "CustomObj__c": ["CustomCustom__c"],
            "MyStandardObjectWithCustomFields": ["Custom__c"],
            "Account": ["Name"],
        }

        task.time_start = datetime.now()

        task._poll_action()
        assert task.poll_complete
        assert "Platform Encryption enablement successfully completed" in caplog.text

    @responses.activate
    def test_repoll(self, create_task_fixture):
        task = create_task_fixture(
            EncryptAllFields,
            {"blocklist_path": "unencryptable.yml", "timeout": "60"},
        )

        task.sf = mock.Mock()
        task.sf.describe.return_value = {
            "sobjects": [
                {"name": "Account"},
                {"name": "MyStandardObjectWithCustomFields"},
                {"name": "CustomObj__c"},
            ]
        }
        task.sf.Account.describe.return_value = {
            "fields": [
                {"name": "Name", "filterable": True},
            ]
        }
        task.sf.MyStandardObjectWithCustomFields.describe.return_value = {
            "fields": [
                {"name": "StandardField", "filterable": True},
                {"name": "Custom__c", "filterable": False},
            ]
        }
        task.sf.CustomObj__c.describe.return_value = {
            "fields": [{"name": "CustomCustom__c", "filterable": False}]
        }

        task.fields_to_encrypt = {
            "CustomObj__c": ["CustomCustom__c"],
            "MyStandardObjectWithCustomFields": ["Custom__c"],
            "Account": ["Name"],
        }

        task.time_start = datetime.now()

        task._poll_action()
        assert not task.poll_complete

    @responses.activate
    def test_poll_timeout(self, create_task_fixture, caplog):
        caplog.set_level(logging.INFO)
        task = create_task_fixture(
            EncryptAllFields,
            {},
        )

        task.fields_to_encrypt = {
            "MyStandardObjectWithCustomFields": ["Custom__c"],
        }

        task.time_start = datetime.now() - timedelta(minutes=2)

        with pytest.raises(CumulusCIException) as err:
            task._poll_action()

        assert "Encryption enablement not successfully completed after" in str(
            err.value
        )
        assert not task.poll_complete
        assert (
            "Couldn't encrypt: MyStandardObjectWithCustomFields fields ['Custom__c'"
            in caplog.text
        )
