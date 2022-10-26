import abc
import os
import re
import urllib.parse
import xml.etree.ElementTree as etree
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Callable, DefaultDict, Dict, List, Optional, Type

import yaml
from pydantic import BaseModel, Field, PrivateAttr

from cumulusci.core.tasks import BaseTask
from cumulusci.utils import elementtree_parse_file
from cumulusci.utils.xml.metadata_tree import MetadataElement

__location__ = os.path.dirname(os.path.realpath(__file__))


def metadata_sort_key(name: str) -> str:
    sections = []
    for section in re.split("[.|-]", name):
        sections.append(metadata_sort_key_section(section))

    key = "_".join(sections)
    key = key.replace("_", "Z")

    return key


def metadata_sort_key_section(name: str) -> str:
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


class RawMetadataMapEntry(BaseModel):
    entity: str = Field(alias="type")
    parser_class: str = Field(alias="class")
    extension: Optional[str] = None
    options: dict = {}


class MetadataMapEntry(BaseModel):
    entity: str
    subdirectory: str
    parser_class: Type["BaseMetadataParser"]
    extension: Optional[str] = None
    options: dict

    def get_parser(self, directory: str, delete: bool = False) -> "BaseMetadataParser":
        return self.parser_class(
            self.entity,
            directory + "/" + self.subdirectory,
            self.extension,
            delete,
            **self.options,
        )


class MetadataMap(BaseModel):
    __root__: Dict[str, List[RawMetadataMapEntry]]

    _by_entity: Dict[str, MetadataMapEntry] = PrivateAttr()
    _by_directory: DefaultDict[str, List[MetadataMapEntry]] = PrivateAttr()

    def cache(self):
        # Populate the cache dicts from the raw entries
        self._by_entity = {}
        self._by_directory = defaultdict(list)
        for subdir, configs in self.__root__.items():
            for config in configs:
                entry = MetadataMapEntry(
                    entity=config.entity,
                    parser_class=globals()[
                        config.parser_class
                    ],  # TODO: this is fragile and requires all subclasses to be in this module.
                    extension=config.extension,
                    subdirectory=subdir,
                    options=config.options,
                )
                self._by_entity[entry.entity] = entry
                self._by_directory[entry.subdirectory].append(entry)

    def config_for_entity(self, entity: str) -> Optional[MetadataMapEntry]:
        return self._by_entity.get(entity)

    def configs_for_directory(self, dir: str) -> List[MetadataMapEntry]:
        return self._by_directory[dir]


class MetadataParserMissingError(Exception):
    pass


@lru_cache()
def get_metadata_map() -> MetadataMap:
    with open(
        __location__ + "/metadata_map.yml", "r", encoding="utf-8"
    ) as f_metadata_map:
        m = MetadataMap.parse_obj(yaml.safe_load(f_metadata_map))
        m.cache()
        return m


class PackageComponent(BaseModel):
    name: str
    paths: List[str]
    content: Optional[bytes]
    xml_root: Optional[MetadataElement]
    xml_element: Optional[MetadataElement]


class PackageXmlGenerator:
    # `types` is supplied as a list of an unrelated Callable class in cumulusci.tasks.salesforce.sourcetracking
    # Essentially this is structural subtyping, but since it's a Callable, we don't need a Protocol to type it.
    types: List[Callable[[], Optional[List[str]]]]
    install_class: Optional[str]
    uninstall_class: Optional[str]
    managed: bool
    delete: bool
    package_name: Optional[str]
    directory: str
    api_version: str

    def __init__(
        self,
        directory: str,
        api_version: str,
        package_name: Optional[str] = None,
        managed: bool = False,
        delete: bool = False,
        install_class: Optional[str] = None,
        uninstall_class: Optional[str] = None,
        types: Optional[List[Callable[[], Optional[List[str]]]]] = None,
    ):
        self.directory = directory
        self.api_version = api_version
        self.package_name = package_name
        self.managed = managed
        self.delete = delete
        self.install_class = install_class
        self.uninstall_class = uninstall_class
        self.types = types or []

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
            metadata_map = get_metadata_map()
            configs = metadata_map.configs_for_directory(item)
            if not configs:
                raise MetadataParserMissingError(
                    "No parser configuration found for subdirectory %s" % item
                )

            for parser_config in configs:
                self.types.append(parser_config.get_parser(self.directory, self.delete))

    def render_xml(self) -> str:
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


