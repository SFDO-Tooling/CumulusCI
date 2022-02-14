import json
import re
import zipfile
from pathlib import Path
from unittest import mock

import pytest
import responses

from cumulusci.core.config import TaskConfig
from cumulusci.core.config.marketing_cloud_service_config import (
    MarketingCloudServiceConfig,
)
from cumulusci.core.exceptions import DeploymentException
from cumulusci.tasks.marketing_cloud.deploy import (
    MCPM_ENDPOINT,
    MarketingCloudDeployTask,
)
from cumulusci.tasks.marketing_cloud.mc_constants import MC_API_VERSION
from cumulusci.utils import temporary_dir

TEST_TSSD = "asdf-qwerty"
STACK_KEY = "S4"


@pytest.fixture
def task(project_config):
    test_zip_file = Path(__file__).parent.absolute() / "test-mc-pkg.zip"
    task = MarketingCloudDeployTask(
        project_config,
        TaskConfig(
            {
                "options": {
                    "package_zip_file": test_zip_file.resolve(),
                    "custom_inputs": "companyName:Acme",
                }
            }
        ),
    )
    task.mc_config = MarketingCloudServiceConfig(
        {
            "rest_instance_url": f"https://{TEST_TSSD}.rest.marketingcloudapis.com/",
            "access_token": "foo",
        },
        "mc",
        None,
    )
    return task


@pytest.fixture
def task_without_custom_inputs(project_config):
    test_zip_file = Path(__file__).parent.absolute() / "test-mc-pkg.zip"
    task = MarketingCloudDeployTask(
        project_config,
        TaskConfig(
            {
                "options": {
                    "package_zip_file": test_zip_file.resolve(),
                    "custom_inputs": None,
                }
            }
        ),
    )
    task.mc_config = MarketingCloudServiceConfig(
        {
            "rest_instance_url": f"https://{TEST_TSSD}.rest.marketingcloudapis.com/",
            "access_token": "foo",
        },
        "mc",
        None,
    )
    return task


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as rsps:
        rsps.add(
            "GET",
            f"https://{TEST_TSSD}.auth.marketingcloudapis.com/{MC_API_VERSION}/userinfo",
            json={"organization": {"stack_key": STACK_KEY}},
        )
        yield rsps


class TestMarketingCloudDeployTask:
    def test_run_task__deploy_succeeds_with_custom_inputs(self, task, mocked_responses):
        mocked_responses.add(
            "POST",
            f"{MCPM_ENDPOINT.format(STACK_KEY)}/deployments",
            json={"id": "JOBID", "status": "IN_PROGRESS"},
        )
        mocked_responses.add(
            "GET",
            f"{MCPM_ENDPOINT.format(STACK_KEY)}/deployments/JOBID",
            json={"status": "DONE", "entities": {}},
        )

        task.logger = mock.Mock()
        task._run_task()
        task.logger.info.assert_called_with("Deployment completed successfully.")
        assert task.logger.error.call_count == 0
        assert task.logger.warn.call_count == 0

    def test_run_task__deploy_succeeds_without_custom_inputs(
        self, task_without_custom_inputs, mocked_responses
    ):
        mocked_responses.add(
            "POST",
            f"{MCPM_ENDPOINT.format(STACK_KEY)}/deployments",
            json={"id": "JOBID", "status": "IN_PROGRESS"},
        )
        mocked_responses.add(
            "GET",
            f"{MCPM_ENDPOINT.format(STACK_KEY)}/deployments/JOBID",
            json={"status": "DONE", "entities": {}},
        )
        task = task_without_custom_inputs
        task.logger = mock.Mock()
        task._run_task()
        task.logger.info.assert_called_with("Deployment completed successfully.")
        assert task.logger.error.call_count == 0
        assert task.logger.warn.call_count == 0

    def test_run_task__deploy_fails(self, task, mocked_responses):
        mocked_responses.add(
            "POST",
            f"{MCPM_ENDPOINT.format(STACK_KEY)}/deployments",
            json={"id": "JOBID", "status": "IN_PROGRESS"},
        )
        mocked_responses.add(
            "GET",
            f"{MCPM_ENDPOINT.format(STACK_KEY)}/deployments/JOBID",
            json={
                "status": "DONE",
                "entities": {
                    "assets": {
                        0: {"status": "FAILED", "issues": ["A problem occurred"]},
                        1: {"status": "SKIPPED", "issues": ["A problem occurred"]},
                    },
                    "categories": {},
                },
            },
        )
        task.logger = mock.Mock()
        with pytest.raises(DeploymentException):
            task._run_task()

        assert task.logger.error.call_count == 2
        assert (
            task.logger.error.call_args_list[0][0][0]
            == "Failed to deploy assets/0. Status: FAILED. Issues: ['A problem occurred']"
        )
        assert (
            task.logger.error.call_args_list[1][0][0]
            == "Failed to deploy assets/1. Status: SKIPPED. Issues: ['A problem occurred']"
        )

    def test_run_task__FATAL_ERROR_result(self, task, mocked_responses):
        mocked_responses.add(
            "POST",
            f"{MCPM_ENDPOINT.format(STACK_KEY)}/deployments",
            json={"id": "JOBID", "status": "FATAL_ERROR"},
        )
        mocked_responses.add(
            "GET",
            f"{MCPM_ENDPOINT.format(STACK_KEY)}/deployments/JOBID",
            json={
                "status": "FATAL_ERROR",
                "entities": {},
            },
        )
        task.logger = mock.Mock()
        with pytest.raises(DeploymentException):
            task._run_task()

    def test_zipfile_not_valid(self, task):
        task.options["package_zip_file"] = "not-a-valid-file.zip"
        task.logger = mock.Mock()
        task._run_task()

        task.logger.error.assert_called_once_with(
            "Package zip file not valid: not-a-valid-file.zip"
        )

    @mock.patch("cumulusci.tasks.marketing_cloud.deploy.uuid")
    def test_construct_payload(self, uuid, task):
        uuid.uuid4.return_value = "cci-deploy"
        pkg_zip_file = Path(task.options["package_zip_file"])
        with temporary_dir() as temp_dir:
            with zipfile.ZipFile(pkg_zip_file) as zf:
                zf.extractall(temp_dir)
                actual_payload = task._construct_payload(Path(temp_dir))

        expected_payload_file = (
            Path(__file__).parent.absolute() / "expected-payload.json"
        )
        with open(expected_payload_file, "r") as f:
            expected_payload = json.load(f)

        assert expected_payload == actual_payload

    def test_add_custom_inputs_to_payload__deployment_exception(self, task):
        custom_inputs = {"foo": "bar"}
        payload = {"input": [{"key": "baz"}]}
        error_message = re.escape("Custom input of key foo not found in package.")
        with pytest.raises(DeploymentException, match=error_message):
            task._add_custom_inputs_to_payload(custom_inputs, payload)

    def test_add_custom_inputs_to_payload(self, task):
        custom_inputs = {"companyName": "Acme"}
        payload = {"input": [{"key": "companyName"}]}
        payload = task._add_custom_inputs_to_payload(custom_inputs, payload)
        assert payload == {"input": [{"key": "companyName", "value": "Acme"}]}
