import os
import re
import shutil
import urllib.parse
from logging import Logger, getLogger
from pathlib import Path

import yaml

from cumulusci.core.tasks import BaseTask
from cumulusci.utils import elementtree_parse_file
from cumulusci.utils.xml import metadata_tree

__location__ = os.path.dirname(os.path.realpath(__file__))


def metadata_sort_key(name):
    sections = []
    for section in re.split("[.|-]", name):
        sections.append(metadata_sort_key_section(section))

    key = "_".join(sections)
    key = key.replace("_", "Z")

    return key


def metadata_sort_key_section(name):
    prefix = "5"
    key = name

    # Sort namespace prefixed names last
    base_name = name
    if base_name.endswith("__c"):
        base_name = base_name[:-3]
    if "__" in base_name:
        prefix = "8"

    key = prefix + name
    return key


class MetadataParserMissingError(Exception):
    pass


class PackageXmlGenerator(object):
    def __init__(
        self,
        directory,
        api_version,
        package_name=None,
        managed=None,
        delete=None,
        install_class=None,
        uninstall_class=None,
        types=None,
        logger=None,
    ):
        with open(
            __location__ + "/metadata_map.yml", "r", encoding="utf-8"
        ) as f_metadata_map:
            self.metadata_map = yaml.safe_load(f_metadata_map)
        self.directory = directory
        self.api_version = api_version
        self.package_name = package_name
        self.managed = managed
        self.delete = delete
        self.install_class = install_class
        self.uninstall_class = uninstall_class
        self.types = types or []
        self.logger = logger

    def __call__(self):
        if not self.types:
            self.parse_types()
        return self.render_xml()

    def parse_types(self):
        for item in sorted(os.listdir(self.directory)):
            if item == "package.xml":
                continue
            if not os.path.isdir(self.directory + "/" + item):
                continue
            if item.startswith("."):
                continue
            config = self.metadata_map.get(item)
            if not config:
                raise MetadataParserMissingError(
                    "No parser configuration found for subdirectory %s" % item
                )

            for parser_config in config:
                options = parser_config.get("options") or {}
                parser = globals()[parser_config["class"]](
                    parser_config["type"],  # Metadata Type
                    self.directory + "/" + item,  # Directory
                    parser_config.get("extension", ""),  # Extension
                    self.delete,  # Parse for deletion?
                    self.logger,  # Logger
                    **options,  # Extra kwargs
                )
                self.types.append(parser)

    def render_xml(self):
        lines = []

        # Print header
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append('<Package xmlns="http://soap.sforce.com/2006/04/metadata">')
        if self.package_name:
            package_name_encoded = urllib.parse.quote(self.package_name, safe=" ")
            lines.append("    <fullName>{0}</fullName>".format(package_name_encoded))

        if self.managed and self.install_class:
            lines.append(
                "    <postInstallClass>{0}</postInstallClass>".format(
                    self.install_class
                )
            )

        if self.managed and self.uninstall_class:
            lines.append(
                "    <uninstallClass>{0}</uninstallClass>".format(self.uninstall_class)
            )

        # Print types sections
        self.types.sort(key=lambda x: x.metadata_type.upper())
        for parser in self.types:
            type_xml = parser()
            if type_xml:
                lines.extend(type_xml)

        # Print footer
        lines.append("    <version>{0}</version>".format(self.api_version))
        lines.append("</Package>")

        return "\n".join(lines)


