import mock
import os
import unittest

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata.modify import RemoveElementsXPath
from cumulusci.utils import temporary_dir


class TestRemoveElementsXPath(unittest.TestCase):
    def test_run_task(self):
        with temporary_dir() as path:
            xml_path = os.path.join(path, "test.xml")
            with open(xml_path, "w") as f:
                f.write("<root><todelete /></root>")

            project_config = BaseProjectConfig(
                BaseGlobalConfig(), config={"noyaml": True}
            )
            task_config = TaskConfig(
                {
                    "options": {
                        "elements": [{"path": "test.xml", "xpath": "./todelete"}],
                        "chdir": path,
                    }
                }
            )
            task = RemoveElementsXPath(project_config, task_config)
            task()
            with open(xml_path, "r") as f:
                result = f.read()
            self.assertEqual(
                '<?xml version="1.0" encoding="UTF-8"?>\n<root/>\n', result
            )
