import base64
import io
import unittest
import zipfile
from unittest.mock import MagicMock, Mock, call, patch

from cumulusci.salesforce_api.rest_deploy import RestDeploy
from cumulusci.tests.util import CURRENT_SF_API_VERSION


def generate_sample_zip_data(parent=""):
    # Create a sample ZIP with two files
    zip_data = io.BytesIO()
    with zipfile.ZipFile(zip_data, "w") as zip_file:
        zip_file.writestr(
            f"{parent}objects/mockfile1.obj", "Sample content for mockfile1"
        )
        zip_file.writestr(
            f"{parent}objects/mockfile2.obj", "Sample content for mockfile2"
        )
    return base64.b64encode(zip_data.getvalue()).decode("utf-8")


class TestRestDeploy(unittest.TestCase):
    # Setup method executed before each test method
    def setUp(self):
        self.mock_logger = Mock()
        self.mock_task = MagicMock()
        self.mock_task.logger = self.mock_logger
        self.mock_task.org_config.instance_url = "https://example.com"
        self.mock_task.org_config.access_token = "dummy_token"
        self.mock_task.project_config.project__package__api_version = (
            CURRENT_SF_API_VERSION
        )
        # Empty zip file for testing
        self.mock_zip = generate_sample_zip_data()

    # Test case for a successful deployment and deploy status
    @patch("requests.post")
    @patch("requests.get")
    def test_deployment_success(self, mock_get, mock_post):

        response_post = Mock(status_code=201)
        response_post.json.return_value = {"id": "dummy_id"}
        mock_post.return_value = response_post

        response_get = Mock(status_code=200)
        response_get.json.side_effect = [
            {"deployResult": {"status": "InProgress"}},
            {"deployResult": {"status": "Succeeded"}},
        ]
        mock_get.return_value = response_get

        deployer = RestDeploy(
            self.mock_task, self.mock_zip, False, False, "NoTestRun", []
        )
        deployer()

        # Assertions to verify log messages
        assert (
            call("Deployment request successful")
            in self.mock_logger.info.call_args_list
        )
        assert call("Deployment InProgress") in self.mock_logger.info.call_args_list
        assert call("Deployment Succeeded") in self.mock_logger.info.call_args_list

        # Assertions to verify API Calls
        expected_get_calls = [
            call(
                f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/metadata/deployRequest/dummy_id?includeDetails=true",
                headers={"Authorization": "Bearer dummy_token"},
            ),
            call(
                f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/metadata/deployRequest/dummy_id?includeDetails=true",
                headers={"Authorization": "Bearer dummy_token"},
            ),
        ]

        mock_post.assert_called_once()
        mock_get.assert_has_calls(expected_get_calls, any_order=True)

    # Test case for a deployment failure
    @patch("requests.post")
    def test_deployment_failure(self, mock_post):

        response_post = Mock(status_code=500)
        response_post.json.return_value = {"id": "dummy_id"}
        mock_post.return_value = response_post

        deployer = RestDeploy(
            self.mock_task, self.mock_zip, False, False, "NoTestRun", []
        )
        deployer()

        # Assertions to verify log messages
        assert (
            call("Deployment request failed with status code 500")
            in self.mock_logger.error.call_args_list
        )

        # Assertions to verify API Calls
        mock_post.assert_called_once()

    # Test for deployment success but deploy status failure
    @patch("requests.post")
    @patch("requests.get")
    def test_deployStatus_failure(self, mock_get, mock_post):

        response_post = Mock(status_code=201)
        response_post.json.return_value = {"id": "dummy_id"}
        mock_post.return_value = response_post

        response_get = Mock(status_code=200)
        response_get.json.side_effect = [
            {"deployResult": {"status": "InProgress"}},
            {
                "deployResult": {
                    "status": "Failed",
                    "details": {
                        "componentFailures": [
                            {
                                "problemType": "Error",
                                "fileName": "metadata/classes/mockfile1.cls",
                                "problem": "someproblem1",
                                "lineNumber": 1,
                                "columnNumber": 1,
                            },
                            {
                                "problemType": "Error",
                                "fileName": "metadata/objects/mockfile2.obj",
                                "problem": "someproblem2",
                                "lineNumber": 2,
                                "columnNumber": 2,
                            },
                        ]
                    },
                }
            },
        ]
        mock_get.return_value = response_get

        deployer = RestDeploy(
            self.mock_task, self.mock_zip, False, False, "NoTestRun", []
        )
        deployer()

        # Assertions to verify log messages
        assert (
            call("Deployment request successful")
            in self.mock_logger.info.call_args_list
        )
        assert call("Deployment InProgress") in self.mock_logger.info.call_args_list
        assert call("Deployment Failed") in self.mock_logger.info.call_args_list
        assert (
            call("ERROR in file classes/mockfile1.cls: someproblem1 at line 1:1")
            in self.mock_logger.error.call_args_list
        )
        assert (
            call("ERROR in file objects/mockfile2.obj: someproblem2 at line 2:2")
            in self.mock_logger.error.call_args_list
        )

        # Assertions to verify API Calls
        expected_get_calls = [
            call(
                f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/metadata/deployRequest/dummy_id?includeDetails=true",
                headers={"Authorization": "Bearer dummy_token"},
            ),
            call(
                f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/metadata/deployRequest/dummy_id?includeDetails=true",
                headers={"Authorization": "Bearer dummy_token"},
            ),
        ]

        mock_post.assert_called_once()
        mock_get.assert_has_calls(expected_get_calls, any_order=True)

    # Test case for a deployment with a pending status
    @patch("requests.post")
    @patch("requests.get")
    def test_pending_call(self, mock_get, mock_post):

        response_post = Mock(status_code=201)
        response_post.json.return_value = {"id": "dummy_id"}
        mock_post.return_value = response_post

        response_get = Mock(status_code=200)
        response_get.json.side_effect = [
            {"deployResult": {"status": "InProgress"}},
            {"deployResult": {"status": "Pending"}},
            {"deployResult": {"status": "Succeeded"}},
        ]
        mock_get.return_value = response_get

        deployer = RestDeploy(
            self.mock_task, self.mock_zip, False, False, "NoTestRun", []
        )
        deployer()

        # Assertions to verify log messages
        assert (
            call("Deployment request successful")
            in self.mock_logger.info.call_args_list
        )
        assert call("Deployment InProgress") in self.mock_logger.info.call_args_list
        assert call("Deployment Pending") in self.mock_logger.info.call_args_list
        assert call("Deployment Succeeded") in self.mock_logger.info.call_args_list

        # Assertions to verify API Calls
        expected_get_calls = [
            call(
                f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/metadata/deployRequest/dummy_id?includeDetails=true",
                headers={"Authorization": "Bearer dummy_token"},
            ),
            call(
                f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/metadata/deployRequest/dummy_id?includeDetails=true",
                headers={"Authorization": "Bearer dummy_token"},
            ),
            call(
                f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/metadata/deployRequest/dummy_id?includeDetails=true",
                headers={"Authorization": "Bearer dummy_token"},
            ),
        ]

        mock_post.assert_called_once()
        mock_get.assert_has_calls(expected_get_calls, any_order=True)

    def test_reformat_zip(self):
        input_zip = generate_sample_zip_data()
        expected_zip = generate_sample_zip_data("metadata/")

        deployer = RestDeploy(
            self.mock_task, self.mock_zip, False, False, "NoTestRun", []
        )
        actual_output_zip = deployer._reformat_zip(input_zip)

        self.assertEqual(
            base64.b64encode(actual_output_zip).decode("utf-8"), expected_zip
        )

    def test_purge_on_delete(self):
        test_data = [
            ("not_sandbox_developer", "Not Developer Edition", False, False, "false"),
            ("purgeOnDelete_true", "Developer Edition", True, True, "true"),
            ("purgeOnDelete_none", "Developer Edition", True, None, "true"),
        ]

        for name, org_type, is_sandbox, purge_on_delete, expected_result in test_data:
            with self.subTest(name=name):
                self.mock_task.org_config.org_type = org_type
                self.mock_task.org_config.is_sandbox = is_sandbox
                deployer = RestDeploy(
                    self.mock_task,
                    self.mock_zip,
                    purge_on_delete,
                    False,
                    "NoTestRun",
                    [],
                )
                self.assertEqual(deployer.purge_on_delete, expected_result)


if __name__ == "__main__":
    unittest.main()
