import pytest  # noqa: F401
from unittest import mock
from cumulusci.tasks.salesforce.tests.util import create_task

from cumulusci.tasks.salesforce import (
    UploadDefaultUserProfilePhoto,  # noqa: F401
    UploadUserProfilePhoto,  # noqa: F401
)
from cumulusci.core.exceptions import CumulusCIException  # noqa: F401


class TestUploadDefaultUserProfilePhoto:
    def setup_method(self):
        self.task = create_task(
            UploadDefaultUserProfilePhoto, {"photo_path": "path/to/profile/photo.png"}
        )

    def test_get_user_id(self):
        expected = "user_id_0001"

        self.task.sf = mock.Mock()
        self.task.sf.restful.return_value = {"identity": expected}
        self.task.logger = mock.Mock()

        actual = self.task.get_user_id()

        assert expected == actual

        self.task.sf.restful.assert_called_once_with("")
        self.task.logger.info.assert_called_once_with(
            f"Uploading profile photo for the default User with ID {expected}."
        )

    @mock.patch("builtins.open", new_callable=mock.mock_open, read_data="photo fi")
    @mock.patch("base64.b64encode")
    @mock.patch("os.path")
    @mock.patch("json.loads")
    def test_run_task__failed_inserting_content_version(
        self, open_mock, base64_base64encode_mock, os_path_mock, json_loads_mock
    ):
        # Calculated variables
        path = self.task.options["photo_path"]

        # Mocks
        self.task.get_user_id = mock.Mock()
        self.task.logger = mock.Mock()
        self.task.logger.info._expected_calls = [
            mock.call(f"Setting user photo to {path}")
        ]


class TestUploadUserProfilePhoto:
    def setup_method(self):
        self.task = create_task(
            UploadUserProfilePhoto,
            {
                "user_field": "Alias",
                "user_field_value": "grace",
                "photo_path": "path/to/profile/photo.png",
            },
        )
