from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple
import pathlib
import shutil

from cumulusci.core.config import UniversalConfig
from cumulusci.tasks.metadata.package import metadata_sort_key
from cumulusci.utils.xml import metadata_tree
from cumulusci.utils.xml.metadata_tree import MetadataElement


class MetadataProcessor:
    def __init__(
        self,
        type_name: Optional[str],
        extension: str = None,
        additional: Dict[str, str] = None,
    ):
        self.type_name = type_name
        self.extension = extension
        self.additional = additional or {}

    def __iter__(self):
        # horrible hack to make it simpler to construct MD_PROCESSORS below
        # (so that a single MetadataProcessor instance can pass type checking
        # for Iterable[MetadataProcessor])
        return iter((self,))

    def collect_members(self, path: pathlib.Path) -> Dict[str, List[str]]:
        """List metadata components found in this path."""
        types = defaultdict(list)
        for item in sorted(path.iterdir()):
            name = item.name
            if name.startswith("."):
                continue

            for name in self.collect_members_from_subpath(item):
                name = self._strip_extension(name)
                name = name.replace("___NAMESPACE___", "%%%NAMESPACE%%%")
                if self.type_name is not None:
                    types[self.type_name].append(name)

            if self.additional:
                self.collect_additional_members(types, item)

        return types

    def collect_members_from_subpath(self, path: pathlib.Path):
        if self.extension and not path.name.endswith(self.extension):
            return
        yield path.name

    def collect_additional_members(
        self, types: Dict[str, List[str]], path: pathlib.Path
    ):
        parent = self._strip_extension(path.name)
        tree = metadata_tree.parse(path)
        for tag, type_name in self.additional.items():
            for el in tree.findall(tag):
                name = f"{parent}.{el.fullName.text}"
                types[type_name].append(name)

    def _strip_extension(self, name: str):
        if self.extension and name.endswith(self.extension):
            name = name[: -len(self.extension)]
        return name

    def merge(self, path: pathlib.Path, src: pathlib.Path, target: pathlib.Path):
        """Merge metadata components into another package."""
        # Make sure metadata folder exists in target package
        (target / path.relative_to(src)).mkdir(parents=True, exist_ok=True)

        for item in path.iterdir():
            if item.name.startswith("."):
                continue

            relative_path = item.relative_to(src)
            target_item_path = target / relative_path

            if self.extension and item.name.endswith(self.extension):
                # merge metadata xml
                self._merge_xml(item, target_item_path)
            else:
                # copy entire folder or file
                copy_op = shutil.copytree if item.is_dir() else shutil.copy
                copy_op(str(item), str(target_item_path))

    def _merge_xml(self, src: pathlib.Path, target: pathlib.Path):
        src_tree = metadata_tree.parse(src)

        # Load or create destination file
        if target.exists():
            target_tree = metadata_tree.parse(target)
        else:
            target_tree = MetadataElement(src_tree.tag)

        additional_metadata_tags = set(self.additional)
        src_has_primary_metadata = any(
            el.tag not in additional_metadata_tags for el in src_tree.iterchildren()
        )

        # First do a pass through the destination file
        # to produce a new list of children that:
        # - preserves elements which are additional metadata types
        # - replaces elements which are not additional metadata types
        #   with the corresponding tags from the source file
        # - keeps existing tags in the same position
        merged_tree = MetadataElement(target_tree.tag)
        for el in target_tree.iterchildren():
            if el.tag in additional_metadata_tags or not src_has_primary_metadata:
                merged_tree.append(el)
            else:
                # If src includes any elements which are not additional metadata,
                # replace all non-additional elements in dest with the corresponding ones from src.
                for el in src_tree.findall(el.tag):
                    # NB this has the side effect of removing them from src_tree,
                    # which we want in order to avoid appending them again below.
                    merged_tree.append(el)

        # Now do a pass through src_tree to handle any tags that were not yet in dest_tree:
        # - additional metadata: replace or append, matching on fullName
        # - non-additional metadata: append
        for el in list(src_tree.iterchildren()):
            if el.tag in additional_metadata_tags:
                existing_el = merged_tree.find(el.tag, fullName=el.fullName.text)
                if existing_el is not None:
                    merged_tree.replace(existing_el, el)
                    continue
            merged_tree.append(el)

        # write merged file
        target.write_text(merged_tree.tostring())


