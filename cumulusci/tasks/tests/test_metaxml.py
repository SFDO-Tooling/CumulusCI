from unittest import mock
import os
import unittest

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.tasks.metaxml import UpdateApi
from cumulusci.tasks.metaxml import UpdateDependencies
from cumulusci.utils import temporary_dir


class TestUpdateApi(unittest.TestCase):
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
                BaseGlobalConfig(), config={"noyaml": True}
            )
            task_config = TaskConfig({"options": {"version": "43.0"}})
            task = UpdateApi(project_config, task_config)
            task()

            with open(meta_xml_path, "r") as f:
                result = f.read()
            self.assertEqual(
                """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>43.0</apiVersion>
</ApexClass>
""",
                result,
            )


class TestUpdateDependencies(unittest.TestCase):
    def test_run_task(self):
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
                BaseGlobalConfig(), config={"noyaml": True}
            )
            project_config.get_static_dependencies = mock.Mock(
                return_value=[
                    {
                        "namespace": "npsp",
                        "version": "3.0",
                        "dependencies": [{"namespace": "npe01", "version": "1.1"}],
                    }
                ]
            )
            task_config = TaskConfig()
            task = UpdateDependencies(project_config, task_config)
            task()

            with open(meta_xml_path, "r") as f:
                result = f.read()
            self.assertEqual(
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
""",
                result,
            )
