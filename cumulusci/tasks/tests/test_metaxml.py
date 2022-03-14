import os
from unittest import mock

from cumulusci.core.config import BaseProjectConfig, TaskConfig, UniversalConfig
from cumulusci.core.dependencies.dependencies import PackageNamespaceVersionDependency
from cumulusci.tasks.metaxml import UpdateApi, UpdateDependencies
from cumulusci.utils import temporary_dir


class TestUpdateApi:
    def test_run_task(self):
        with temporary_dir() as d:
            os.mkdir(".git")
            os.mkdir("src")
            meta_xml_path = os.path.join(d, "src", "test-meta.xml")
            with open(meta_xml_path, "w") as f:
                f.write(
                    """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>1.0</apiVersion>
</ApexClass>
"""
                )

            project_config = BaseProjectConfig(
                UniversalConfig(), config={"noyaml": True}
            )
            task_config = TaskConfig({"options": {"version": "43.0"}})
            task = UpdateApi(project_config, task_config)
            task()

            with open(meta_xml_path, "r") as f:
                result = f.read()
            assert (
                """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>43.0</apiVersion>
</ApexClass>
"""
                == result
            )


class TestUpdateDependencies:
    @mock.patch("cumulusci.tasks.metaxml.get_static_dependencies")
    def test_run_task(self, get_static_dependencies):
        get_static_dependencies.return_value = [
            PackageNamespaceVersionDependency(namespace="npe01", version="1.1"),
            PackageNamespaceVersionDependency(namespace="npsp", version="3.0"),
        ]

        with temporary_dir() as d:
            os.mkdir(".git")
            os.mkdir("src")
            meta_xml_path = os.path.join(d, "src", "test-meta.xml")
            with open(meta_xml_path, "w") as f:
                f.write(
                    """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <packageVersions>
        <namespace>npsp</namespace>
        <majorNumber>1</majorNumber>
        <minorNumber>0</minorNumber>
    </packageVersions>
    <packageVersions>
        <namespace>npe01</namespace>
        <majorNumber>1</majorNumber>
        <minorNumber>0</minorNumber>
    </packageVersions>
</ApexClass>
"""
                )

            project_config = BaseProjectConfig(
                UniversalConfig(), config={"noyaml": True}
            )
            task_config = TaskConfig()
            task = UpdateDependencies(project_config, task_config)
            task()

            with open(meta_xml_path, "r") as f:
                result = f.read()
            assert (
                """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <packageVersions>
        <namespace>npsp</namespace>
        <majorNumber>3</majorNumber>
        <minorNumber>0</minorNumber>
    </packageVersions>
    <packageVersions>
        <namespace>npe01</namespace>
        <majorNumber>1</majorNumber>
        <minorNumber>1</minorNumber>
    </packageVersions>
</ApexClass>
"""
                == result
            )