class FolderMetadataProcessor(MetadataProcessor):
    type_name: str

    def collect_members_from_subpath(self, path):
        if not path.is_dir():
            return

        # Add the member if it is not namespaced
        name = path.name
        if "__" not in name:
            yield name

        # Add subitems
        for subpath in sorted(path.iterdir()):
            subname = subpath.name
            if subname.startswith(".") or subname.endswith("-meta.xml"):
                continue
            subname = self._strip_extension(subname)
            yield f"{name}/{subname}"

    def merge(self, path: pathlib.Path, src: pathlib.Path, target: pathlib.Path):
        # Copy each component's file to the corresponding path in the target package.
        members = self.collect_members(path)
        for name in members[self.type_name]:
            if "/" in name:
                item = path / (name + (self.extension or ""))
            else:
                # folder -- only need to copy the -meta.xml
                item = path / (name + "-meta.xml")
            relpath = item.relative_to(src)
            (target / relpath).parent.mkdir(parents=True, exist_ok=True)
            if not item.is_dir():
                shutil.copy(str(item), str(target / relpath))
            meta_xml = item.parent / (item.name + "-meta.xml")
            if meta_xml.exists():
                shutil.copy(str(meta_xml), str(target / relpath) + "-meta.xml")


class BundleMetadataProcessor(MetadataProcessor):
    def collect_members_from_subpath(self, path):
        if path.is_dir():
            yield path.name


class XmlElementMetadataProcessor(MetadataProcessor):
    def __init__(self, type_name: Optional[str], extension: str, tag: str):
        self.type_name = type_name
        self.extension = extension
        self.tag = tag
        self.additional = ()

    def collect_members_from_subpath(self, path):
        parent = self._strip_extension(path.name)
        tree = metadata_tree.parse(path)
        for el in tree.findall(self.tag):
            name = el.fullName.text
            yield f"{parent}.{name}"


class ObjectMetadataProcessor(MetadataProcessor):
    def collect_members_from_subpath(self, path):
        name = path.name

        # Skip namespaced custom objects
        if len(name.split("__")) > 2:
            return

        # Skip standard objects
        if not name.endswith(
            ("__c.object", "__mdt.object", "__e.object", "__b.object")
        ):
            return

        yield name


def _iter_processors(
    path: pathlib.Path,
) -> Iterable[Tuple[pathlib.Path, MetadataProcessor]]:
    """Gets a processor for each folder in a metadata package"""
    for item in path.iterdir():
        if item.name.startswith(".") or not item.is_dir():
            continue
        try:
            processors = MD_PROCESSORS[item.name]
        except KeyError:
            raise Exception(f"Unexpected folder in metadata package: {item}")
        for processor in processors:
            yield item, processor


class MetadataPackage:
    """Represents a Salesforce metadata package
    https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_package.htm
    """

    def __init__(self, types: Dict[str, List[str]] = None, version: str = None):
        self.types = defaultdict(list)
        for k, v in types.items():
            self.types[k] = v
        self.version = version or UniversalConfig().package__api_version

    @classmethod
    def from_path(cls, path: pathlib.Path):
        version = None
        manifest_path = path / "package.xml"
        if manifest_path.exists():
            manifest = metadata_tree.parse(manifest_path)
            version = str(manifest.version.text)

        types: Dict[str, List[str]] = {}
        for folder_path, processor in _iter_processors(path):
            types.update(processor.collect_members(folder_path))
        return MetadataPackage(types, version)

    def write_manifest(self, path):
        manifest_path = path / "package.xml"
        manifest = MetadataElement("Package")
        for name, members in sorted(self.types.items()):
            types = MetadataElement("types")
            for member in sorted(members, key=metadata_sort_key):
                types.append("members", member)
            manifest.append(types)
        manifest.append("version", self.version)
        manifest_path.write_text(manifest.tostring(xml_declaration=True))


