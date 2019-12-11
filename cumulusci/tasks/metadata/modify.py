import glob
from xml.sax.saxutils import escape

import lxml.etree as ET

from cumulusci.core.tasks import BaseTask
from cumulusci.utils import cd


xml_encoding = '<?xml version="1.0" encoding="UTF-8"?>\n'
SF_NS = "http://soap.sforce.com/2006/04/metadata"


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
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.chdir = self.options.get("chdir")
        self.elements = self.options["elements"]

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
            root = ET.parse(f)
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

            processed = bytes(salesforce_encoding(root), "utf-8")

            if orig != processed:
                self.logger.info("Modified {}".format(f))
                with open(f, "wb") as fp:
                    fp.write(processed)


def has_content(element):
    return element.text or list(element)


def salesforce_encoding(xdoc):
    r = xml_encoding
    if SF_NS in xdoc.getroot().tag:
        xdoc.getroot().attrib["xmlns"] = SF_NS
    for action, elem in ET.iterwalk(
        xdoc, events=("start", "end", "start-ns", "end-ns", "comment")
    ):
        if action == "start-ns":
            pass  # handle this nicely if SF starts using multiple namespaces
        elif action == "start":
            tag = elem.tag
            if "}" in tag:
                tag = tag.split("}")[1]
            text = (
                escape(elem.text, {"'": "&apos;", '"': "&quot;"})
                if elem.text is not None
                else ""
            )

            attrs = "".join([f' {k}="{v}"' for k, v in elem.attrib.items()])
            if not has_content(elem):
                r += f"<{tag}{attrs}/>"
            else:
                r += f"<{tag}{attrs}>{text}"
        elif action == "end" and has_content(elem):
            tag = elem.tag
            if "}" in tag:
                tag = tag.split("}")[1]
            tail = elem.tail if elem.tail else "\n"
            r += f"</{tag}>{tail}"
        elif action == "comment":
            r += str(elem) + (elem.tail if elem.tail else "")
    return r
