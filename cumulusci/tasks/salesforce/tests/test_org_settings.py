import base64
import io
import json
import os
import pathlib
import zipfile
from unittest.mock import Mock

import pytest

from cumulusci.tasks.salesforce.org_settings import (
    DeployOrgSettings,
    build_settings_package,
)
from cumulusci.utils import temporary_dir

from .util import create_task


class TestDeployOrgSettings:
    def test_run_task__json_only(self):
        with temporary_dir() as d:
            with open("dev.json", "w") as f:
                json.dump(
                    {
                        "settings": {
                            "orgPreferenceSettings": {"s1DesktopEnabled": True},
                            "otherSettings": {
                                "nestedDict": {
                                    "boolValue": True,
                                    "stringValue": "string",
                                },
                                "nestedList": [
                                    {
                                        "boolValue": True,
                                        "stringValue": "foo",
                                    },
                                    {
                                        "boolValue": False,
                                        "stringValue": "bar",
                                    },
                                ],
                            },
                        },
                    },
                    f,
                )
            path = os.path.join(d, "dev.json")
            task_options = {"definition_file": path, "api_version": "48.0"}
            task = create_task(DeployOrgSettings, task_options)
            task.api_class = Mock()
            task()

        package_zip = task.api_class.call_args[0][1]
        zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(package_zip)), "r")
        assert (
            readtext(zf, "package.xml")
            == """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>OrgPreference</members>
        <members>Other</members>
        <name>Settings</name>
    </types>
    <version>48.0</version>
</Package>"""
        )
        assert (
            readtext(zf, "settings/OrgPreference.settings")
            == """<?xml version="1.0" encoding="UTF-8"?>
<OrgPreferenceSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <preferences>
        <settingName>S1DesktopEnabled</settingName>
        <settingValue>True</settingValue>
    </preferences>
</OrgPreferenceSettings>"""
        )
        assert (
            readtext(zf, "settings/Other.settings")
            == """<?xml version="1.0" encoding="UTF-8"?>
<OtherSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <nestedDict>
        <boolValue>true</boolValue>
        <stringValue>string</stringValue>
    </nestedDict>
    <nestedList>
        <boolValue>true</boolValue>
        <stringValue>foo</stringValue>
    </nestedList>
    <nestedList>
        <boolValue>false</boolValue>
        <stringValue>bar</stringValue>
    </nestedList>
</OtherSettings>"""
        )
        zf.close()

    def test_run_task__json_only__with_org_settings(self):
        with temporary_dir() as d:
            with open("dev.json", "w") as f:
                json.dump(
                    {
                        "settings": {
                            "orgPreferenceSettings": {"s1DesktopEnabled": True},
                            "otherSettings": {
                                "nested": {
                                    "boolValue": True,
                                    "stringValue": "string",
                                },
                            },
                        },
                        "objectSettings": {"foo__c": {"sharingModel": "Private"}},
                    },
                    f,
                )
            path = os.path.join(d, "dev.json")
            task_options = {"definition_file": path, "api_version": "48.0"}
            task = create_task(DeployOrgSettings, task_options)
            task.api_class = Mock()
            task()

        package_zip = task.api_class.call_args[0][1]
        zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(package_zip)), "r")
        # The context manager's output is tested separately, below.
        assert (
            readtext(zf, "package.xml")
            == """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Foo__c</members>
        <name>CustomObject</name>
    </types>
    <types>
        <members>OrgPreference</members>
        <members>Other</members>
        <name>Settings</name>
    </types>
    <version>48.0</version>
</Package>"""
        )
        zf.close()

    def test_run_task__settings_only(self):
        settings = {
            "orgPreferenceSettings": {"s1DesktopEnabled": True},
            "otherSettings": {
                "nested": {
                    "boolValue": True,
                    "stringValue": "string",
                },
            },
        }
        task_options = {"settings": settings, "api_version": "48.0"}
        task = create_task(DeployOrgSettings, task_options)
        task.api_class = Mock()
        task()

        package_zip = task.api_class.call_args[0][1]
        zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(package_zip)), "r")
        assert (
            readtext(zf, "package.xml")
            == """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>OrgPreference</members>
        <members>Other</members>
        <name>Settings</name>
    </types>
    <version>48.0</version>
</Package>"""
        )
        assert (
            readtext(zf, "settings/OrgPreference.settings")
            == """<?xml version="1.0" encoding="UTF-8"?>
<OrgPreferenceSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <preferences>
        <settingName>S1DesktopEnabled</settingName>
        <settingValue>True</settingValue>
    </preferences>
</OrgPreferenceSettings>"""
        )
        assert (
            readtext(zf, "settings/Other.settings")
            == """<?xml version="1.0" encoding="UTF-8"?>
<OtherSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <nested>
        <boolValue>true</boolValue>
        <stringValue>string</stringValue>
    </nested>
</OtherSettings>"""
        )
        zf.close()

    def test_run_task__json_and_settings(self):
        with temporary_dir() as d:
            with open("dev.json", "w") as f:
                json.dump(
                    {
                        "settings": {
                            "orgPreferenceSettings": {"s1DesktopEnabled": True},
                        },
                    },
                    f,
                )
            path = os.path.join(d, "dev.json")
            settings = {
                "otherSettings": {
                    "nested": {
                        "boolValue": True,
                        "stringValue": "string",
                    },
                },
            }
            task_options = {
                "definition_file": path,
                "settings": settings,
                "api_version": "48.0",
            }
            task = create_task(DeployOrgSettings, task_options)
            task.api_class = Mock()
            task()

        package_zip = task.api_class.call_args[0][1]
        zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(package_zip)), "r")
        assert (
            readtext(zf, "package.xml")
            == """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>OrgPreference</members>
        <members>Other</members>
        <name>Settings</name>
    </types>
    <version>48.0</version>
</Package>"""
        )
        assert (
            readtext(zf, "settings/OrgPreference.settings")
            == """<?xml version="1.0" encoding="UTF-8"?>
<OrgPreferenceSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <preferences>
        <settingName>S1DesktopEnabled</settingName>
        <settingValue>True</settingValue>
    </preferences>
</OrgPreferenceSettings>"""
        )
        assert (
            readtext(zf, "settings/Other.settings")
            == """<?xml version="1.0" encoding="UTF-8"?>
<OtherSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <nested>
        <boolValue>true</boolValue>
        <stringValue>string</stringValue>
    </nested>
</OtherSettings>"""
        )
        zf.close()

    def test_run_task__no_settings(self):
        with temporary_dir() as d:
            with open("dev.json", "w") as f:
                f.write("{}")
            path = os.path.join(d, "dev.json")
            task_options = {"definition_file": path}
            task = create_task(DeployOrgSettings, task_options)
            task.api_class = Mock()
            task()
            assert not task.api_class.called

    def test_run_task_bad_settings_type(self):
        with temporary_dir() as d:
            with open("dev.json", "w") as f:
                json.dump(
                    {
                        "settings": {
                            "otherSettings": {
                                "none": None,
                            },
                        },
                    },
                    f,
                )
            path = os.path.join(d, "dev.json")
            task_options = {"definition_file": path, "api_version": "48.0"}
            task = create_task(DeployOrgSettings, task_options)
            task.api_class = Mock()
            with pytest.raises(TypeError):
                task()

    def test_run_task_bad_nested_list_settings_type(self):
        with temporary_dir() as d:
            with open("dev.json", "w") as f:
                json.dump(
                    {
                        "settings": {
                            "otherSettings": {
                                "nestedList": ["foo"],
                            },
                        },
                    },
                    f,
                )
            path = os.path.join(d, "dev.json")
            task_options = {"definition_file": path, "api_version": "48.0"}
            task = create_task(DeployOrgSettings, task_options)
            task.api_class = Mock()
            with pytest.raises(TypeError):
                task()


