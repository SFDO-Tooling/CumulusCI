from unittest.mock import Mock
import base64
import io
import json
import os
import zipfile

import pytest

from cumulusci.tasks.salesforce.org_settings import DeployOrgSettings
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
                                "nested": {
                                    "boolValue": True,
                                    "stringValue": "string",
                                },
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
        <members>*</members>
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
        <members>*</members>
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
        <members>*</members>
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
                                "list": [],
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