class BaseMetadataParser(object):
    def __init__(self, metadata_type, directory, extension, delete, logger=None):
        self.metadata_type = metadata_type
        self.directory = directory
        self.extension = extension
        self.delete = delete
        self.members = []
        self.logger: Logger = logger or getLogger(__file__)

        if self.delete:
            self.delete_excludes = self.get_delete_excludes()

    def __call__(self):
        self.parse_items()
        return self.render_xml()

    def get_delete_excludes(self):
        filename = os.path.join(
            __location__, "..", "..", "files", "delete_excludes.txt"
        )
        excludes = []
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                excludes.append(line.strip())
        return excludes

    def parse_items(self):
        # Loop through items
        for item in sorted(os.listdir(self.directory)):
            # on Macs this file is generated by the OS. Shouldn't be in the package.xml
            if item.startswith("."):
                continue

            # Ignore the CODEOWNERS file which is special to Github
            if item in ["CODEOWNERS", "OWNERS"]:
                continue

            if item.endswith("-meta.xml"):
                continue

            if self.extension and not item.endswith("." + self.extension):
                continue

            if self.check_delete_excludes(item):
                continue

            self.parse_item(item)

    def check_delete_excludes(self, item):
        if not self.delete:
            return False
        if item in self.delete_excludes:
            return True
        return False

    def parse_item(self, item):
        members = self._parse_item(item)
        if members:
            for member in members:
                # Translate filename namespace tokens into in-file namespace tokens
                member = member.replace("___NAMESPACE___", "%%%NAMESPACE%%%")
                self.members.append(member)

    def _parse_item(self, item):
        "Receives a file or directory name and returns a list of members"
        raise NotImplementedError("Subclasses should implement their parser here")

    def strip_extension(self, filename):
        return filename.rsplit(".", 1)[0]

    def render_xml(self):
        output = []
        if not self.members:
            return
        output.append("    <types>")
        self.members.sort(key=metadata_sort_key)
        for member in self.members:
            if isinstance(member, bytes):
                member = member.decode("utf-8")
            output.append("        <members>{0}</members>".format(member))
        output.append("        <name>{0}</name>".format(self.metadata_type))
        output.append("    </types>")
        return output

    def strip_folder(self, component_list):
        for item in sorted(os.listdir(self.directory)):
            if item.startswith("."):
                continue

            # Ignore the CODEOWNERS file which is special to Github
            if item in ["CODEOWNERS", "OWNERS"]:
                continue

            if item.endswith("-meta.xml"):
                continue

            if self.extension and not item.endswith("." + self.extension):
                continue

            self._strip_component(item, component_list)

    def _strip_component(self, item, component_list):
        raise NotImplementedError(
            "Subclasses should implement their stripping component logic"
        )


class MetadataFilenameParser(BaseMetadataParser):
    def _parse_item(self, item):
        return [self.strip_extension(item)]

    def _strip_component(self, item, component_list):
        if self.strip_extension(item) not in component_list:
            path = os.path.join(self.directory, item)
            self.logger.info(
                f"Deleting component {self.strip_extension(item)} of type {self.metadata_type}"
            )
            os.remove(path)
            if os.path.exists(path + "-meta.xml"):
                os.remove(path + "-meta.xml")


class MetadataFolderParser(BaseMetadataParser):
    def _parse_item(self, item):
        members = []
        path = self.directory + "/" + item

        # Skip non-directories
        if not os.path.isdir(path):
            return members

        # Only add the folder itself if its -meta.xml is present
        # (If there's no -meta.xml, this package is adding items to an existing folder.)
        if Path(path + "-meta.xml").exists():
            members.append(item)

        for subitem in sorted(os.listdir(path)):
            if subitem.endswith("-meta.xml") or subitem.startswith("."):
                continue
            submembers = self._parse_subitem(item, subitem)
            members.extend(submembers)

        return members

    def check_delete_excludes(self, item):
        return False

    def _parse_subitem(self, item, subitem):
        return [item + "/" + self.strip_extension(subitem)]

    def _strip_component(self, item, component_list):
        path = os.path.join(self.directory, item)
        # Check if it is a directory and take action
        if (
            os.path.isdir(path)
            and os.path.exists(path + "-meta.xml")
            and item not in component_list
        ):
            self.logger.info(f"Deleting component {item} of type {self.metadata_type}")
            shutil.rmtree(path)
            os.remove(path + "-meta.xml")

        if os.path.isdir(path):
            for subitem in sorted(os.listdir(path)):
                if subitem.endswith("-meta.xml") or subitem.startswith("."):
                    continue
                self._strip_subitem(item, subitem, component_list)

    def _strip_subitem(self, item, subitem, component_list):
        if item + "/" + self.strip_extension(subitem) not in component_list:
            path = os.path.join(self.directory, item, subitem)
            self.logger.info(
                f"Deleting component {item}/{self.strip_extension(subitem)} of type {self.metadata_type}"
            )
            os.remove(path)
            if os.path.exists(path + "-meta.xml"):
                os.remove(path + "-meta.xml")


class MissingNameElementError(Exception):
    pass


class ParserConfigurationError(Exception):
    pass


