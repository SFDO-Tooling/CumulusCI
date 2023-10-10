import logging
import os
import xml.etree.ElementTree as ET
import zipfile
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

import pytest

from cumulusci.core.config import TaskConfig
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.salesforce_api.retrieve_profile_api import RetrieveProfileApi
from cumulusci.tasks.salesforce.retrieve_profile import RetrieveProfile


@pytest.fixture
def retrieve_profile_task(tmpdir):
    project_config = MagicMock()
    task_config = TaskConfig(
        {"options": {"profiles": ["Profile1", "Profile2"], "target": tmpdir}}
    )
    org_config = MagicMock()
    task = RetrieveProfile(project_config, task_config, org_config)
    task.logger = logging.getLogger(__name__)
    task.logger.setLevel(logging.DEBUG)
    return task


def test_init_options(retrieve_profile_task):
    retrieve_profile_task._init_options(retrieve_profile_task.task_config.config)
    assert retrieve_profile_task.profiles == ["Profile1", "Profile2"]


def test_init_options_raises_error_with_no_profiles():
    project_config = MagicMock()
    task_config = TaskConfig({"options": {"profiles": None}})
    org_config = MagicMock()

    with pytest.raises(ValueError) as exc_info:
        RetrieveProfile(project_config, task_config, org_config)

    assert str(exc_info.value) == "At least one profile must be specified."


def test_init_options_raises_error_with_invalid_target_directory():
    project_config = MagicMock()
    task_config = TaskConfig(
        {"options": {"profiles": ["Profile1"], "target": "/nonexistent/directory"}}
    )
    org_config = MagicMock()

    with pytest.raises(FileNotFoundError) as exc_info:
        RetrieveProfile(project_config, task_config, org_config)

    expected_message = "The extract directory '/nonexistent/directory' does not exist."
    assert str(exc_info.value) == expected_message


def test_init_options_raises_error_with_non_directory_target(tmp_path):
    tmpfile = tmp_path / "file.txt"
    tmpfile.write_text("Something")
    project_config = MagicMock()
    task_config = TaskConfig({"options": {"profiles": ["Profile1"], "target": tmpfile}})
    org_config = MagicMock()

    with pytest.raises(NotADirectoryError) as exc_info:
        RetrieveProfile(project_config, task_config, org_config)

    expected_message = f"'{tmpfile}' is not a directory."
    assert str(exc_info.value) == expected_message


def create_temp_zip_file():
    temp_zipfile = NamedTemporaryFile(delete=True)

    with zipfile.ZipFile(temp_zipfile, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("profiles/Profile1.profile", "")

    return zipfile.ZipFile(temp_zipfile, "r")


def test_run_task(retrieve_profile_task, tmpdir, caplog):
    retrieve_profile_task.extract_dir = tmpdir
    temp_zipfile = create_temp_zip_file()

    with patch.object(
        RetrieveProfileApi,
        "_retrieve_permissionable_entities",
        return_value={"ApexClass": ["TestApexClass"]},
    ), patch.object(
        RetrieveProfileApi, "_init_task", return_value="something"
    ), patch.object(
        ApiRetrieveUnpackaged, "__call__", return_value=temp_zipfile
    ):
        retrieve_profile_task._run_task()

    assert os.path.exists(tmpdir)
    profile1_path = os.path.join(tmpdir, "profiles/Profile1.profile")
    assert os.path.exists(profile1_path)

    log_messages = [record.message for record in caplog.records]
    print(log_messages)
    assert f"Profiles Profile1 unzipped into folder '{tmpdir}'" in log_messages
    assert (
        f"Profiles Profile1, Profile2 unzipped into folder '{tmpdir}'"
        not in log_messages
    )
    assert (
        "The following profiles were not found or could not be retrieved: Profile2"
        in log_messages
    )


def test_get_api(retrieve_profile_task):
    retrieve_profile_task.package_xml = ""
    api = retrieve_profile_task._get_api()
    assert isinstance(api, ApiRetrieveUnpackaged)


def remove_whitespace(xml_str):
    return "".join(line.strip() for line in xml_str.splitlines())


def compare_xml_strings(xml_str1, xml_str2):
    xml_str1 = remove_whitespace(xml_str1)
    xml_str2 = remove_whitespace(xml_str2)

    tree1 = ET.ElementTree(ET.fromstring(xml_str1))
    tree2 = ET.ElementTree(ET.fromstring(xml_str2))

    parsed_xml_str1 = ET.tostring(tree1.getroot(), encoding="unicode")
    parsed_xml_str2 = ET.tostring(tree2.getroot(), encoding="unicode")

    return parsed_xml_str1 == parsed_xml_str2


def test_create_package_xml(retrieve_profile_task):
    input_dict = {
        "ApexClass": ["Class1", "Class2"],
        "Profile": ["Profile1", "Profile2"],
    }
    package_xml = retrieve_profile_task._create_package_xml(input_dict)

    expected_package_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Package xmlns="http://soap.sforce.com/2006/04/metadata">
        <types>
            <members>Class1</members>
            <members>Class2</members>
            <name>ApexClass</name>
        </types>
        <types>
            <members>Profile1</members>
            <members>Profile2</members>
            <name>Profile</name>
        </types>
        <version>58.0</version>
    </Package>"""

    assert compare_xml_strings(package_xml, expected_package_xml)


if __name__ == "__main__":
    pytest.main()