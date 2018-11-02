import mock
import re
import unittest

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import OrgConfig
from cumulusci.tasks.apexdoc import GenerateApexDocs


class TestGenerateApexDocs(unittest.TestCase):
    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(
            self.global_config, config={"noyaml": True}
        )
        self.task_config = TaskConfig({"options": {"version": "1.0"}})
        self.org_config = OrgConfig({}, "test")

    def test_task(self):
        task = GenerateApexDocs(self.project_config, self.task_config, self.org_config)
        task._run_command = mock.Mock()
        task()
        self.assertTrue(
            re.match(
                r"java -jar .*.apexdoc.jar -s .*.src.classes -t .*",
                task.options["command"],
            )
        )
