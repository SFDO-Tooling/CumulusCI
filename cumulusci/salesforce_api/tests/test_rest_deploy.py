import unittest
from unittest.mock import MagicMock, Mock, call, patch

from cumulusci.salesforce_api.rest_deploy import RestDeploy


class TestRestDeploy(unittest.TestCase):
    # Setup method executed before each test method
    def setUp(self):
        self.mock_logger = Mock()
        self.mock_task = MagicMock()
        self.mock_task.logger = self.mock_logger
        self.mock_task.org_config.instance_url = "https://example.com"
        self.mock_task.org_config.access_token = "dummy_token"
        # Header for empty zip file
        self.mock_zip = "UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA=="

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

        # Assertions to verify log messages and method calls
        mock_post.assert_called_once()
        self.assertEqual(
            self.mock_logger.info.call_args_list[0],
            call("Deployment request successful"),
        )
        self.assertEqual(
            self.mock_logger.info.call_args_list[1],
            call("Deployment completed with status: Succeeded"),
        )
        self.assertEqual(self.mock_logger.info.call_count, 2)
        self.assertEqual(self.mock_logger.error.call_count, 0)
        self.assertEqual(self.mock_logger.debug.call_count, 0)

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

        # Assertions to verify log messages and method calls
        mock_post.assert_called_once()
        self.assertEqual(
            self.mock_logger.error.call_args_list[0],
            call("Deployment request failed with status code 500"),
        )
        self.assertEqual(self.mock_logger.info.call_count, 0)
        self.assertEqual(self.mock_logger.error.call_count, 1)
        self.assertEqual(self.mock_logger.debug.call_count, 0)

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

        # Assertions to verify log messages and method calls
        mock_post.assert_called_once()
        self.assertEqual(
            self.mock_logger.info.call_args_list[0],
            call("Deployment request successful"),
        )
        self.assertEqual(
            self.mock_logger.info.call_args_list[1],
            call("Deployment completed with status: Failed"),
        )
        self.assertEqual(self.mock_logger.info.call_count, 2)
        self.assertEqual(
            self.mock_logger.error.call_args_list[0],
            call("ERROR in file classes/mockfile1.cls: someproblem1 at line 1:1"),
        )
        self.assertEqual(
            self.mock_logger.error.call_args_list[1],
            call("ERROR in file objects/mockfile2.obj: someproblem2 at line 2:2"),
        )
        self.assertEqual(self.mock_logger.error.call_count, 2)
        self.assertEqual(self.mock_logger.debug.call_count, 0)

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

        # Assertions to verify log messages and method calls
        mock_post.assert_called_once()
        self.assertEqual(
            self.mock_logger.info.call_args_list[0],
            call("Deployment request successful"),
        )
        self.assertEqual(
            self.mock_logger.info.call_args_list[1],
            call("Deployment completed with status: Succeeded"),
        )
        self.assertEqual(self.mock_logger.info.call_count, 2)
        self.assertEqual(self.mock_logger.error.call_count, 0)
        self.assertEqual(
            self.mock_logger.debug.call_args_list[0], call("Deployment status: Pending")
        )
        self.assertEqual(self.mock_logger.debug.call_count, 1)


if __name__ == "__main__":
    unittest.main()
