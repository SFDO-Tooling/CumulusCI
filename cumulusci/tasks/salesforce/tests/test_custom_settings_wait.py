import pytest
import responses

from cumulusci.core.config import BaseProjectConfig, TaskConfig, UniversalConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.tests.utils import MockLoggerMixin
from cumulusci.tasks.salesforce.custom_settings_wait import CustomSettingValueWait
from cumulusci.tests.util import DummyOrgConfig


class TestRunCustomSettingsWait(MockLoggerMixin):
    def setup_method(self):
        self.api_version = 42.0
        self.universal_config = UniversalConfig(
            {"project": {"api_version": self.api_version}}
        )
        self.task_config = TaskConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.project_config.config["project"] = {
            "package": {"api_version": self.api_version}
        }
        keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(keychain)
        self.org_config = DummyOrgConfig(
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

        # simulate finding no settings record and then finding one with the expected value
        task, url = self._get_url_and_task()
        responses.add(
            responses.GET, url, json={"totalSize": 0, "done": True, "records": []}
        )
        response = self._get_query_resp()
        response["records"][0]["Customizable_Rollups_Enabled__c"] = True
        responses.add(responses.GET, url, json=response)
        task()

    @responses.activate
    def test_run_custom_settings_wait_match_bool_changed_case(self):
        self.task_config.config["options"] = {
            "object": "CUSTOMIZABLE_Rollup_Setings__c",
            "field": "CUSTOMIZABLE_Rollups_enabled__C",
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
    def test_run_custom_settings_wait_match_str(self):
        self.task_config.config["options"] = {
            "object": "Customizable_Rollup_Setings__c",
            "field": "Rollups_Account_Batch_Size__c",
            "value": "asdf",
            "poll_interval": 1,
        }

        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        response["records"][0]["Rollups_Account_Batch_Size__c"] = "asdf"
        responses.add(responses.GET, url, json=response)
        task()

    @responses.activate
    def test_run_custom_settings_wait_not_settings_object(self):
        self.task_config.config["options"] = {
            "object": "Customizable_Rollup_Setings__c",
            "field": "Rollups_Account_Batch_Size__c",
            "value": 200,
            "poll_interval": 1,
        }

        task, url = self._get_url_and_task()
        responses.add(
            responses.GET,
            url,
            status=400,
            json=[
                {
                    "message": "\nSELECT SetupOwnerId FROM npe5__Affiliation__c\n       ^\nERROR at Row:1:Column:8\nNo such column 'SetupOwnerId' on entity 'npe5__Affiliation__c'. If you are attempting to use a custom field, be sure to append the '__c' after the custom field name. Please reference your WSDL or the describe call for the appropriate names.",
                    "errorCode": "INVALID_FIELD",
                }
            ],
        )

        with pytest.raises(TaskOptionsError) as e:
            task()

        assert "supported" in str(e.value)

    def test_apply_namespace__managed(self):
        self.project_config.config["project"]["package"]["namespace"] = "ns"
        self.task_config.config["options"] = {
            "object": "%%%NAMESPACE%%%Test__c",
            "field": "Field__c",
            "value": "x",
            "managed": True,
            "namespaced": True,
        }
        task, url = self._get_url_and_task()
        task.object_name = "%%%NAMESPACE%%%Test__c"
        task.field_name = "%%%NAMESPACE%%%Field__c"
        task._apply_namespace()
        assert task.object_name == "ns__Test__c"
        assert task.field_name == "ns__Field__c"