class BaseMetadataParser(abc.ABC):
    metadata_type: str
    directory: str
    extension: Optional[str]
    delete: bool
    members: list
    delete_excludes: Optional[List[str]]

    def __init__(
        self, metadata_type: str, directory: str, extension: Optional[str], delete: bool
    ):
        self.metadata_type = metadata_type
        self.directory = directory
        self.extension = extension
        self.delete = delete
        self.members = []

        if self.delete:
            self.delete_excludes = self.get_delete_excludes()

    def __call__(self) -> Optional[List[str]]:
        self.parse_items()
        return self.render_xml()

    def get_delete_excludes(self) -> List[str]:
        filename = os.path.join(
            __location__, "..", "..", "files", "delete_excludes.txt"
        )
        excludes = []
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                excludes.append(line.strip())
        return excludes

    @abc.abstractmethod
    def find_item(self, item: str) -> Optional[PackageComponent]:
        """Locate the on-disk representation of the given component"""
        ...

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

    def check_delete_excludes(self, item: str) -> bool:
        if not self.delete:
            return False
        if item in self.delete_excludes:  # type: ignore
            return True
        return False

    def parse_item(self, item: str):
        members = self._parse_item(item)
        if members:
            for member in members:
                # Translate filename namespace tokens into in-file namespace tokens
                member = member.replace("___NAMESPACE___", "%%%NAMESPACE%%%")
                self.members.append(member)

    @abc.abstractmethod
    def _parse_item(self, item: str) -> List[str]:
        "Receives a file or directory name and returns a list of members"
        ...

    def strip_extension(self, filename: str) -> str:
        return filename.rsplit(".", 1)[0]

    def render_xml(self) -> Optional[List[str]]:
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


class MetadataFilenameParser(BaseMetadataParser):
    def _parse_item(self, item: str) -> List[str]:
        return [self.strip_extension(item)]

    def find_item(self, item: str) -> Optional[PackageComponent]:
        if self.extension:
            filename = f"{item}.{self.extension}"
        else:
            filename = item

        path = Path(self.directory) / filename
        if path.exists():
            return PackageComponent(
                name=item,
                paths=[str(path)],
                content=None,
                xml_root=None,
                xml_element=None,
            )


class MetadataFolderParser(BaseMetadataParser):
    def _parse_item(self, item: str) -> List[str]:
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

    def find_item(self, item: str) -> Optional[PackageComponent]:
        if self.extension:
            filename = f"{item}.{self.extension}"
        else:
            filename = item

        path = Path(self.directory) / filename
        if path.exists():
            return PackageComponent(
                name=item,
                paths=[str(path)],
                content=None,
                xml_root=None,
                xml_element=None,
            )

    def check_delete_excludes(self, item: str) -> bool:
        return False

    def _parse_subitem(self, item: str, subitem: str) -> List[str]:
        return [item + "/" + self.strip_extension(subitem)]


class MissingNameElementError(Exception):
    pass


class ParserConfigurationError(Exception):
    pass


