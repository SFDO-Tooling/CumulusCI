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
def retrieve_profile_task():
    project_config = MagicMock()
    task_config = TaskConfig({"options": {"profiles": "Profile1, Profile2"}})
    org_config = MagicMock()
    task = RetrieveProfile(project_config, task_config, org_config)
    return task


def test_init_options(retrieve_profile_task):
    assert retrieve_profile_task.options["profiles"] == "Profile1, Profile2"


def create_temp_zip_file():
    temp_zipfile = NamedTemporaryFile(delete=True)

    with zipfile.ZipFile(temp_zipfile, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("profiles/Profile1.profile", "")
        zipf.writestr("profiles/Profile2.profile", "")
        zipf.writestr("profiles/Profile3.profile", "")

    return zipfile.ZipFile(temp_zipfile, "r")


def test_run_task(retrieve_profile_task, tmpdir):
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
    profile2_path = os.path.join(tmpdir, "profiles/Profile2.profile")
    profile3_path = os.path.join(tmpdir, "profiles/Profile3.profile")

    assert os.path.exists(profile1_path)
    assert os.path.exists(profile2_path)
    assert os.path.exists(profile3_path)


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
