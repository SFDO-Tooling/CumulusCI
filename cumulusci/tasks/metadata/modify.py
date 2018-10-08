import glob

import lxml.etree as ET

from cumulusci.core.tasks import BaseTask
from cumulusci.utils import cd
from cumulusci.utils import elementtree_parse_file


class RemoveElementsXPath(BaseTask):
    task_options = {
        "elements": {
            "description": "A list of dictionaries containing path and xpath keys. The path key is a file path that supports wildcards and xpath is the xpath for the elements to remove.  Multiple dictionaries can be passed in the list to run multiple removal queries in the same task.  Metadata elements in the xpath need to be prefixed with ns:, for example: ./ns:Layout/ns:relatedLists",
            "required": True,
        },
        "chdir": {
            "description": "Change the current directory before running the replace"
        },
    }

    def _run_task(self):
        chdir = self.options.get("chdir")
        if chdir:
            self.logger.info("Changing directory to {}".format(chdir))
        with cd(chdir):
            for element in self.options["elements"]:
                self._process_element(element)

    def _process_element(self, element):
        self.logger.info(
            "Removing elements matching {xpath} from {path}".format(**element)
        )
        for f in glob.glob(element["path"]):
            with open(f, "rb") as fp:
                orig = fp.read()
            root = ET.parse(f)
            res = root.findall(
                element["xpath"].replace(
                    "ns:", "{http://soap.sforce.com/2006/04/metadata}"
                )
            )
            for element in res:
                element.getparent().remove(element)
            processed = (
                b'<?xml version="1.0" encoding="UTF-8"?>\n'
                + ET.tostring(root, encoding="utf-8")
                + b"\n"
            )
            if orig != processed:
                self.logger.info("Modified {}".format(f))
                with open(f, "wb") as fp:
                    fp.write(processed)
