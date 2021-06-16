import json
import pytest
import responses
import zipfile

from pathlib import Path
from unittest import mock

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import DeploymentException
from cumulusci.tasks.marketing_cloud.deploy import MarketingCloudDeployTask
from cumulusci.tasks.marketing_cloud.deploy import MCPM_ENDPOINT
from cumulusci.utils import temporary_dir


@pytest.fixture
def task(project_config):
    test_zip_file = Path(__file__).parent.absolute() / "test-mc-pkg.zip"
    task = MarketingCloudDeployTask(
        project_config,
        TaskConfig({"options": {"package_zip_file": test_zip_file.resolve()}}),
    )
    task.mc_config = mock.Mock()
    task.mc_config.access_token = "foo"
    task.mc_config.tssd = "bar"
    return task


class TestMarketingCloudDeployTask:
    @responses.activate
    def test_run_task__deploy_succeeds(self, task):
        responses.add(
            "POST",
            f"{MCPM_ENDPOINT}/deployments",
            json={"info": {"id": "JOBID", "status": "IN_PROGRESS"}},
        )
        responses.add(
            "GET",
            f"{MCPM_ENDPOINT}/deployments/JOBID",
            json={"status": "DONE", "entities": {}},
        )

        task.logger = mock.Mock()
        task._run_task()
        task.logger.info.assert_called_with("Deployment completed successfully.")
        assert task.logger.error.call_count == 0
        assert task.logger.warn.call_count == 0

    @responses.activate
    def test_run_task__deploy_fails(self, task):
        responses.add(
            "POST",
            f"{MCPM_ENDPOINT}/deployments",
            json={"info": {"id": "JOBID", "status": "IN_PROGRESS"}},
        )
        responses.add(
            "GET",
            f"{MCPM_ENDPOINT}/deployments/JOBID",
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

    def test_zipfile_not_valid(self, task):
        task.options["package_zip_file"] = "not-a-valid-file.zip"
        task.logger = mock.Mock()
        task._run_task()

        task.logger.error.assert_called_once_with(
            "Package zip file not valid: not-a-valid-file.zip"
        )

    def test_construct_payload(self, task):
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
