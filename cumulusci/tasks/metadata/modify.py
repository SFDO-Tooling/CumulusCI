import glob

import lxml.etree as ET

from cumulusci.core.tasks import BaseTask
from cumulusci.utils import cd
from cumulusci.utils.xml import (
    elementtree_parse_file,
    serialize_sf_style,
    XML_ENCODING_DECL,
)


class RemoveElementsXPath(BaseTask):
    """Remove elements based on an XPath."""

    task_options = {
        "elements": {
            "description": (
                "A list of dictionaries containing path and xpath "
                "keys. The path key is a file path that supports "
                "wildcards and xpath is the xpath for the elements "
                "to remove.  Multiple dictionaries can be passed in "
                "the list to run multiple removal queries in the same "
                "task.  Metadata elements in the xpath need to be prefixed "
                "with ns:, for example: ./ns:Layout/ns:relatedLists"
            ),
            "required": True,
        },
        "chdir": {
            "description": "Change the current directory before running the replace"
        },
        "output_style": {
            "description": "Output style to use: 'salesforce' or 'simple'",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.chdir = self.options.get("chdir")
        self.elements = self.options["elements"]
        self.output_style = self.options.get("output_style", "")

    def _run_task(self):
        if self.chdir:
            self.logger.info("Changing directory to {}".format(self.chdir))
        with cd(self.chdir):
            for element in self.elements:
                self._process_element(element, self.output_style)

    def _process_element(self, step, output_style):
        self.logger.info(
            "Removing elements matching {xpath} from {path}".format(**step)
        )
        for f in glob.glob(step["path"], recursive=True):
            self.logger.info(f"Checking {f}")
            with open(f, "rb") as fp:
                orig = fp.read()
            root = elementtree_parse_file(f)
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

            if output_style.lower() == "salesforce":
                processed = bytes(serialize_sf_style(root), "utf-8")
            else:
                processed = (
                    bytes(XML_ENCODING_DECL, encoding="utf-8")
                    + ET.tostring(root, encoding="utf-8")
                    + b"\n"
                )

            if orig != processed:
                self.logger.info("Modified {}".format(f))
                with open(f, "wb") as fp:
                    fp.write(processed)