class MetadataXmlElementParser(BaseMetadataParser):

    namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

    def __init__(
        self,
        metadata_type,
        directory,
        extension,
        delete,
        logger=None,
        item_xpath=None,
        name_xpath=None,
    ):
        super(MetadataXmlElementParser, self).__init__(
            metadata_type, directory, extension, delete, logger
        )
        if not item_xpath:
            raise ParserConfigurationError("You must provide a value for item_xpath")
        self.item_xpath = item_xpath
        if not name_xpath:
            name_xpath = "./sf:fullName"
        self.name_xpath = name_xpath

    def _parse_item(self, item):
        root = elementtree_parse_file(self.directory + "/" + item)
        members = []

        parent = self.strip_extension(item)

        for item in self.get_item_elements(root):
            members.append(self.get_item_name(item, parent))

        return members

    def check_delete_excludes(self, item):
        return False

    def get_item_elements(self, root):
        return root.findall(self.item_xpath, self.namespaces)

    def get_name_elements(self, item):
        return item.findall(self.name_xpath, self.namespaces)

    def get_item_name(self, item, parent):
        """Returns the value of the first name element found inside of element"""
        names = self.get_name_elements(item)
        if not names:
            raise MissingNameElementError

        name = names[0].text
        prefix = self.item_name_prefix(parent)
        if prefix:
            name = prefix + name

        return name

    def item_name_prefix(self, parent):
        return parent + "."

    def _strip_component(self, item, component_list):
        parent = self.strip_extension(item)
        package_tree = elementtree_parse_file(
            os.path.join(self.directory, item), namespace=self.namespaces["sf"]
        )
        root = package_tree.getroot()
        for element in self.get_item_elements(root):
            component_name = (
                self.item_name_prefix(parent) + self.get_name_elements(element)[0].text
            )
            if component_name not in component_list:
                self.logger.info(
                    f"Deleting component {component_name} of type {self.metadata_type}"
                )
                root.remove(element)
        package_tree.write(
            os.path.join(self.directory, item), encoding="UTF-8", xml_declaration=True
        )


# TYPE SPECIFIC PARSERS


class CustomLabelsParser(MetadataXmlElementParser):
    def item_name_prefix(self, parent):
        return ""


class CustomObjectParser(MetadataFilenameParser):
    def _parse_item(self, item):
        members = []

        # Skip namespaced custom objects
        if len(item.split("__")) > 2:
            return members

        # Skip standard objects
        if (
            not item.endswith("__c.object")
            and not item.endswith("__mdt.object")
            and not item.endswith("__e.object")
            and not item.endswith("__b.object")
        ):
            return members

        members.append(self.strip_extension(item))
        return members

    def _strip_component(self, item, component_list):
        # Skip namespaced custom objects
        if len(item.split("__")) > 2:
            return

        # Skip standard objects
        if (
            not item.endswith("__c.object")
            and not item.endswith("__mdt.object")
            and not item.endswith("__e.object")
            and not item.endswith("__b.object")
        ):
            return

        if self.strip_extension(item) not in component_list:
            self.logger.info(
                f"Deleting component {self.strip_extension(item)} of type {self.metadata_type}"
            )
            path = os.path.join(self.directory, item)
            os.remove(path)


class RecordTypeParser(MetadataXmlElementParser):
    def check_delete_excludes(self, item):
        if self.delete:
            return True


class BusinessProcessParser(MetadataXmlElementParser):
    def check_delete_excludes(self, item):
        if self.delete:
            return True


class BundleParser(BaseMetadataParser):
    def _parse_item(self, item):
        members = []
        path = self.directory + "/" + item

        # Skip non-directories
        if not os.path.isdir(path):
            return members

        # item is a directory; add directory to members and ignore processing directory's files
        members.append(item)

        return members

    def _strip_component(self, item, component_list):
        path = os.path.join(self.directory, item)
        # Check if it is a directory and take action
        if os.path.isdir(path):
            if item not in component_list:
                self.logger.info(
                    f"Deleting component {item} of type {self.metadata_type}"
                )
                shutil.rmtree(path)


class LWCBundleParser(BaseMetadataParser):
    def _parse_item(self, item):
        members = []
        path = self.directory + "/" + item

        # Skip non-directories
        if not os.path.isdir(path) or item.startswith("__"):
            return members

        # item is a directory; add directory to members and ignore processing directory's files
        members.append(item)

        return members

    def _strip_component(self, item, component_list):
        path = os.path.join(self.directory, item)
        # Check if it is a directory and take action
        if os.path.isdir(path):
            if item not in component_list:
                self.logger.info(
                    f"Deleting component {item} of type {self.metadata_type}"
                )
                shutil.rmtree(path)


