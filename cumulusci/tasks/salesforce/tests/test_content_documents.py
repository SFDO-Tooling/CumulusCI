import pytest  # noqa: F401
from unittest import mock
import responses
from cumulusci.tasks.salesforce.tests.util import create_task

from pathlib import Path
import os
from cumulusci.tasks.salesforce.content_documents import (
    InsertContentDocument,
    to_cumulusci_exception,
)
from cumulusci.core.exceptions import CumulusCIException  # noqa: F401
from simple_salesforce.exceptions import SalesforceMalformedRequest


def get_rest_api_base_url(task):
    return f"{task.org_config.instance_url}/services/data/{task.project_config.project__package__api_version}"


def test_to_cumulusci_exception():
    e = to_cumulusci_exception(
        SalesforceMalformedRequest(
            "url",
            "status",
            "resource_name",
            [
                {"message": "Error message 1.", "errorCode": "ERROR_1"},
                {"errorCode": "ERROR_2"},
                {"message": "Error message 3.", "errorCode": "ERROR_3"},
            ],
        )
    )

    assert type(e) is CumulusCIException
    assert "Error message 1.; Unknown.; Error message 3." == e.args[0]


class TestInsertContentDocument:
    def setup_method(self):
        self.base_path = os.path.dirname(__file__)

        # Path to an existing directory (that is not a file).
        self.directory_path = Path(os.path.join(self.base_path, "mocks")).resolve()

        assert (
            self.directory_path.exists()
        ), 'A directory should exist with path "{self.directory_path}"'

        assert (
            not self.directory_path.is_file()
        ), f'directory_path "{self.directory_path}" should not be a file.'

        # Path to an existing file.
        self.file_path = Path(
            os.path.join(self.base_path, "mocks/InsertContentDocument.file.txt")
        ).resolve()

        assert (
            self.file_path.exists()
        ), 'A file should exist with path "{self.file_path}"'

        assert (
            self.file_path.is_file()
        ), f'file_path "{self.file_path}" should be a file.'

        # Resusable data
        self.queries = ["query_1", "query_2", "query_3"]
        self.content_version_id = "0681k000001YWQ5AAO"
        self.content_document_id = "0691k000001LtfEAAS"
        self.e = SalesforceMalformedRequest(
            "url",
            "status",
            "resource_name",
            [
                {"message": "Error message 1.", "errorCode": "ERROR_1"},
                {"errorCode": "ERROR_2"},
                {"message": "Error message 3.", "errorCode": "ERROR_3"},
            ],
        )
        self.expected_exception_message = "Error message 1.; Unknown.; Error message 3."
        # TODO: change to record_ids
        self.user_id = "0051k000003cEL3AAM"

        # Set up REST API configuration.

        """
        self.task = create_task(
            InsertContentDocument,
            {"path": self.file_path, "queries": self.queries},
        )
        self.task.logger = mock.Mock()
        # self.task.sf = mock.Mock()
        """

    """
    def test_get_user_id_by_query__valid_query__0_records(self):
        # where is prefixed with "where " which will be stripped when injected into the query.
        where = "where (FirstName = 'User' OR LastName = 'User') AND IsActive = true AND CreatedDate = TODAY"
        expected_query = "SELECT Id FROM User WHERE (FirstName = 'User' OR LastName = 'User') AND IsActive = true AND CreatedDate = TODAY LIMIT 2"

        self.task.sf.query_all.return_value = {"records": []}

        self.task.logger.info._expected_calls = [
            mock.call(f"Querying User: {expected_query}")
        ]

        # Execute the test
        with pytest.raises(CumulusCIException) as e:
            self.task._get_user_id_by_query(where)

        assert e.value.args[0] == "No Users found."

        self.task.sf.query_all.assert_called_once_with(expected_query)
        self.task.logger.info.assert_has_calls(self.task.logger.info._expected_calls)

    def test_get_user_id_by_query__valid_query__1_record(self):
        # where is prefixed with "where " which will be stripped when injected into the query.
        where = "where (FirstName = 'User' OR LastName = 'User') AND IsActive = true AND CreatedDate = TODAY"
        expected_query = "SELECT Id FROM User WHERE (FirstName = 'User' OR LastName = 'User') AND IsActive = true AND CreatedDate = TODAY LIMIT 2"

        expected = self.user_id

        self.task.sf.query_all.return_value = {"records": [{"Id": expected}]}

        self.task.logger.info._expected_calls = [
            mock.call(f"Querying User: {expected_query}"),
            mock.call(f"Uploading profile photo for the User with ID {expected}"),
        ]

        # Execute the test
        actual = self.task._get_user_id_by_query(where)

        assert expected == actual

        self.task.sf.query_all.assert_called_once_with(expected_query)
        self.task.logger.info.assert_has_calls(self.task.logger.info._expected_calls)

    def test_get_user_id_by_query__valid_query__2_records(self):
        # where is prefixed with "where " which will be stripped when injected into the query.
        where = "where (FirstName = 'User' OR LastName = 'User') AND IsActive = true AND CreatedDate = TODAY"
        expected_query = "SELECT Id FROM User WHERE (FirstName = 'User' OR LastName = 'User') AND IsActive = true AND CreatedDate = TODAY LIMIT 2"

        id_0 = self.user_id
        id_1 = "0051k000003cEL8AAM"

        self.task.sf.query_all.return_value = {"records": [{"Id": id_0}, {"Id": id_1}]}

        self.task.logger.info._expected_calls = [
            mock.call(f"Querying User: {expected_query}")
        ]

        # Execute the test
        with pytest.raises(CumulusCIException) as e:
            self.task._get_user_id_by_query(where)

        assert (
            e.value.args[0] == f"More than one User found (at least 2): {id_0}, {id_1}"
        )

        self.task.sf.query_all.assert_called_once_with(expected_query)
        self.task.logger.info.assert_has_calls(self.task.logger.info._expected_calls)

    def test_get_user_id_by_query__invalid_query(self):
        where = "(FirstName = 'User' OR LastName = 'User') AND IsActive = true AND CreatedDate = TODAY but the end of this query is invalid SOQL "
        expected_query = "SELECT Id FROM User WHERE (FirstName = 'User' OR LastName = 'User') AND IsActive = true AND CreatedDate = TODAY but the end of this query is invalid SOQL  LIMIT 2"

        self.task.sf.query_all.side_effect = self.e

        self.task.logger.info._expected_calls = [
            mock.call(f"Querying User: {expected_query}")
        ]

        # Execute the test
        with pytest.raises(CumulusCIException) as e:
            self.task._get_user_id_by_query(where)

        assert e.value.args[0] == self.expected_exception_message

        self.task.sf.query_all.assert_called_once_with(expected_query)
        self.task.logger.info.assert_has_calls(self.task.logger.info._expected_calls)

    def test_get_default_user_id(self):
        expected = self.user_id

        self.task.sf.restful.return_value = {
            "identity": f"a bunch of other things{expected}"
        }

        actual = self.task._get_default_user_id()

        assert expected == actual

        self.task.logger.info.assert_called_once_with(
            f"Uploading profile photo for the default User with ID {expected}"
        )
    """

    def test_init_options__path_does_not_exist(self):
        fake_path = "not a real/path/to/a/file"
        with pytest.raises(CumulusCIException) as e:
            create_task(
                InsertContentDocument,
                {"path": fake_path},
            )

        assert e.value.args[0] == f'Invalid "path". No file found at {fake_path}'

    def test_init_options__path_points_to_directory(self):
        with pytest.raises(CumulusCIException) as e:
            create_task(
                InsertContentDocument,
                {"path": self.directory_path},
            )

        assert (
            e.value.args[0] == f'Invalid "path". No file found at {self.directory_path}'
        )

    def test_init_options__path_points_to_file__default_options(self):
        task = create_task(
            InsertContentDocument,
            {"path": self.file_path},
        )

        assert task.options["path"] == Path(
            self.file_path
        ), '"path" option should be a Path instance pointint to self.file_path.'

        assert (
            task.options["queries"] is None
        ), 'The default "queries" option should be None.'

        assert (
            task.options["share_type"] == "I"
        ), 'The default "share_type" option should equal "I".'

        assert (
            task.options["visibility"] == "AllUsers"
        ), 'The default "visibility" option should equal "AllUsers".'

    def test_init_options__path_points_to_file__override_options(self):
        queries = ",".join(self.queries)
        share_type = "V"
        visibility = "SharedUsers"

        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": queries,
                "share_type": share_type,
                "visibility": visibility,
            },
        )

        assert task.options["path"] == Path(
            self.file_path
        ), '"path" option should be a Path instance pointint to self.file_path.'

        assert (
            task.options["queries"] == self.queries
        ), '"queries" option should be overridden.'

        assert (
            task.options["share_type"] == share_type
        ), '"share_type" option should be overridden.'

        assert (
            task.options["visibility"] == visibility
        ), '"visibility" option should be overridden.'

    """
    @responses.activate
    def test_insert_content_document__exception_creating_content_document(self):
        errors = "the reason why inserting the ContentVersion failed"
        self.task.sf.ContentVersion.create.return_value = {
            "success": False,
            "errors": errors,
        }

        with temporary_dir() as d:
            # Copy photo to temporary direcory.
            shutil.copy(str(self.file_path), d)
            temp_photo_path = pathlib.Path(os.path.join(d, self.file)).resolve()
            assert (
                temp_photo_path.exists()
            ), "photo mock was not copied to the temporary directory"
            assert (
                temp_photo_path.is_file()
            ), "Path the the photo mock in the temporary directory should point to a file"

            self.task.sf.ContentVersion.create._expected_calls = [
                mock.call(
                    {
                        "PathOnClient": temp_photo_path.name,
                        "Title": temp_photo_path.stem,
                        "VersionData": base64.b64encode(
                            temp_photo_path.read_bytes()
                        ).decode("utf-8"),
                    }
                )
            ]

            with pytest.raises(CumulusCIException) as e:
                self.task._insert_content_document(self.file)

        assert e.value.args[0] == f"Failed to create photo ContentVersion: {errors}"

        self.task.sf.ContentVersion.create.assert_has_calls(
            self.task.sf.ContentVersion.create._expected_calls
        )

        self.task.logger.info.assert_called_once_with(
            f"Setting user photo to {self.file}"
        )
    """

    @responses.activate
    def test_insert_content_document__success(self):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": self.queries,
            },
        )
        task.logger = mock.Mock()

        api_version = f"v{task.project_config.project__package__api_version}"
        token_url = f"{task.org_config.instance_url}/services/data"
        rest_url = f"{token_url}/{api_version}"

        # Get access token call.
        responses.add(
            responses.GET,
            token_url,
            json=[{"version": task.project_config.project__package__api_version}],
        )

        # Insert ContentVersion call.
        responses.add(
            responses.POST,
            f"{rest_url}/sobjects/ContentVersion/",
            content_type="application/json",
            status=201,
            json={"id": self.content_version_id, "success": True, "errors": []},
        )

        # Query ContentVersion.ContentDocumentId call.
        responses.add(
            responses.GET,
            f"{rest_url}/query/?q=SELECT+Id%2C+ContentDocumentId+FROM+ContentVersion+WHERE+Id+%3D+%27{self.content_version_id}%27",
            content_type="application/json",
            status=201,
            json={
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "ContentVersion",
                            "url": f"/services/data/{api_version}/sobjects/ContentVersion/{self.content_version_id}",
                        },
                        "Id": self.content_version_id,
                        "ContentDocumentId": self.content_document_id,
                    }
                ],
            },
        )

        # Initialize REST API
        task._init_task()

        # Execute _insert_content_document.
        assert (
            self.content_document_id == task._insert_content_document()
        ), "_insert_content_document should execute successfully and return the inserted ContentVersion.ContentDocumentId."

    """
    def test_delete_content_document(self):
        self.task._delete_content_document(self.content_document_id)

        self.task.sf.ContentDocument.delete.assert_called_once_with(
            self.content_document_id
        )

    def test_assign_user_profile_photo__exception(self):
        self.task.sf.restful.side_effect = self.e
        self.task.logger.error._expected_calls = [
            mock.call(
                "An error occured assigning the ContentDocument as the users's profile photo."
            ),
            mock.call(f"Deleting ContentDocument {self.content_document_id}"),
        ]
        self.task._delete_content_document = mock.Mock()

        with pytest.raises(CumulusCIException) as e:
            self.task._assign_user_profile_photo(self.user_id, self.content_document_id)

        assert e.value.args[0] == self.expected_exception_message

        self.task._delete_content_document.assert_called_once_with(
            self.content_document_id
        )

        self.task.logger.error.assert_has_calls(self.task.logger.error._expected_calls)

    def test_assign_user_profile_photo__success(self):
        self.task._delete_content_document = mock.Mock()

        self.task._assign_user_profile_photo(self.user_id, self.content_document_id)

        self.task.sf.restful.assert_called_once_with(
            f"connect/user-profiles/{self.user_id}/photo",
            data=json.dumps({"fileId": self.content_document_id}),
            method="POST",
        )

        self.task._delete_content_document.assert_not_called()

        self.task.logger.error.assert_not_called()

    def test_run_task__default_user(self):
        assert bool(self.task.options.get("where")) is False

        self.task._get_default_user_id = mock.Mock()
        self.task._get_user_id_by_query = mock.Mock()
        self.task._insert_content_document = mock.Mock()
        self.task._assign_user_profile_photo = mock.Mock()

        self.task._run_task()

        self.task._get_default_user_id.assert_called_once_with()

        self.task._get_user_id_by_query.assert_not_called()

        self.task._insert_content_document.assert_called_once_with(
            self.task.options["photo"]
        )

        self.task._assign_user_profile_photo.assert_called_once_with(
            self.task._get_default_user_id.return_value,
            self.task._insert_content_document.return_value,
        )

    def test_run_task__queries_user(self):
        self.task.options["where"] = mock.Mock()
        assert bool(self.task.options.get("where")) is True

        self.task._get_default_user_id = mock.Mock()
        self.task._get_user_id_by_query = mock.Mock()
        self.task._insert_content_document = mock.Mock()
        self.task._assign_user_profile_photo = mock.Mock()

        self.task._run_task()

        self.task._get_default_user_id.assert_not_called()

        self.task._get_user_id_by_query.assert_called_once_with(
            self.task.options["where"]
        )

        self.task._insert_content_document.assert_called_once_with(
            self.task.options["photo"]
        )

        self.task._assign_user_profile_photo.assert_called_once_with(
            self.task._get_user_id_by_query.return_value,
            self.task._insert_content_document.return_value,
        )
    """