def write_manifest(components: Dict[str, List[str]], api_version, path: pathlib.Path):
    """Write package.xml including components to the specified path."""
    MetadataPackage(components, api_version).write_manifest(path)


def update_manifest(path: pathlib.Path):
    """Generate package.xml based on actual metadata present in a folder."""
    MetadataPackage.from_path(path).write_manifest(path)


def merge_metadata(
    src: pathlib.Path, dest: pathlib.Path, update_manifest=update_manifest
):
    """Merge one metadata package into another.

    The merging logic for each subfolder is delegated to a MetadataProcessor.
    """
    for folder_path, processor in _iter_processors(src):
        processor.merge(folder_path, src, dest)

    if update_manifest:
        update_manifest(dest)


MD_PROCESSORS: Dict[str, Iterable[MetadataProcessor]] = {
    "applications": MetadataProcessor("CustomApplication", ".app"),
    "aura": BundleMetadataProcessor("AuraDefinitionBundle"),
    "classes": MetadataProcessor("ApexClass", ".cls-meta.xml"),
    "components": MetadataProcessor("ApexComponent", ".component"),
    "customMetadata": MetadataProcessor("CustomMetadata", ".md"),
    "documents": FolderMetadataProcessor("Document"),
    "email": FolderMetadataProcessor("EmailTemplate", ".email"),
    "featureParameters": (
        MetadataProcessor("FeatureParameterBoolean", ".featureParameterBoolean"),
        MetadataProcessor("FeatureParameterInteger", ".featureParameterInteger"),
    ),
    "flexipages": MetadataProcessor("FlexiPage", ".flexipage"),
    "labels": MetadataProcessor("CustomLabels", ".labels"),
    "layouts": MetadataProcessor("Layout", ".layout"),
    "letterhead": MetadataProcessor("Letterhead", ".letter"),
    "lwc": BundleMetadataProcessor("LightningComponentBundle"),
    "matchingRules": XmlElementMetadataProcessor(
        "MatchingRule", ".matchingRule", "matchingRules"
    ),
    "objects": ObjectMetadataProcessor(
        "CustomObject",
        ".object",
        {
            "businessProcesses": "BusinessProcess",
            "compactLayouts": "CompactLayout",
            "fields": "CustomField",
            "fieldSets": "FieldSet",
            "indexes": "Index",
            "listViews": "ListView",
            "namedFilters": "NamedFilter",
            "recordTypes": "RecordType",
            "sharingReasons": "SharingReason",
            "validationRules": "ValidationRule",
            "webLinks": "WebLink",
        },
    ),
    "objectTranslations": MetadataProcessor(
        "CustomObjectTranslation", ".objectTranslation"
    ),
    "pages": MetadataProcessor("ApexPage", ".page"),
    "quickActions": MetadataProcessor("QuickAction", ".quickAction"),
    "remoteSiteSettings": MetadataProcessor("RemoteSiteSetting", ".remoteSite"),
    "reports": FolderMetadataProcessor("Report", ".report"),
    "reportTypes": MetadataProcessor("ReportType", ".reportType"),
    "staticresources": MetadataProcessor("StaticResource", ".resource"),
    "tabs": MetadataProcessor("CustomTab", ".tab"),
    "translations": MetadataProcessor("Translations", ".translation"),
    "triggers": MetadataProcessor("ApexTrigger", ".trigger"),
    "workflows": MetadataProcessor(
        None,
        ".workflow",
        {
            "alerts": "WorkflowAlert",
            "fieldUpdates": "WorkflowFieldUpdate",
            "outboundMessages": "WorkflowOutboundMessage",
            "rules": "WorkflowRule",
            "tasks": "WorkflowTask",
        },
    ),
}

# To do:
# - coverage
# - add missing types
# - preserve package settings
# - use it to generate package.xml elsewhere
