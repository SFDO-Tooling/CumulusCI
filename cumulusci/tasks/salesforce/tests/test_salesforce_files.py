import json
import os
import unittest
from unittest.mock import Mock, call, mock_open, patch

from cumulusci.tasks.salesforce.salesforce_files import (
    ListFiles,
    RetrieveFiles,
    UploadFiles,
)
from cumulusci.tasks.salesforce.tests.util import create_task


class TestDisplayFiles:
    def test_display_files(self):
        task = create_task(ListFiles, {})
        task._init_api = Mock()
        task._init_api.return_value.query.return_value = {
            "totalSize": 2,
            "records": [
                {"Title": "TEST1", "Id": "0PS000000000000", "FileType": "TXT"},
                {"Title": "TEST2", "Id": "0PS000000000001", "FileType": "TXT"},
            ],
        }
        task()

        task._init_api.return_value.query.assert_called_once_with(
            "SELECT Title, Id, FileType FROM ContentDocument"
        )
        assert task.return_values == [
            {"Id": "0PS000000000000", "FileName": "TEST1", "FileType": "TXT"},
            {"Id": "0PS000000000001", "FileName": "TEST2", "FileType": "TXT"},
        ]


class TestRetrieveFiles(unittest.TestCase):
    @patch("requests.get")
    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("builtins.open")
    def test_run_task(self, mock_open, mock_makedirs, mock_exists, mock_get):
        # Mock Salesforce query response
        mock_sf = Mock()
        mock_sf.query.return_value = {
            "totalSize": 2,
            "records": [
                {
                    "Title": "TEST1",
                    "Id": "0PS000000000000",
                    "FileType": "TXT",
                    "VersionData": "version1",
                    "ContentDocumentId": "doc1",
                },
                {
                    "Title": "TEST2",
                    "Id": "0PS000000000001",
                    "FileType": "TXT",
                    "VersionData": "version2",
                    "ContentDocumentId": "doc2",
                },
            ],
        }

        # Mock org config
        mock_org_config = Mock()
        mock_org_config.instance_url = "https://test.salesforce.com"
        mock_org_config.access_token = "test token"

        # Create task with mocked Salesforce and org config
        task = create_task(RetrieveFiles, {"path": "test_dir", "file_list": ""})
        task.sf = mock_sf
        task.org_config = mock_org_config

        # Mock file existence and request response
        mock_exists.return_value = False
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Run the task
        task._run_task()

        # Check if query was called with correct SOQL
        mock_sf.query.assert_called_once_with(
            "SELECT Title, Id, FileType, VersionData, ContentDocumentId FROM ContentVersion WHERE isLatest=true "
        )

        # Check if files are downloaded
        expected_calls = [
            call(
                "https://test.salesforce.com/version1",
                headers={"Authorization": "Bearer test token"},
                stream=True,
            ),
            call(
                "https://test.salesforce.com/version2",
                headers={"Authorization": "Bearer test token"},
                stream=True,
            ),
        ]
        mock_get.assert_has_calls(expected_calls, any_order=True)

        # Check if files are written correctly
        mock_open.assert_any_call(os.path.join("test_dir", "TEST1.txt"), "wb")
        mock_open.assert_any_call(os.path.join("test_dir", "TEST2.txt"), "wb")

        # Check if return values are set correctly
        self.assertEqual(
            task.return_values,
            [
                {
                    "Id": "0PS000000000000",
                    "FileName": "TEST1",
                    "FileType": "TXT",
                    "VersionData": "version1",
                    "ContentDocumentId": "doc1",
                },
                {
                    "Id": "0PS000000000001",
                    "FileName": "TEST2",
                    "FileType": "TXT",
                    "VersionData": "version2",
                    "ContentDocumentId": "doc2",
                },
            ],
        )


class TestUploadFiles(unittest.TestCase):
    @patch("requests.post")
    @patch("os.listdir")
    @patch("os.path.isfile")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test data")
    def test_run_task(self, mock_open, mock_isfile, mock_listdir, mock_post):
        # Mock org config and project config
        mock_org_config = Mock()
        mock_org_config.instance_url = "https://test.salesforce.com"
        mock_org_config.access_token = "test token"

        mock_project_config = Mock()
        mock_project_config.project__package__api_version = "50.0"

        # Create task with mocked configs
        task = create_task(UploadFiles, {"path": "test_dir", "file_list": ""})
        task.org_config = mock_org_config
        task.project_config = mock_project_config

        # Mock file discovery
        mock_listdir.return_value = ["file1.txt", "file2.txt"]
        mock_isfile.side_effect = lambda filepath: filepath in [
            os.path.join("test_dir", "file1.txt"),
            os.path.join("test_dir", "file2.txt"),
        ]

        # Mock requests response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "contentversionid"}
        mock_post.return_value = mock_response

        # Run the task
        task._run_task()

        mock_open.assert_any_call(os.path.join("test_dir", "file1.txt"), "rb")
        mock_open.assert_any_call(os.path.join("test_dir", "file2.txt"), "rb")

        # Check if requests.post was called correctly
        expected_calls = [
            call(
                "https://test.salesforce.com/services/data/v50.0/sobjects/ContentVersion/",
                headers={"Authorization": "Bearer test token"},
                files={
                    "entity_content": (
                        "",
                        json.dumps(
                            {
                                "Title": "file1",
                                "PathOnClient": os.path.join("test_dir", "file1.txt"),
                            }
                        ),
                        "application/json",
                    ),
                    "VersionData": (
                        "file1.txt",
                        mock_open(),
                        "application/octet-stream",
                    ),
                },
            ),
            call(
                "https://test.salesforce.com/services/data/v50.0/sobjects/ContentVersion/",
                headers={"Authorization": "Bearer test token"},
                files={
                    "entity_content": (
                        "",
                        json.dumps(
                            {
                                "Title": "file2",
                                "PathOnClient": os.path.join("test_dir", "file2.txt"),
                            }
                        ),
                        "application/json",
                    ),
                    "VersionData": (
                        "file2.txt",
                        mock_open(),
                        "application/octet-stream",
                    ),
                },
            ),
        ]

        self.assertEqual(
            task.return_values,
            [
                {
                    "Title": "file1",
                    "PathOnClient": os.path.join("test_dir", "file1.txt"),
                },
                {
                    "Title": "file2",
                    "PathOnClient": os.path.join("test_dir", "file2.txt"),
                },
            ],
        )

        mock_post.assert_has_calls(expected_calls, any_order=True)
