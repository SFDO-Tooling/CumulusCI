import os
import shutil
from tempfile import mkdtemp
from pathlib import Path

from unittest import mock
from unittest.mock import Mock, patch

import pytest
from pytest_mock import mocker

from cumulusci.core.config import (
    BaseProjectConfig,
    OrgConfig,
    ScratchOrgConfig,
    ServiceConfig,
    TaskConfig,
    UniversalConfig,
)
from cumulusci.core.config.sfdx_org_config import SfdxOrgConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.keychain.base_project_keychain import BaseProjectKeychain
from cumulusci.core.keychain.tests.conftest import org_config
from cumulusci.tasks import util
from cumulusci.tests.util import DummyLogger
from cumulusci.utils import temporary_dir

OMNISTUDIO_LWC_XML = """<?xml version="1.0" encoding="UTF-8"?>
<RemoteSiteSetting xmlns="http://soap.sforce.com/2006/04/metadata">
    <disableProtocolSecurity>false</disableProtocolSecurity>
    <isActive>true</isActive>
    <url>${OmniStudioLightning}</url>
</RemoteSiteSetting>
"""

OMNISTUDIO_VISUALFORCE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<RemoteSiteSetting xmlns="http://soap.sforce.com/2006/04/metadata">
    <disableProtocolSecurity>false</disableProtocolSecurity>
    <isActive>true</isActive>
    <url>${OmniStudioVisualforce}</url>
</RemoteSiteSetting>
"""


class TestUtilTasks:
    def setup_method(self, method):
        self.old_dir = os.getcwd()
        self.tempdir = mkdtemp()
        os.chdir(self.tempdir)
        os.mkdir(os.path.join(self.tempdir, ".git"))
        self.universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.org_config = OrgConfig({}, "test")
        self.task_config = TaskConfig({})

    def teardown_method(self):
        os.chdir(self.old_dir)
        shutil.rmtree(self.tempdir)

    @mock.patch("cumulusci.tasks.util.download_extract_zip")
    def test_DownloadZip(self, download_extract_zip):
        target = os.path.join(self.tempdir, "extracted")
        task_config = TaskConfig({"options": {"url": "http://test", "dir": target}})
        task = util.DownloadZip(self.project_config, task_config, self.org_config)
        task()
        download_extract_zip.assert_called_once_with("http://test", target, None)

    def test_ListMetadataTypes(self):
        os.mkdir(os.path.join(self.tempdir, "src"))
        package_xml_path = os.path.join(self.tempdir, "src", "package.xml")
        with open(package_xml_path, "w") as f:
            f.write(
                """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Test__c</members>
        <name>CustomObject</name>
    </types>
