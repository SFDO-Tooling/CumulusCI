import unittest
from unittest.mock import MagicMock, patch

import responses

from cumulusci.core.config import (
    BaseGlobalConfig,
    BaseProjectConfig,
    OrgConfig,
    TaskConfig,
)
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.exceptions import SalesforceException
from cumulusci.tasks.salesforce.custom_settings_wait import CustomSettingValueWait
from cumulusci.core.tests.utils import MockLoggerMixin


@patch(
    "cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials",
    MagicMock(return_value=None),
)
class TestRunCustomSettingsWait(MockLoggerMixin, unittest.TestCase):
    def setUp(self):
        self.api_version = 42.0
        self.global_config = BaseGlobalConfig(
            {"project": {"api_version": self.api_version}}
        )
        self.task_config = TaskConfig()
        self.project_config = BaseProjectConfig(
            self.global_config, config={"noyaml": True}
        )
        self.project_config.config["project"] = {
            "package": {"api_version": self.api_version}
        }
        keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(keychain)
        self.org_config = OrgConfig(
            {
                "id": "foo/1",
                "instance_url": "https://example.com",
                "access_token": "abc123",
            },
            "test",
        )
        self.base_normal_url = "{}/services/data/v{}/query/".format(
            self.org_config.instance_url, self.api_version
        )
        self.task_log = self._task_log_handler.messages

    def _get_query_resp(self):
        return {
            "size": 1,
            "totalSize": 1,
            "done": True,
            "queryLocator": None,
            "entityTypeName": "Customizable_Rollup_Setings__c",
            "records": [
                {
                    "attributes": {
                        "type": "Customizable_Rollup_Setings__c",
                        "url": "/services/data/v47.0/sobjects/Customizable_Rollup_Setings__c/707L0000014nnPHIAY",
                    },
                    "Id": "707L0000014nnPHIAY",
                    "SetupOwnerId": "00Dxxxxxxxxxxxx",
                    "Customizable_Rollups_Enabled__c": True,
                    "Rollups_Account_Batch_Size__c": 200,
                }
            ],
        }

    def _get_url_and_task(self):
        task = CustomSettingValueWait(
            self.project_config, self.task_config, self.org_config
        )
        url = self.base_normal_url
        return task, url

    @responses.activate
    def test_run_custom_settings_wait_match_bool(self):
        self.task_config.config["options"] = {
            "object": "Customizable_Rollup_Setings__c",
            "field": "Customizable_Rollups_Enabled__c",
            "value": True,
            "poll_interval": 1,
        }

        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        response["records"][0]["Customizable_Rollups_Enabled__c"] = True
        responses.add(responses.GET, url, json=response)
        task()

    @responses.activate
    def test_run_custom_settings_wait_match_int(self):
        self.task_config.config["options"] = {
            "object": "Customizable_Rollup_Setings__c",
            "field": "Rollups_Account_Batch_Size__c",
            "value": 200,
            "poll_interval": 1,
        }

        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        response["records"][0]["Rollups_Account_Batch_Size__c"] = 200
        responses.add(responses.GET, url, json=response)
        task()

    @responses.activate
    def test_run_custom_settings_wait_bad_object(self):
        self.task_config.config["options"] = {
            "object": "Customizable_Rollup_Setings__c",
            "field": "Rollups_Account_Batch_Size__c",
            "value": 200,
            "poll_interval": 1,
        }

        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        response["records"][0]["SetupOwnerId"] = "00X"
        responses.add(responses.GET, url, json=response)
        # task()

        with self.assertRaises(SalesforceException) as e:
            task()

        assert "found" in str(e.exception)
