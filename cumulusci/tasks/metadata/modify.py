import glob

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseTask
from cumulusci.utils import cd
from cumulusci.utils.xml import lxml_parse_file
from cumulusci.utils.xml.salesforce_encoding import serialize_xml_for_salesforce

SF_NS = "http://soap.sforce.com/2006/04/metadata"


class RemoveElementsXPath(BaseTask):
    """Remove elements based on an XPath."""

    task_options = {
        "xpath": {
            "description": (
                "An XPath specification of elements to remove. Supports the re: "
                "regexp function namespace. As in re:match(text(), '.*__c')"
                "Use ns: to refer to the Salesforce namespace for metadata elements."
                "for example: ./ns:Layout/ns:relatedLists (one-level) or //ns:relatedLists (recursive)"
                "Many advanced examples are available here: "
                "https://github.com/SalesforceFoundation/NPSP/blob/26b585409720e2004f5b7785a56e57498796619f/cumulusci.yml#L342"
            )
        },
        "path": {
            "description": (
                "A path to the files to change. Supports wildcards including ** for directory recursion. "
                "More info on the details: "
                "https://www.poftut.com/python-glob-function-to-match-path-directory-file-names-with-examples/ "
                "https://www.tutorialspoint.com/How-to-use-Glob-function-to-find-files-recursively-in-Python "
            )
        },
        "elements": {
            "description": (
                "A list of dictionaries containing path and xpath "
                "keys. Multiple dictionaries can be passed in "
                "the list to run multiple removal queries in the same "
                "task. This parameter is intended for usages invoked as part "
                "of a cumulusci.yml ."
            )
        },
        "chdir": {
            "description": "Change the current directory before running the replace"
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.chdir = self.options.get("chdir")
        self.elements = self.options.get("elements")
        xpath = self.options.get("xpath")
        path = self.options.get("path")
        if xpath and not path:
            raise TaskOptionsError("Specified XPath without `path` to work on.")
        elif path and not xpath:
            raise TaskOptionsError("Specified path without `xpath` to apply.")
        elif (path and self.elements) or (not self.elements and not path):
            raise TaskOptionsError(
                "Please specify either a single `path` and `xpath` (in CLI or cumulusci.yml) "
                "or a list of several through the `elements` option (cumulusci.yml)."
            )

        if not self.elements:
            self.elements = [{"xpath": xpath, "path": path}]

    def _run_task(self):
        if self.chdir:
            self.logger.info("Changing directory to {}".format(self.chdir))
        with cd(self.chdir):
            for element in self.elements:
                self._process_element(element)

    def _process_element(self, step):
        self.logger.info(
            "Removing elements matching {xpath} from {path}".format(**step)
        )
        for f in glob.glob(step["path"], recursive=True):
            self.logger.info(f"Checking {f}")
            with open(f, "rb") as fp:
                orig = fp.read()
            root = lxml_parse_file(f)
            res = root.xpath(
                step["xpath"],
                namespaces={
                    "ns": "http://soap.sforce.com/2006/04/metadata",
                    "re": "http://exslt.org/regular-expressions",
                },
            )
            self.logger.info(f"Found {len(res)} matching elements")
            for element in res:
                element.getparent().remove(element)

            processed = serialize_xml_for_salesforce(root, xml_declaration=True)

            if orig != processed:
                self.logger.info("Modified {}".format(f))
                with open(f, "w", encoding="utf-8") as fp:
                    fp.write(processed)
