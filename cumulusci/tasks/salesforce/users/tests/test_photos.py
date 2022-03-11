import base64
import json
import os
import pathlib
import shutil
from unittest import mock

import pytest  # noqa: F401
from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.exceptions import CumulusCIException  # noqa: F401
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.salesforce.users.photos import UploadProfilePhoto, join_errors
from cumulusci.utils import temporary_dir


def test_join_errors():
    e = SalesforceMalformedRequest(
        "url",
        "status",
        "resource_name",
        [
            {"message": "Error message 1.", "errorCode": "ERROR_1"},
            {"message": "Error message 2.", "errorCode": "ERROR_2"},
            {"message": "Error message 3.", "errorCode": "ERROR_3"},
        ],
    )

    assert join_errors(e) == "Error message 1.; Error message 2.; Error message 3."


class TestUploadProfilePhoto:
    def setup_method(self):
        # Photo information
        self.photo = "photo.mock.txt"
        self.base_path = os.path.dirname(__file__)
        self.photo_path = pathlib.Path(
            os.path.join(self.base_path, self.photo)
        ).resolve()
        assert self.photo_path.exists(), "photo mock cannot be found"
        assert self.photo_path.is_file(), "photo_path should point to a file"

        # Resusable data
        self.content_version_id = "0681k000001YWQ5AAO"
        self.content_document_id = "0691k000001LtfEAAS"

        self.e = SalesforceMalformedRequest(
            "url",
            "status",
            "resource_name",
            [
                {"message": "Error message 1.", "errorCode": "ERROR_1"},
                {"message": "Error message 2.", "errorCode": "ERROR_2"},
                {"message": "Error message 3.", "errorCode": "ERROR_3"},
            ],
        )
        self.expected_exception_message = (
            "Error message 1.; Error message 2.; Error message 3."
        )
        self.user_id = "0051k000003cEL3AAM"

        # Task with mocks
        self.task = create_task(UploadProfilePhoto, {"photo": self.photo})
        self.task.logger = mock.Mock()
        self.task.sf = mock.Mock()

    def test_raise_cumulusci_exception(self):
        with pytest.raises(CumulusCIException) as e:
            self.task._raise_cumulusci_exception(self.e)

        assert e.value.args[0] == self.expected_exception_message

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

    def test_insert_content_document__no_photo_found(self):
        with temporary_dir():
            with pytest.raises(CumulusCIException) as e:
                self.task._insert_content_document(self.photo)

            assert e.value.args[0] == f"No photo found at {self.photo}"

    def test_insert_content_document__exception_creating_content_document(self):
        errors = "the reason why inserting the ContentVersion failed"
        self.task.sf.ContentVersion.create.return_value = {
            "success": False,
            "errors": errors,
        }

        with temporary_dir() as d:
            # Copy photo to temporary direcory.
            shutil.copy(str(self.photo_path), d)
            temp_photo_path = pathlib.Path(os.path.join(d, self.photo)).resolve()
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
                self.task._insert_content_document(self.photo)

        assert e.value.args[0] == f"Failed to create photo ContentVersion: {errors}"

        self.task.sf.ContentVersion.create.assert_has_calls(
            self.task.sf.ContentVersion.create._expected_calls
        )

        self.task.logger.info.assert_called_once_with(
            f"Setting user photo to {self.photo}"
        )

    def test_insert_content_document__success(self):
        self.task.sf.ContentVersion.create.return_value = {
            "success": True,
            "id": self.content_version_id,
        }
        self.task.sf.query.return_value = {
            "records": [
                {
                    "Id": self.content_version_id,
                    "ContentDocumentId": self.content_document_id,
                }
            ]
        }
        self.task.logger.info._expected_calls = [
            mock.call(f"Setting user photo to {self.photo}"),
            mock.call(
                f"Uploaded profile photo ContentDocument {self.content_document_id}"
            ),
        ]

        expected = self.content_document_id

        with temporary_dir() as d:
            # Copy photo to temporary direcory.
            shutil.copy(str(self.photo_path), d)
            temp_photo_path = pathlib.Path(os.path.join(d, self.photo)).resolve()
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

            actual = self.task._insert_content_document(self.photo)

        assert expected == actual

        self.task.sf.ContentVersion.create.assert_has_calls(
            self.task.sf.ContentVersion.create._expected_calls
        )

        self.task.sf.query.assert_called_once_with(
            f"SELECT Id, ContentDocumentId FROM ContentVersion WHERE Id = '{self.content_version_id}'"
        )

        self.task.logger.info.assert_has_calls(self.task.logger.info._expected_calls)

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
