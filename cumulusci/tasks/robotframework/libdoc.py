import os
import os.path
import re
import time
import jinja2
import robot.utils

import cumulusci
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_glob_list_arg
from cumulusci.robotframework import PageObjects

from robot.libdocpkg import DocumentationBuilder
from robot.libraries.BuiltIn import RobotNotRunningError
from robot.libdocpkg.robotbuilder import LibraryDocBuilder
from robot.utils import Importer


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
            "description": "The output file where the documentation will be written",
            "required": True,
        },
        "title": {
            "description": "A string to use as the title of the generated output",
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
                    libdoc = DocumentationBuilder(library_name).build(library_name)
                    kwfile.add_keywords(libdoc)

                # if we get here, we were able to process the file correctly
                kwfiles.append(kwfile)
                processed_files.append(library_name)

            except RobotNotRunningError as e:
                # oddly, robot's exception has a traceback embedded in the message, so we'll
                # only print out the first line to hide most of the noise
                self.logger.warn("unexpected error: {}".format(str(e).split("\n")[0]))

        try:
            with open(self.options["output"], "w") as f:
                html = self._render_html(kwfiles)
                f.write(html)
                self.logger.info("created {}".format(f.name))
        except Exception as e:
            raise TaskOptionsError(
                "Unable to create output file '{}' ({})".format(
                    self.options["output"], e.strerror
                )
            )

        return {"files": processed_files, "html": html}

    def _render_html(self, libraries):
        """Generate the html. `libraries` is a list of LibraryDocumentation objects"""

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
            libraries=libraries,
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

    def add_keywords(self, libdoc, page_object=tuple()):
        self.keywords[page_object] = libdoc
