import csv
import os
import os.path
import re
import time
from pathlib import Path

import jinja2
import robot.utils
from robot.libdocpkg.builder import DocumentationBuilder
from robot.libdocpkg.robotbuilder import LibraryDocBuilder, ResourceDocBuilder
from robot.libraries.BuiltIn import RobotNotRunningError
from robot.utils import Importer

import cumulusci
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_bool_arg, process_glob_list_arg
from cumulusci.robotframework import PageObjects
from cumulusci.utils.fileutils import view_file


class RobotLibDoc(BaseTask):
    task_options = {
        "path": {
            "description": (
                "The path to one or more keyword libraries to be documented. "
                "The path can be single a python file, a .robot file, a python "
                "module (eg: cumulusci.robotframework.Salesforce) or a comma "
                "separated list of any of those. Glob patterns are supported "
                "for filenames (eg: ``robot/SAL/doc/*PageObject.py``). The order "
                "of the files will be preserved in the generated documentation. "
                "The result of pattern expansion will be sorted"
            ),
            "required": True,
        },
        "output": {
            "description": (
                "The output file where the documentation will be written. "
                "Normally an HTML file will be generated. If the filename "
                "ends with '.csv' then a csv file will be generated instead."
            ),
            "required": True,
        },
        "title": {
            "description": "A string to use as the title of the generated output",
            "required": False,
        },
        "preview": {
            "description": (
                "If True, automatically open a window to view the "
                "generated data when the task is successful"
            ),
            "required": False,
        },
    }

    def _validate_options(self):
        super(RobotLibDoc, self)._validate_options()
        self.options["path"] = process_glob_list_arg(self.options["path"])

        # Attempt to collect all files that don't match existing
        # files. Note: "path" could be a library module path (for example,
        # cumulusci.robotframework.CumulusCI) so we only do this check for
        # files that end in known library suffixes (.py, .robot, .resource).
        bad_files = []
        for path in self.options["path"]:
            name, extension = os.path.splitext(path)
            if extension in (".py", ".robot", ".resource") and not os.path.exists(path):
                bad_files.append(path)

        if bad_files:
            if len(bad_files) == 1:
                error_message = "Unable to find the input file '{}'".format(
                    bad_files[0]
                )
            else:
                files = ", ".join(["'{}'".format(filename) for filename in bad_files])
                error_message = "Unable to find the following input files: {}".format(
                    files
                )
            raise TaskOptionsError(error_message)

        self.options["preview"] = process_bool_arg(self.options.get("preview", False))

    def is_pageobject_library(self, path):
        """Return True if the file looks like a page object library"""
        if path.endswith(".py"):
            with open(path, "r") as f:
                data = f.read()
                if re.search(r"@pageobject\(", data):
                    return True
        return False

    def _run_task(self):
        kwfiles = []
        processed_files = []
        for library_name in self.options["path"]:
            kwfile = KeywordFile(library_name)
            try:
                if self.is_pageobject_library(library_name):
                    PageObjects._reset()
                    module = Importer().import_class_or_module_by_path(
                        os.path.abspath(library_name)
                    )
                    kwfile.doc = module.__doc__
                    if hasattr(module, "TITLE"):
                        kwfile.title = module.TITLE

                    for pobj_name, pobj in sorted(PageObjects.registry.items()):
                        pobj = PageObjects.registry[pobj_name]
                        libname = "{}.{}".format(pobj.__module__, pobj.__name__)
                        libdoc = LibraryDocBuilder().build(libname)
                        libdoc.src = os.path.basename(library_name)
                        libdoc.pobj = libname
                        kwfile.add_keywords(libdoc, pobj_name)

                else:
                    # this test necessary due to a backwards-incompatible change
                    # in robot 6.x where .robot files get unconditionally passed
                    # to SuiteBuilder which then generates an error on keyword
                    # files since they don't have test cases.
                    if library_name.endswith(".robot"):
                        libdoc = ResourceDocBuilder().build(library_name)
                    else:
                        libdoc = DocumentationBuilder().build(library_name)
                    kwfile.add_keywords(libdoc)

                # if we get here, we were able to process the file correctly
                kwfiles.append(kwfile)
                processed_files.append(library_name)

            except RobotNotRunningError as e:
                # oddly, robot's exception has a traceback embedded in the message, so we'll
                # only print out the first line to hide most of the noise
                self.logger.warning(
                    "unexpected error: {}".format(str(e).split("\n")[0])
                )

        try:
            if self.options["output"].endswith(".csv"):
                data = self._convert_to_tuples(kwfiles)
                with open(self.options["output"], "w", newline="") as f:
                    csv_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                    csv_writer.writerows(data)

            else:
                html = self._convert_to_html(kwfiles)
                with open(self.options["output"], "w") as f:
                    f.write(html)
            self.logger.info("created {}".format(self.options["output"]))

            if self.options["preview"]:
                view_file(self.options["output"])

        except Exception as e:
            raise TaskOptionsError(
                "Unable to create output file '{}' ({})".format(
                    self.options["output"], str(e)
                )
            )

        return {"files": processed_files}

    def _convert_to_tuples(self, kwfiles):
        """Convert the list of keyword files into a list of tuples

        The first element in the list will be a list of column headings.
        """
        rows = []
        for kwfile in kwfiles:
            rows.extend(kwfile.to_tuples())
        rows = sorted(set(rows))
        rows.insert(0, KeywordFile.get_header())
        return rows

    def _convert_to_html(self, kwfiles):
        """Convert the list of keyword files into html"""

        title = self.options.get("title", "Keyword Documentation")
        date = time.strftime("%A %B %d, %I:%M %p")
        cci_version = cumulusci.__version__

        stylesheet_path = os.path.join(os.path.dirname(__file__), "stylesheet.css")
        with open(stylesheet_path) as f:
            stylesheet = f.read()

        jinjaenv = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(__file__)), autoescape=False
        )
        jinjaenv.filters["robot_html"] = robot.utils.html_format
        template = jinjaenv.get_template("template.html")
        return template.render(
            libraries=kwfiles,
            title=title,
            cci_version=cci_version,
            stylesheet=stylesheet,
            date=date,
        )


