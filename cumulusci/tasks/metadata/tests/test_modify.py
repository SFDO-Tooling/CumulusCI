import os
import unittest

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.tasks.metadata.modify import RemoveElementsXPath
from cumulusci.utils import temporary_dir


class TestRemoveElementsXPath(unittest.TestCase):
    def run_xml_through_task(self, xml, options):
        with temporary_dir() as path:
            xml_path = os.path.join(path, "test.xml")
            with open(xml_path, "w") as f:
                f.write(xml)

            project_config = BaseProjectConfig(
                BaseGlobalConfig(), config={"noyaml": True}
            )
            task_config = TaskConfig({"options": {**options, "chdir": path}})
            task = RemoveElementsXPath(project_config, task_config)
            task()
            with open(xml_path, "r") as f:
                result = f.read()
            return result

    def test_run_task(self):
        result = self.run_xml_through_task(
            "<root><todelete/></root>",
            {"elements": [{"path": "test.xml", "xpath": "./todelete"}]},
        )
        self.assertEqual('<?xml version="1.0" encoding="UTF-8"?>\n<root/>\n', result)

    def test_salesforce_encoding(self):
        result = self.run_xml_through_task(
            """<root><todelete /><a>"'</a></root>""",
            {
                "elements": [{"path": "test.xml", "xpath": "todelete"}],
                "output_style": "salesforce",
            },
        )
        self.assertEqual(
            '<?xml version="1.0" encoding="UTF-8"?>\n<root xmlns="http://soap.sforce.com/2006/04/metadata"><a>&quot;&apos;</a>\n</root>\n',
            result,
        )

    def test_namespaces_ns(self):
        result = self.run_xml_through_task(
            """<root xmlns="http://soap.sforce.com/2006/04/metadata"><todelete /><a>"'</a></root>""",
            {
                "elements": [{"path": "test.xml", "xpath": "ns:todelete"}],
                "output_style": "salesforce",
            },
        )
        self.assertEqual(
            '<?xml version="1.0" encoding="UTF-8"?>\n<root xmlns="http://soap.sforce.com/2006/04/metadata"><a>&quot;&apos;</a>\n</root>\n',
            result,
        )

    def test_regular_expressions(self):
        result = self.run_xml_through_task(
            """<root xmlns="http://soap.sforce.com/2006/04/metadata"><todelete>baz</todelete><todelete>bar</todelete></root>""",
            {
                "elements": [
                    {
                        "path": "test.xml",
                        "xpath": "ns:todelete[re:match('bar', text())]",
                    }
                ],
                "output_style": "salesforce",
            },
        )
        self.assertEqual(
            '<?xml version="1.0" encoding="UTF-8"?>\n<root xmlns="http://soap.sforce.com/2006/04/metadata"><todelete>baz</todelete>\n</root>\n',
            result,
        )

    def test_comment(self):
        result = self.run_xml_through_task(
            """<root><a><!-- Foo --></a><todelete></todelete></root>""",
            {
                "elements": [{"path": "test.xml", "xpath": "todelete"}],
                "output_style": "salesforce",
            },
        )
        self.assertEqual(
            '<?xml version="1.0" encoding="UTF-8"?>\n<root xmlns="http://soap.sforce.com/2006/04/metadata"><a><!-- Foo --></a>\n</root>\n',
            result,
        )
