import pathlib
from unittest.mock import Mock, call

import pytest
import yaml

from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.tasks.salesforce.custom_settings import LoadCustomSettings
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.utils import temporary_dir


class TestLoadCustomSettings:
    def test_run_task__bad_path(self):
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})
        with pytest.raises(TaskOptionsError):
            task()

    def test_run_task__wrong_format(self):
        with temporary_dir():
            pathlib.Path("test.yml").write_text("Test__c: Test")
            task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})
            task.sf = Mock()

            with pytest.raises(
                CumulusCIException, match="must be a list or a map structure"
            ):
                task._run_task()

    def test_load_settings_list_setting(self):
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})
        task.sf = Mock()

        task.settings = {"Test__c": {"Name": {"Field__c": "Test"}}}
        task._load_settings()

        task.sf.Test__c.upsert.assert_called_once_with(
            "Name/Name", {"Field__c": "Test"}
        )

    def test_load_settings_hierarchy_setting_profile(self):
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

    def test_load_settings_hierarchy_setting_profile__error(self):
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
        with pytest.raises(CumulusCIException):
            task._load_settings()

        task.sf.Test__c.create.assert_not_called()
        task.sf.query.assert_has_calls(
            [call("SELECT Id FROM Profile WHERE Name = 'Test'")]
        )

    def test_load_settings_hierarchy_setting_user(self):
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

    def test_load_settings_hierarchy_setting_user_email(self):
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

    def test_load_settings_hierarchy_org(self):
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

    def test_load_settings_hierarchy_no_location(self):
        task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})

        task.sf = Mock()
        task.sf.query.side_effect = [
            {"totalSize": 1, "records": [{"Id": "001000000000000"}]},
            {"totalSize": 0},
        ]
        task.settings = {"Test__c": [{"data": {"Field__c": "Test"}}]}
        with pytest.raises(CumulusCIException):
            task._load_settings()

        task.sf.Test__c.create.assert_not_called()

    def test_load_settings_hierarchy_update(self):
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

    def test_run_task(self, sf):
        with temporary_dir():
            pathlib.Path("test.yml").write_text(
                yaml.dump(
                    {"Test__c": [{"location": "org", "data": {"Field__c": "Test"}}]}
                )
            )
            task = create_task(LoadCustomSettings, {"settings_path": "test.yml"})
            task.sf = Mock()
            task.sf.query.side_effect = [
                {"totalSize": 1, "records": [{"Id": "001000000000000"}]},
                {"totalSize": 1, "records": [{"Id": "001000000000001"}]},
            ]

            task._run_task()

        task.sf.Test__c.update.assert_called_once_with(
            "001000000000001", {"Field__c": "Test", "SetupOwnerId": "001000000000000"}
        )

        task.sf.query.assert_has_calls(
            [
                call("SELECT Id FROM Organization"),
                call("SELECT Id FROM Test__c WHERE SetupOwnerId = '001000000000000'"),
            ]
        )
