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
    MCPM_BASE_ENDPOINT,
    MCPM_JOB_ID_HEADER,
    UNKNOWN_STATUS_MESSAGE,
    MarketingCloudDeployTask,
)
from cumulusci.tasks.marketing_cloud.mc_constants import MC_API_VERSION
from cumulusci.utils import temporary_dir

TEST_TSSD = "asdf-qwerty"
STACK_KEY = "S4"
TEST_ZIPFILE = "test-mc-pkg.zip"
PAYLOAD_FILE = "expected-payload.json"
JOB_NAME = "foo_job"

# This JSON does not necessarily include the complete data provided by Marketing Cloud
# It is intended to exercise functionality in the class under test.
# The response is designed to go with the content of `expected-payload.json`
VALIDATION_RESPONSE_FILE = "validation-response.json"


@pytest.fixture
def task(project_config):
    test_zip_file = Path(__file__).parent.absolute() / TEST_ZIPFILE
    task = MarketingCloudDeployTask(
        project_config,
        TaskConfig(
            {
                "options": {
                    "package_zip_file": test_zip_file.resolve(),
                    "custom_inputs": "companyName:Acme",
                    "name": JOB_NAME,
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
    task.poll_interval_s = 0  # Do not poll during testing
    return task


@pytest.fixture
def validation_response():
    with open(Path(__file__).parent.absolute() / VALIDATION_RESPONSE_FILE) as f:
        return json.load(f)


@pytest.fixture
def expected_payload():
    expected_payload_file = Path(__file__).parent.absolute() / PAYLOAD_FILE
    with open(expected_payload_file, "r") as f:
        return json.load(f)


@pytest.fixture
def task_without_custom_inputs(project_config):
    test_zip_file = Path(__file__).parent.absolute() / TEST_ZIPFILE
    task = MarketingCloudDeployTask(
        project_config,
        TaskConfig(
            {
                "options": {
                    "package_zip_file": test_zip_file.resolve(),
                    "custom_inputs": None,
                    "name": JOB_NAME,
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


@pytest.fixture
def mocked_validation_responses(mocked_responses):
    mocked_responses.add(
        "POST",
        f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/validate",
        json={"id": "0be865fe-efb2-479d-99c2-c1b608155369"},
        match=[responses.matchers.header_matcher({MCPM_JOB_ID_HEADER: JOB_NAME})],
    )
    mocked_responses.add(
        "GET",
        f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/validate/0be865fe-efb2-479d-99c2-c1b608155369",
        match=[responses.matchers.header_matcher({MCPM_JOB_ID_HEADER: JOB_NAME})],
        json={"status": "DONE"},
    )

    yield mocked_responses


@pytest.fixture
def mocked_polling_validation_responses(mocked_responses, validation_response):
    mocked_responses.add(
        "POST",
        f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/validate",
        match=[responses.matchers.header_matcher({MCPM_JOB_ID_HEADER: JOB_NAME})],
        json={"id": "0be865fe-efb2-479d-99c2-c1b608155369"},
    )
    mocked_responses.add(
        "GET",
        f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/validate/0be865fe-efb2-479d-99c2-c1b608155369",
        match=[responses.matchers.header_matcher({MCPM_JOB_ID_HEADER: JOB_NAME})],
        json={"status": "NOT_FOUND"},
    )
    mocked_responses.add(
        "GET",
        f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/validate/0be865fe-efb2-479d-99c2-c1b608155369",
        match=[responses.matchers.header_matcher({MCPM_JOB_ID_HEADER: JOB_NAME})],
        json={"status": "IN_PROGRESS"},
    )
    mocked_responses.add(
        "GET",
        f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/validate/0be865fe-efb2-479d-99c2-c1b608155369",
        match=[responses.matchers.header_matcher({MCPM_JOB_ID_HEADER: JOB_NAME})],
        json={"status": "NOT_FOUND"},
    )
    mocked_responses.add(
        "GET",
        f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/validate/0be865fe-efb2-479d-99c2-c1b608155369",
        match=[responses.matchers.header_matcher({MCPM_JOB_ID_HEADER: JOB_NAME})],
        json=validation_response,
    )

    yield mocked_responses


@pytest.fixture
def mocked_polling_validation_responses_all_not_found(mocked_responses):
    mocked_responses.add(
        "POST",
        f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/validate",
        match=[responses.matchers.header_matcher({MCPM_JOB_ID_HEADER: JOB_NAME})],
        json={"id": "0be865fe-efb2-479d-99c2-c1b608155369"},
    )
    for _ in range(10):
        mocked_responses.add(
            "GET",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/validate/0be865fe-efb2-479d-99c2-c1b608155369",
            match=[responses.matchers.header_matcher({MCPM_JOB_ID_HEADER: JOB_NAME})],
            json={"status": "NOT_FOUND"},
        )

    yield mocked_responses


class TestMarketingCloudDeployTask:
    def test_run_task__deploy_succeeds_with_custom_inputs(
        self, task, mocked_validation_responses
    ):
        mocked_validation_responses.add(
            "POST",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments",
            json={"id": "JOBID", "status": "IN_PROGRESS"},
        )
        mocked_validation_responses.add(
            "GET",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments/JOBID",
            json={"status": "DONE", "entities": {}},
        )

        task.logger = mock.Mock()
        task._run_task()
        task.logger.info.assert_called_with(
            "Deployment (JOBID) completed successfully."
        )
        assert task.logger.error.call_count == 0
        assert task.logger.warn.call_count == 0

    def test_run_task__deploy_succeeds_without_custom_inputs(
        self, task_without_custom_inputs, mocked_validation_responses
    ):
        mocked_validation_responses.add(
            "POST",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments",
            json={"id": "JOBID", "status": "IN_PROGRESS"},
        )
        mocked_validation_responses.add(
            "GET",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments/JOBID",
            json={"status": "DONE", "entities": {}},
        )
        task = task_without_custom_inputs
        task.logger = mock.Mock()
        task._run_task()
        task.logger.info.assert_called_with(
            "Deployment (JOBID) completed successfully."
        )
        assert task.logger.error.call_count == 0
        assert task.logger.warn.call_count == 0

    def test_run_task__deploy_fails(self, task, mocked_validation_responses):
        mocked_validation_responses.add(
            "POST",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments",
            json={"id": "JOBID", "status": "IN_PROGRESS"},
        )
        mocked_validation_responses.add(
            "GET",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments/JOBID",
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

    def test_run_task__FATAL_ERROR_result(self, task, mocked_validation_responses):
        mocked_validation_responses.add(
            "POST",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments",
            json={"id": "JOBID", "status": "FATAL_ERROR"},
        )
        mocked_validation_responses.add(
            "GET",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments/JOBID",
            json={
                "status": "FATAL_ERROR",
                "entities": {},
            },
        )
        task.logger = mock.Mock()
        with pytest.raises(DeploymentException):
            task._run_task()

    def test_run_task__unknown_deploy_status(
        self, task, mocked_validation_responses, caplog
    ):
        unknown_status = "FOOBAR"
        mocked_validation_responses.add(
            "POST",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments",
            json={"id": "JOBID"},
        )
        mocked_validation_responses.add(
            "GET",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments/JOBID",
            json={
                "status": unknown_status,
                "entities": {},
            },
        )
        caplog.clear()
        with pytest.raises(DeploymentException):
            task._run_task()

        logged_messages = [log.message for log in caplog.records]
        assert UNKNOWN_STATUS_MESSAGE.format(unknown_status) in logged_messages

    # NOTE: the x-mcpm-job-id header is validated implicitly by all use
    # of Responses mocks.

    def test_validate_package__validation_accepts_intermittent_not_found(
        self, task, mocked_polling_validation_responses
    ):
        mocked_polling_validation_responses.add(
            "POST",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments",
            json={"id": "JOBID", "status": "IN_PROGRESS"},
        )
        mocked_polling_validation_responses.add(
            "GET",
            f"{MCPM_BASE_ENDPOINT.format(STACK_KEY)}/deployments/JOBID",
            json={"status": "DONE", "entities": {}},
        )
        task._run_task()
        assert task.validation_response["status"] == "DONE"

    def test_validate_package__validation_fails_consistent_not_found(
        self, task, mocked_polling_validation_responses_all_not_found
    ):
        with pytest.raises(DeploymentException):
            task._run_task()

    def test_update_payload_entities_with_actions(
        self, task, expected_payload, validation_response
    ):
        task.validation_response = validation_response
        validated_payload = task._update_payload_entities_with_actions(expected_payload)

        assert validated_payload["entities"]["assets"]["0"]["action"] == {
            "type": "create",
            "available": True,
            "issues": [],
        }

    def test_action_for_entity(self, task, validation_response):
        task.validation_response = validation_response

        # We should expect to get back the first action with available == True
        assert task.action_for_entity("assets", "0") == {
            "type": "create",
            "available": True,
            "issues": [],
        }
        assert task.action_for_entity("foo", "0") is None

    def test_zipfile_not_valid(self, task):
        task.options["package_zip_file"] = "not-a-valid-file.zip"
        task.logger = mock.Mock()
        task._run_task()

        task.logger.error.assert_called_once_with(
            "Package zip file not valid: not-a-valid-file.zip"
        )

    def test_construct_payload(self, task, expected_payload):
        task.options["name"] = "cci-deploy"
        pkg_zip_file = Path(task.options["package_zip_file"])
        with temporary_dir() as temp_dir:
            with zipfile.ZipFile(pkg_zip_file) as zf:
                zf.extractall(temp_dir)
                actual_payload = task._construct_payload(Path(temp_dir))

        assert expected_payload == actual_payload

    def test_construct_payload__file_not_found(self, task):
        """Ensure we state clearly state where expect files to be"""
        task.options["name"] = "cci-deploy"
        pkg_zip_file = Path(task.options["package_zip_file"])
        with temporary_dir() as temp_dir:
            with zipfile.ZipFile(pkg_zip_file) as zf:
                zf.extractall(temp_dir)

                expected_payload_file = Path(temp_dir + "/info.json")
                assert expected_payload_file.is_file()
                Path.unlink(expected_payload_file)

                with pytest.raises(DeploymentException):
                    task._construct_payload(Path(temp_dir))

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