</Package>"""
            )

        task = util.ListMetadataTypes(
            self.project_config, self.task_config, self.org_config
        )
        task.logger = DummyLogger()
        task()

        output = task.logger.get_output()
        assert "Metadata types found" in output
        assert "CustomObject" in output

    @mock.patch("cumulusci.tasks.util.time")
    def test_Sleep(self, time):
        task_config = TaskConfig({"options": {"seconds": "1"}})
        task = util.Sleep(self.project_config, task_config, self.org_config)
        task()
        time.sleep.assert_called_once_with(1)

    def test_Delete__single_file(self):
        file_path = os.path.join(self.tempdir, "file")
        with open(file_path, "w"):
            pass

        task_config = TaskConfig({"options": {"path": "file"}})
        task = util.Delete(self.project_config, task_config, self.org_config)
        task()

        assert not os.path.exists(file_path)

    def test_Delete__glob(self):
        target = os.path.join(self.tempdir, "dir1")
        os.mkdir(target)
        file_path = os.path.join(target, "file")
        with open(file_path, "w"):
            pass

        task_config = TaskConfig({"options": {"path": ["*"], "chdir": target}})
        task = util.Delete(self.project_config, task_config, self.org_config)
        task()

        assert not os.path.exists(file_path)

    def test_Delete__subdir(self):
        target = os.path.join(self.tempdir, "dir1")
        os.mkdir(target)

        task_config = TaskConfig({"options": {"path": "dir1"}})
        task = util.Delete(self.project_config, task_config, self.org_config)
        task()

        assert not os.path.exists(target)

    def test_Delete__no_match(self):
        task_config = TaskConfig({"options": {"path": "bogus"}})
        task = util.Delete(self.project_config, task_config, self.org_config)
        task()

    @mock.patch("cumulusci.tasks.util.find_replace")
    def test_FindReplace(self, find_replace):
        task_config = TaskConfig({"options": {"find": "foo", "path": ".", "max": 1}})
        task = util.FindReplace(self.project_config, task_config, self.org_config)
        task()
        find_replace.assert_called_once()

    @mock.patch("cumulusci.tasks.util.find_replace")
    def test_FindReplace_env_replace_error(self, find_replace):
        with pytest.raises(TaskOptionsError):
            task_config = TaskConfig(
                {
                    "options": {
                        "find": "foo",
                        "replace": "bar",
                        "env_replace": True,
                        "path": ".",
                        "max": 1,
                    }
                }
            )
            task = util.FindReplace(self.project_config, task_config, self.org_config)
            task()
            find_replace.assert_called_once()

    @mock.patch("cumulusci.tasks.util.find_replace")
    def test_FindReplace_env_replace(self, find_replace):
        with mock.patch.dict(os.environ, {"bar": "bars"}):
            task_config = TaskConfig(
                {
                    "options": {
                        "find": "foo",
                        "replace": "bar",
                        "env_replace": True,
                        "path": ".",
                        "max": 1,
                    }
                }
            )
            task = util.FindReplace(self.project_config, task_config, self.org_config)
            task()
            assert task.options["replace"] == "bars"
            find_replace.assert_called_once()

    @mock.patch("cumulusci.tasks.util.find_replace_regex")
    def test_FindReplaceRegex(self, find_replace_regex):
        task_config = TaskConfig({"options": {"find": "foo", "path": "."}})
        task = util.FindReplaceRegex(self.project_config, task_config, self.org_config)
        task()
        find_replace_regex.assert_called_once()

    def test_CopyFile(self):
        src = os.path.join(self.tempdir, "src")
        with open(src, "w"):
            pass
        dest = os.path.join(self.tempdir, "dest")

        task_config = TaskConfig({"options": {"src": src, "dest": dest}})
        task = util.CopyFile(self.project_config, task_config, self.org_config)
        task()

        assert os.path.exists(dest)

    def test_LogLine(self):
        task_config = TaskConfig({"options": {"level": "debug", "line": "test"}})
        task = util.LogLine(self.project_config, task_config, self.org_config)
        task.logger = DummyLogger()
        task()
        output = task.logger.get_output()
        assert output == "Beginning task: LogLine\n\ntest"

    def test_PassOptionAsResult(self):
        task_config = TaskConfig({"options": {"result": "test"}})
        task = util.PassOptionAsResult(
            self.project_config, task_config, self.org_config
        )
        task()
        assert task.result == "test"

    def test_PassOptionAsReturnValue(self):
        task_config = TaskConfig({"options": {"key": "foo", "value": "bar"}})
        task = util.PassOptionAsReturnValue(
            self.project_config, task_config, self.org_config
        )
        result = task()
        assert result["foo"] == "bar"

    def test_injectLWCRemoteSiteSettingURL(self):
        with temporary_dir() as tmpdir:
            tmpdir = Path(tmpdir).resolve()
            tempfile = tmpdir / "remotSiteSetting.xml"
            with open(tempfile, "w+", encoding=("utf-8")) as file:
                file.write(OMNISTUDIO_LWC_XML)
                task_config = TaskConfig(
                    {"options": {"find": "${OmniStudioLightning}", "path": tmpdir}}
                )
                self.org_config = mock.MagicMock(
                    instance_url="https://test.my.salesforce.com",
                    name="test",
                    instance_name="CS100",
                )
                self.project_config.keychain = mock.MagicMock(api_version="42.0")
                task = util.InjectMetaDataValueLWC(
                    project_config=self.project_config,
                    task_config=task_config,
                    org_config=self.org_config,
                )
                preview = file
                preview.seek(0)
                preview = preview.read()
                assert preview == OMNISTUDIO_LWC_XML
                task()
                file.seek(0)
                final = file.read()
                assert final == final.replace(
                    ".my.salesforce.com", ".lightning.force.com"
                )
                file.close()

    def test_error_injectLWCRemoteSiteSettingURL(self):
        with temporary_dir() as tmpdir:
            tmpdir = Path(tmpdir).resolve()
            tempfile = tmpdir / "remotSiteSetting.xml"
            with open(tempfile, "w+", encoding=("utf-8")) as file:
                file.write(OMNISTUDIO_VISUALFORCE_XML)
                task_config = TaskConfig(
                    {
                        "options": {
                            "find": "${OmniStudioVisualforce}",
                        }
                    }
                )
                self.org_config = mock.MagicMock(
                    instance_url="https://test.my.salesforce.com",
                    name="test",
                    instance_name="CS100",
                )
                self.project_config.keychain = mock.MagicMock(api_version="42.0")
                with pytest.raises(
                    TaskOptionsError, match="Please check your options passed in."
                ):
                    util.InjectMetaDataValueLWC(
                        project_config=self.project_config,
                        task_config=task_config,
                        org_config=self.org_config,
                    )
                file.close()

    def test_injectVisualForceRemoteSiteSettingURL(self):
        with temporary_dir() as tmpdir:
            tmpdir = Path(tmpdir).resolve()
            tempfile = tmpdir / "remotSiteSetting.xml"
            with open(tempfile, "w+", encoding=("utf-8")) as file:
                file.write(OMNISTUDIO_VISUALFORCE_XML)
                task_config = TaskConfig(
                    {"options": {"find": "${OmniStudioVisualforce}", "path": tmpdir}}
                )
                self.org_config = mock.MagicMock(
                    instance_url="https://test.my.salesforce.com",
                    name="test",
                    instance_name="CS100",
                )
                self.project_config.keychain = mock.MagicMock(api_version="42.0")
                task = util.InjectMetaDataValueVisualForce(
                    project_config=self.project_config,
                    task_config=task_config,
                    org_config=self.org_config,
                )
                preview = file
                preview.seek(0)
                preview = preview.read()
                assert preview == OMNISTUDIO_VISUALFORCE_XML
                task()
                file.seek(0)
                final = file.read()
                assert final == final.replace(
                    ".my.salesforce.com",
                    f"--omnistudio.{self.org_config.instance_name}.visual.force.com",
                )
                file.close()

    def test_error_injectVisualForceRemoteSiteSettingURL(self):
        with temporary_dir() as tmpdir:
            tmpdir = Path(tmpdir).resolve()
            tempfile = tmpdir / "remotSiteSetting.xml"
            with open(tempfile, "w+", encoding=("utf-8")) as file:
                file.write(OMNISTUDIO_VISUALFORCE_XML)
                task_config = TaskConfig(
                    {
                        "options": {
                            "find": "${OmniStudioVisualforce}",
                        }
                    }
                )
                self.org_config = mock.MagicMock(
                    instance_url="https://test.my.salesforce.com",
                    name="test",
                    instance_name="CS100",
                )
                self.project_config.keychain = mock.MagicMock(api_version="42.0")
                with pytest.raises(
                    TaskOptionsError, match="Please check your options passed in."
                ):
                    util.InjectMetaDataValueVisualForce(
                        project_config=self.project_config,
                        task_config=task_config,
                        org_config=self.org_config,
                    )
                file.close()
