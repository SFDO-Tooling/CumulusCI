import unittest
import yaml
from unittest.mock import Mock, patch, call, mock_open

from cumulusci.tasks.salesforce import LoadCustomSettings
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.core.exceptions import TaskOptionsError, CumulusCIException


class TestLoadCustomSettings(unittest.TestCase):
    @patch("os.path.isfile")
    def test_init_options__exception(self, isfile):
        isfile.return_value = False
        with self.assertRaises(TaskOptionsError):
            create_task(LoadCustomSettings, {"settings_path": "test.yml"})

    @patch("os.path.isfile")
    def test_load_settings_bad_yaml(self, isfile):
        isfile.return_value = True
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})

        task.sf = Mock()

        task.settings = {"Test__c": "Test"}
        with self.assertRaises(CumulusCIException):
            task._load_settings()

    @patch("os.path.isfile")
    def test_load_settings_list_setting(self, isfile):
        isfile.return_value = True
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})

        task.sf = Mock()

        task.settings = {"Test__c": {"Name": {"Field__c": "Test"}}}
        task._load_settings()

        task.sf.Test__c.upsert.assert_called_once_with(
            "Name/Name", {"Field__c": "Test"}
        )

    @patch("os.path.isfile")
    def test_load_settings_hierarchy_setting_profile(self, isfile):
        isfile.return_value = True
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})

        task.sf = Mock()
        task.sf.query.side_effect = [
            {"totalSize": 1, "records": [{"Id": "001000000000000"}]},
            {"totalSize": 0},
        ]
        task.settings = {
            "Test__c": [{"location": {"profile": "Test"}, "data": {"Field__c": "Test"}}]
        }
        task._load_settings()

        task.sf.Test__c.create.assert_called_once_with(
            {"Field__c": "Test", "SetupOwnerId": "001000000000000"}
        )
        task.sf.query.assert_has_calls(
            [
                call("SELECT Id FROM Profile WHERE Name = 'Test'"),
                call("SELECT Id FROM Test__c WHERE SetupOwnerId = '001000000000000'"),
            ]
        )

    @patch("os.path.isfile")
    def test_load_settings_hierarchy_setting_profile__error(self, isfile):
        isfile.return_value = True
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})

        task.sf = Mock()
        task.sf.query.side_effect = [
            {
                "totalSize": 2,
                "records": [{"Id": "001000000000000"}, {"Id": "001000000000001"}],
            },
            {"totalSize": 0},
        ]
        task.settings = {
            "Test__c": [{"location": {"profile": "Test"}, "data": {"Field__c": "Test"}}]
        }
        with self.assertRaises(CumulusCIException):
            task._load_settings()

        task.sf.Test__c.create.assert_not_called()
        task.sf.query.assert_has_calls(
            [call("SELECT Id FROM Profile WHERE Name = 'Test'")]
        )

    @patch("os.path.isfile")
    def test_load_settings_hierarchy_setting_user(self, isfile):
        isfile.return_value = True
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})

        task.sf = Mock()
        task.sf.query.side_effect = [
            {"totalSize": 1, "records": [{"Id": "001000000000000"}]},
            {"totalSize": 0},
        ]
        task.settings = {
            "Test__c": [
                {
                    "location": {"user": {"name": "test@example.com"}},
                    "data": {"Field__c": "Test"},
                }
            ]
        }
        task._load_settings()

        task.sf.Test__c.create.assert_called_once_with(
            {"Field__c": "Test", "SetupOwnerId": "001000000000000"}
        )

        task.sf.query.assert_has_calls(
            [
                call("SELECT Id FROM User WHERE Username = 'test@example.com'"),
                call("SELECT Id FROM Test__c WHERE SetupOwnerId = '001000000000000'"),
            ]
        )

    @patch("os.path.isfile")
    def test_load_settings_hierarchy_setting_user_email(self, isfile):
        isfile.return_value = True
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})

        task.sf = Mock()
        task.sf.query.side_effect = [
            {"totalSize": 1, "records": [{"Id": "001000000000000"}]},
            {"totalSize": 0},
        ]
        task.settings = {
            "Test__c": [
                {
                    "location": {"user": {"email": "test-user@example.com"}},
                    "data": {"Field__c": "Test"},
                }
            ]
        }
        task._load_settings()

        task.sf.Test__c.create.assert_called_once_with(
            {"Field__c": "Test", "SetupOwnerId": "001000000000000"}
        )

        task.sf.query.assert_has_calls(
            [
                call("SELECT Id FROM User WHERE Email = 'test-user@example.com'"),
                call("SELECT Id FROM Test__c WHERE SetupOwnerId = '001000000000000'"),
            ]
        )

    @patch("os.path.isfile")
    def test_load_settings_hierarchy_org(self, isfile):
        isfile.return_value = True
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})

        task.sf = Mock()
        task.sf.query.side_effect = [
            {"totalSize": 1, "records": [{"Id": "001000000000000"}]},
            {"totalSize": 0},
        ]
        task.settings = {"Test__c": [{"location": "org", "data": {"Field__c": "Test"}}]}
        task._load_settings()

        task.sf.Test__c.create.assert_called_once_with(
            {"Field__c": "Test", "SetupOwnerId": "001000000000000"}
        )

        task.sf.query.assert_has_calls(
            [
                call("SELECT Id FROM Organization"),
                call("SELECT Id FROM Test__c WHERE SetupOwnerId = '001000000000000'"),
            ]
        )

    @patch("os.path.isfile")
    def test_load_settings_hierarchy_no_location(self, isfile):
        isfile.return_value = True
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})

        task.sf = Mock()
        task.sf.query.side_effect = [
            {"totalSize": 1, "records": [{"Id": "001000000000000"}]},
            {"totalSize": 0},
        ]
        task.settings = {"Test__c": [{"data": {"Field__c": "Test"}}]}
        with self.assertRaises(CumulusCIException):
            task._load_settings()

        task.sf.Test__c.create.assert_not_called()

    @patch("os.path.isfile")
    def test_load_settings_hierarchy_update(self, isfile):
        isfile.return_value = True
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})

        task.sf = Mock()
        task.sf.query.side_effect = [
            {"totalSize": 1, "records": [{"Id": "001000000000000"}]},
            {"totalSize": 1, "records": [{"Id": "001000000000001"}]},
        ]
        task.settings = {"Test__c": [{"location": "org", "data": {"Field__c": "Test"}}]}
        task._load_settings()

        task.sf.Test__c.update.assert_called_once_with(
            "001000000000001", {"Field__c": "Test", "SetupOwnerId": "001000000000000"}
        )

        task.sf.query.assert_has_calls(
            [
                call("SELECT Id FROM Organization"),
                call("SELECT Id FROM Test__c WHERE SetupOwnerId = '001000000000000'"),
            ]
        )

    @patch("os.path.isfile")
    @patch("simple_salesforce.Salesforce")
    def test_run_task(self, sf, isfile):
        isfile.return_value = True
        m = mock_open(
            read_data=yaml.dump(
                {"Test__c": [{"location": "org", "data": {"Field__c": "Test"}}]}
            )
        )
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})

        sf.return_value.query.side_effect = [
            {"totalSize": 1, "records": [{"Id": "001000000000000"}]},
            {"totalSize": 1, "records": [{"Id": "001000000000001"}]},
        ]
        with patch("builtins.open", m):
            task()

        task.sf.Test__c.update.assert_called_once_with(
            "001000000000001", {"Field__c": "Test", "SetupOwnerId": "001000000000000"}
        )

        task.sf.query.assert_has_calls(
            [
                call("SELECT Id FROM Organization"),
                call("SELECT Id FROM Test__c WHERE SetupOwnerId = '001000000000000'"),
            ]
        )