class DocumentParser(MetadataFolderParser):
    def _parse_subitem(self, item, subitem):
        return [item + "/" + subitem]

    def _strip_subitem(self, item, subitem, component_list):
        if item + "/" + subitem not in component_list:
            path = os.path.join(self.directory, item, subitem)
            self.logger.info(
                f"Deleting component {item}/{subitem} of type {self.metadata_type}"
            )
            os.remove(path)
            if os.path.exists(path + "-meta.xml"):
                os.remove(path + "-meta.xml")


class UpdatePackageXml(BaseTask):
    task_options = {
        "path": {
            "description": "The path to a folder of metadata to build the package.xml from",
            "required": True,
        },
        "output": {"description": "The output file, defaults to <path>/package.xml"},
        "package_name": {
            "description": "If set, overrides the package name inserted into the <fullName> element"
        },
        "managed": {
            "description": "If True, generate a package.xml for deployment to the managed package packaging org"
        },
        "delete": {
            "description": "If True, generate a package.xml for use as a destructiveChanges.xml file for deleting metadata"
        },
        "install_class": {
            "description": "Specify post install class file to be used. Defaults to what is set in project config"
        },
        "uninstall_class": {
            "description": "Specify post uninstall class file to be used. Defaults to what is set in project config"
        },
    }

    def _init_options(self, kwargs):
        super(UpdatePackageXml, self)._init_options(kwargs)
        self.options["managed"] = self.options.get("managed") in (True, "True", "true")

    def _init_task(self):
        package_name = self.options.get("package_name")
        if not package_name:
            if self.options.get("managed"):
                package_name = self.project_config.project__package__name_managed
            if not package_name:
                package_name = self.project_config.project__package__name

        self.package_xml = PackageXmlGenerator(
            directory=self.options.get("path"),
            api_version=self.project_config.project__package__api_version,
            package_name=package_name,
            managed=self.options.get("managed", False),
            delete=self.options.get("delete", False),
            install_class=self.options.get(
                "install_class", self.project_config.project__package__install_class
            ),
            uninstall_class=self.options.get(
                "uninstall_class", self.project_config.project__package__uninstall_class
            ),
        )

    def _run_task(self):
        output = self.options.get(
            "output", "{}/package.xml".format(self.options.get("path"))
        )
        self.logger.info(
            "Generating {} from metadata in {}".format(output, self.options.get("path"))
        )
        package_xml = self.package_xml()
        with open(self.options.get("output", output), mode="w", encoding="utf-8") as f:
            f.write(package_xml)


class RemoveSourceComponents:
    def __init__(self, directory, package_xml, api_version, logger):
        self.directory = directory
        self.package_xml = package_xml
        self.api_version = api_version
        self.logger = logger

    def __call__(self):
        xml_map = self.generate_package_xml_map()
        self.folder_parser = PackageXmlGenerator(
            directory=self.directory, api_version=self.api_version, logger=self.logger
        )
        self.folder_parser.parse_types()
        self.folder_parser.types.sort(key=lambda x: x.metadata_type.upper())
        for parse_type in self.folder_parser.types:
            parse_type.strip_folder(
                xml_map[parse_type.metadata_type]
                if parse_type.metadata_type in xml_map
                else []
            )

    def generate_package_xml_map(self) -> dict:
        package = metadata_tree.parse(self.package_xml)
        xml_map = {}
        for type in package.types:
            members = []
            try:
                for member in type.members:
                    members.append(member.text)
            except AttributeError:  # Exception if there are no members for a type
                pass
            xml_map[type["name"].text] = members
        return xml_map


class RemoveUnwantedComponents(BaseTask):
    task_options = {
        "path": {
            "description": "The path to a folder of metadata to strip the components",
            "required": True,
        },
        "package_xml": {
            "description": "The path to package xml file to refer",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.run_class = RemoveSourceComponents(
            directory=self.options.get("path"),
            package_xml=self.options.get("package_xml"),
            api_version=self.project_config.project__package__api_version,
            logger=self.logger,
        )

    def _run_task(self):
        self.logger.info(
            "Removing unwanted components from " + self.options.get("path")
        )
        self.run_class()
