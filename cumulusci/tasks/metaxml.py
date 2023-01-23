import fileinput
import os
import re
import sys

from cumulusci.core.dependencies.dependencies import PackageNamespaceVersionDependency
from cumulusci.core.dependencies.resolvers import get_static_dependencies
from cumulusci.core.tasks import BaseTask
from cumulusci.utils.xml import lxml_parse_file


class MetaXmlBaseTask(BaseTask):
    def _init_options(self, kwargs):
        super(MetaXmlBaseTask, self)._init_options(kwargs)
        if "dir" not in self.options or not self.options["dir"]:
            self.options["dir"] = os.path.join(self.project_config.repo_root, "src")

    def _run_task(self):
        for root, dirs, files in os.walk(self.options["dir"]):
            for filename in files:
                filename = os.path.join(root, filename)
                if filename.endswith("-meta.xml"):
                    tree = lxml_parse_file(filename)
                    if self._process_xml(tree.getroot()):
                        self._write_file(tree, filename)
                        self.logger.info("Processed file %s", filename)

    def _write_file(self, tree, filename):
        tree.write(filename, xml_declaration=True, encoding="UTF-8", pretty_print=True)
        # change back to double quotes in header to minimize diffs
        for line in fileinput.input(filename, inplace=1):
            if line.startswith("<?xml"):
                sys.stdout.write(line.replace("'", '"'))
            else:
                sys.stdout.write(line)


class UpdateApi(MetaXmlBaseTask):
    task_options = {
        "dir": {"description": "Base directory to search for ``*-meta.xml`` files"},
        "version": {"description": "API version number e.g. 37.0", "required": True},
    }

    def _process_xml(self, root):
        changed = False
        xmlns = re.search("({.+}).+", root.tag).group(1)
        api_version = root.find("{}apiVersion".format(xmlns))
        if api_version is not None and api_version.text != self.options["version"]:
            api_version.text = self.options["version"]
            changed = True
        return changed


class UpdateDependencies(MetaXmlBaseTask):
    task_options = {
        "dir": {"description": "Base directory to search for ``*-meta.xml`` files"}
    }

    def _init_task(self):
        self.dependencies = []
        dependencies = get_static_dependencies(
            self.project_config,
            resolution_strategy="production",
        )
        self._process_dependencies(dependencies)

    def _process_dependencies(self, dependencies):
        for dependency in dependencies:
            if isinstance(dependency, PackageNamespaceVersionDependency):
                self.dependencies.append((dependency.namespace, dependency.version))

    def _process_xml(self, root):
        changed = False
        xmlns = re.search("({.+}).+", root.tag).group(1)
        for namespace, version in self.dependencies:
            v_major, v_minor = version.split(".")
            for package_version in root.findall("{}packageVersions".format(xmlns)):
                if package_version.find("{}namespace".format(xmlns)).text != namespace:
                    continue
                major = package_version.find("{}majorNumber".format(xmlns))
                if major.text != v_major:
                    major.text = v_major
                    changed = True
                minor = package_version.find("{}minorNumber".format(xmlns))
                if minor.text != v_minor:
                    minor.text = v_minor
                    changed = True
        return changed