class KeywordFile:
    """Helper class which represents a file and its keywords

    A file may have just a bunch of keywords, or groups of
    keywords organized as page objects. Each group of keywords
    is stored in self.keywords, with the page object metadata
    as a key.

    For normal libraries, the key is an empty tuple.
    """

    def __init__(self, path):
        if os.path.exists(path):
            self.filename = os.path.basename(path)
        else:
            # if it's not a file, it must be a module
            self.filename = path.split(".")[-1]
        self.title = self.filename
        self.path = path
        self.keywords = {}

    @classmethod
    def get_header(cls):
        return ["Name", "Source", "Line#", "po type", "po_object", "Documentation"]

    def add_keywords(self, libdoc, page_object=tuple()):
        self.keywords[page_object] = libdoc

    def to_tuples(self):
        """Convert the dictionary of keyword data to a set of tuples"""
        rows = []
        cwd = Path.cwd()
        base_pageobjects_path = os.path.join(
            "cumulusci", "robotframework", "pageobjects"
        )

        for po, libdoc in self.keywords.items():
            (po_type, po_object) = po if po else ("", "")
            for keyword in libdoc.keywords:
                # we don't want to see the same base pageobject
                # keywords a kajillion times. This should probably
                # be configurable, but I don't need it to be right now.
                if base_pageobjects_path in str(keyword.source):
                    continue

                path = Path(keyword.source)
                if path.is_absolute():
                    try:
                        path = path.relative_to(cwd)
                    except ValueError:
                        # ok, fine. We'll use the path as-is.
                        pass
                path = str(path)

                # make sure that if you change the list of columns here
                # that you modify the `get_header` property too!
                row = (
                    keyword.name,
                    path,
                    keyword.lineno,
                    po_type,
                    po_object,
                    keyword.doc,
                )
                rows.append(row)

        rows = set(rows)
        return rows
