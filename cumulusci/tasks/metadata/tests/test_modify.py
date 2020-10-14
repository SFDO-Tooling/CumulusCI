import os
import unittest
from cumulusci.core.config import UniversalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.tasks.metadata.modify import RemoveElementsXPath
from cumulusci.utils import temporary_dir
from cumulusci.core.exceptions import TaskOptionsError


class TestRemoveElementsXPath(unittest.TestCase):
    def _run_task(self, options):
        project_config = BaseProjectConfig(UniversalConfig(), config={"noyaml": True})
        task_config = TaskConfig({"options": options})
        task = RemoveElementsXPath(project_config, task_config)
        task()

    def _run_xml_through_task(self, xml, options):
        with temporary_dir() as path:
            xml_path = os.path.join(path, "test.xml")
            with open(xml_path, "w") as f:
                f.write(xml)
            self._run_task({**options, "chdir": path})
            with open(xml_path, "r") as f:
                result = f.read()
            return result

    def test_cli_errors(self):
        with self.assertRaises(TaskOptionsError):
            self._run_task({})
        with self.assertRaises(TaskOptionsError):
            self._run_task({"path": "foo"})
        with self.assertRaises(TaskOptionsError):
            self._run_task({"xpath": "foo"})
        with self.assertRaises(TaskOptionsError):
            self._run_task(
                {
                    "XPath": "foo",
                    "path": "foo",
                    "elements": [{"xpath": "a", "path": "bar"}],
                }
            )

    def test_cli(self):
        result = self._run_xml_through_task(
            xml="<root>a<todelete/></root>",
            options={"xpath": "todelete", "path": "test.xml"},
        )
        self.assertEqual(
            '<?xml version="1.0" encoding="UTF-8"?>\n<root>a</root>\n', result
        )

    def test_run_task(self):
        result = self._run_xml_through_task(
            "<root>a<todelete/></root>",
            {"elements": [{"path": "test.xml", "xpath": "./todelete"}]},
        )
        self.assertEqual(
            '<?xml version="1.0" encoding="UTF-8"?>\n<root>a</root>\n', result
        )

    def test_salesforce_encoding(self):
        result = self._run_xml_through_task(
            """<root  xmlns="http://soap.sforce.com/2006/04/metadata"><todelete /><a>"'</a></root>""",
            {
                "elements": [{"path": "test.xml", "xpath": "ns:todelete"}],
                "output_style": "salesforce",
            },
        )
        self.assertEqual(
            '<?xml version="1.0" encoding="UTF-8"?>\n<root xmlns="http://soap.sforce.com/2006/04/metadata"><a>&quot;&apos;</a>\n</root>\n',
            result,
        )

    def test_namespaces_ns(self):
        result = self._run_xml_through_task(
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
        result = self._run_xml_through_task(
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
        result = self._run_xml_through_task(
            """<root><a><!-- Foo --></a><todelete></todelete></root>""",
            {
                "elements": [{"path": "test.xml", "xpath": "todelete"}],
                "output_style": "salesforce",
            },
        )
        self.assertEqual(
            '<?xml version="1.0" encoding="UTF-8"?>\n<root><a><!-- Foo --></a>\n</root>\n',
            result,
        )

    def test_empty_element(self):
        result = self._run_xml_through_task(
            """<root><a/></root>""",
            {
                "elements": [{"path": "test.xml", "xpath": "todelete"}],
                "output_style": "salesforce",
            },
        )
        self.assertEqual(
            '<?xml version="1.0" encoding="UTF-8"?>\n<root><a/>\n</root>\n', result
        )