class MetadataXmlElementParser(BaseMetadataParser):

    namespaces: Dict[str, str] = {"sf": "http://soap.sforce.com/2006/04/metadata"}
    name_xpath: str
    item_xpath: str

    def __init__(
        self,
        metadata_type: str,
        directory: str,
        extension: str,
        delete: bool,
        item_xpath: Optional[str] = None,
        name_xpath: Optional[str] = None,
    ):
        super(MetadataXmlElementParser, self).__init__(
            metadata_type, directory, extension, delete
        )
        if not item_xpath:
            raise ParserConfigurationError("You must provide a value for item_xpath")
        self.item_xpath = item_xpath
        self.name_xpath = name_xpath or "./sf:fullName"

    def _parse_item(self, item: str) -> List[str]:
        root = elementtree_parse_file(self.directory + "/" + item)
        members = []

        parent = self.strip_extension(item)

        for elem in self.get_item_elements(root):
            members.append(self.get_item_name(elem, parent))

        return members

    def find_item(self, item: str) -> Optional[PackageComponent]:
        path_elements = item.split(".")
        if self.extension:
            filename = f"{path_elements[0]}.{self.extension}"
        else:
            filename = path_elements[0]

        path = Path(self.directory) / filename
        if path.exists():
            root = elementtree_parse_file(path)
            elements = [
                x
                for x in self.get_item_elements(root)
                if self.get_item_name(x, path_elements[0]) == item
            ]
            if elements:
                return PackageComponent(
                    name=item,
                    paths=[str(path)],
                    content=None,
                    xml_root=MetadataElement(root.getroot()),
                    xml_element=MetadataElement(elements[0], root),
                )

    def check_delete_excludes(self, item: str) -> bool:
        return False

    def get_item_elements(self, root: etree.ElementTree) -> List[etree.Element]:
        return root.findall(self.item_xpath, self.namespaces)

    def get_name_elements(self, item: etree.Element) -> List[etree.Element]:
        return item.findall(self.name_xpath, self.namespaces)

    def get_item_name(self, item: etree.Element, parent: str) -> str:
        """Returns the value of the first name element found inside of element"""
        names = self.get_name_elements(item)
        if not names:
            raise MissingNameElementError

        name = names[0].text or ""
        prefix = self.item_name_prefix(parent)
        if prefix:
            name = prefix + name

        return name

    def item_name_prefix(self, parent: str) -> str:
        return parent + "."


# TYPE SPECIFIC PARSERS


class CustomLabelsParser(MetadataXmlElementParser):
    def item_name_prefix(self, parent: str) -> str:
        return ""


class CustomObjectParser(MetadataFilenameParser):
    def _parse_item(self, item: str) -> List[str]:
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


class RecordTypeParser(MetadataXmlElementParser):
    def check_delete_excludes(self, item: str) -> bool:
        return self.delete


class BusinessProcessParser(MetadataXmlElementParser):
    def check_delete_excludes(self, item: str) -> bool:
        return self.delete


class BundleParser(BaseMetadataParser):
    def _parse_item(self, item: str) -> List[str]:
        members = []
        path = self.directory + "/" + item

        # Skip non-directories
        if not os.path.isdir(path):
            return members

        # item is a directory; add directory to members and ignore processing directory's files
        members.append(item)

        return members


class LWCBundleParser(BaseMetadataParser):
    def _parse_item(self, item: str) -> List[str]:
        members = []
        path = self.directory + "/" + item

        # Skip non-directories
        if not os.path.isdir(path) or item.startswith("__"):
            return members

        # item is a directory; add directory to members and ignore processing directory's files
        members.append(item)

        return members


class DocumentParser(MetadataFolderParser):
    def _parse_subitem(self, item: str, subitem: str) -> List[str]:
        return [item + "/" + subitem]


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
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options["managed"] = self.options.get("managed") in (True, "True", "true")

    def _init_task(self):
        package_name = self.options.get("package_name")
        if not package_name:
            if self.options.get("managed"):
                package_name = self.project_config.project__package__name_managed
            if not package_name:
                package_name = self.project_config.project__package__name

        self.package_xml = PackageXmlGenerator(
            directory=self.options["path"],
            api_version=self.project_config.project__package__api_version,
            package_name=package_name,
            managed=self.options.get("managed", False),
            delete=self.options.get("delete", False),
            install_class=self.project_config.project__package__install_class,
            uninstall_class=self.project_config.project__package__uninstall_class,
        )

    def _run_task(self):
        output = self.options.get(
            "output", "{}/package.xml".format(self.options.get("path"))
        )
        self.logger.info(  # type: ignore
            "Generating {} from metadata in {}".format(output, self.options.get("path"))
        )
        package_xml = self.package_xml()
        with open(self.options.get("output", output), mode="w", encoding="utf-8") as f:
            f.write(package_xml)