def readtext(zf, name):
    with zf.open(name, "r") as f:
        return io.TextIOWrapper(f).read()


class TestBuildSettingsPackage:
    def test_build_settings_package(self):
        settings = {
            "otherSettings": {
                "nested": {
                    "boolValue": True,
                    "stringValue": "string",
                },
            }
        }
        object_settings = {
            "account": {
                "defaultRecordType": "Default",
                "sharingModel": "Public",
            },
            "solution": {"defaultRecordType": "Default"},
        }
        with build_settings_package(settings, object_settings, "48.0") as path:
            assert (
                (pathlib.Path(path) / "package.xml").read_text()
                == """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Solution.DefaultSolution</members>
        <name>BusinessProcess</name>
    </types>
    <types>
        <members>Account.Default</members>
        <members>Solution.Default</members>
        <name>RecordType</name>
    </types>
    <types>
        <members>Other</members>
        <name>Settings</name>
    </types>
    <version>48.0</version>
</Package>"""
            )
            assert (
                (pathlib.Path(path) / "settings" / "Other.settings").read_text()
                == """<?xml version="1.0" encoding="UTF-8"?>
<OtherSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <nested>
        <boolValue>true</boolValue>
        <stringValue>string</stringValue>
    </nested>
</OtherSettings>"""
            )

            rm_ws = "".maketrans("", "", " \t \n")

            assert (
                (pathlib.Path(path) / "objects" / "Account.object")
                .read_text()
                .translate(rm_ws)
                == """<?xml version="1.0" encoding="UTF-8"?>
<Object xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingModel>Public</sharingModel>
    <recordTypes>
        <fullName>Default</fullName>
        <label>Default</label>
        <active>true</active>
    </recordTypes>
</Object>""".translate(
                    rm_ws
                )
            )
            assert (
                (pathlib.Path(path) / "objects" / "Solution.object")
                .read_text()
                .translate(rm_ws)
                == """<?xml version="1.0" encoding="UTF-8"?>
<Object xmlns="http://soap.sforce.com/2006/04/metadata">

    <recordTypes>
        <fullName>Default</fullName>
        <label>Default</label>
        <active>true</active>
        <businessProcess>DefaultSolution</businessProcess>
    </recordTypes>

    <businessProcesses>
        <fullName>DefaultSolution</fullName>
        <isActive>true</isActive>
        <values>
            <fullName>Draft</fullName>
        </values>
    </businessProcesses>
</Object>""".translate(
                    rm_ws
                )
            )
