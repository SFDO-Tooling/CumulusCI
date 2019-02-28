import os
import os.path
import time
import jinja2
import robot.utils

import cumulusci
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_list_arg

from robot.libdocpkg import DocumentationBuilder
from robot.libraries.BuiltIn import RobotNotRunningError


class RobotLibDoc(BaseTask):
    task_options = {
        "path": {
            "description": "The path to the robot library to be documented.  Can be single a python file or a .robot file, or a comma separated list of those files. The order of the files will be preserved in the generated documentation.",
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

        self.options["path"] = process_list_arg(self.options["path"])

        bad_files = []
        for input_file in self.options["path"]:
            if not os.path.exists(input_file):
                bad_files.append(input_file)

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

    def _run_task(self):
        libraries = []
        processed_files = {}
        for input_file in self.options["path"]:
            try:
                libdoc = DocumentationBuilder(input_file).build(input_file)
                libraries.append(libdoc)
                processed_files[input_file] = libdoc

                # robot doesn't save the orginal name but we want to use that
                # in our generated file
                libdoc.src = os.path.basename(input_file)

                # if we want to save the official libdoc file, uncomment the following
                # two lines:
                # libdoc.save(self.options['output_file'], "HTML")
                # self.logger.info("created {}".format(output_file))

            except RobotNotRunningError as e:
                # oddly, robot's exception has a traceback embedded in the message, so we'll
                # only print out the first line to hide most of the noise
                self.logger.warn("unexpected error: {}".format(str(e).split("\n")[0]))

        with open(self.options["output"], "w") as f:
            html = self._render_html(libraries)
            f.write(html)
            self.logger.info("created {}".format(f.name))

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
