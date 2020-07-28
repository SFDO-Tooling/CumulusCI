from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple
import pathlib
import shutil

from cumulusci.core.config import BaseGlobalConfig
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

    def merge(
        self, path: pathlib.Path, src: "MetadataPackage", dest: "MetadataPackage"
    ):
        """Merge metadata components into another package."""
        # Make sure metadata folder exists in destination package
        (dest.path / path.relative_to(src.path)).mkdir(parents=True, exist_ok=True)

        for item in path.iterdir():
            if item.name.startswith("."):
                continue

            relative_path = item.relative_to(src.path)
            dest_item_path = dest.path / relative_path

            if self.extension and item.name.endswith(self.extension):
                # merge metadata xml
                self._merge_xml(item, dest_item_path)
            else:
                # copy entire folder or file
                copy_op = shutil.copytree if item.is_dir() else shutil.copy
                copy_op(str(item), str(dest_item_path))

    def _merge_xml(self, src_path: pathlib.Path, dest_path: pathlib.Path):
        src_tree = metadata_tree.parse(src_path)

        # Load or create destination file
        if dest_path.exists():
            dest_tree = metadata_tree.parse(dest_path)
        else:
            dest_tree = MetadataElement(src_tree.tag)

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
        merged_tree = MetadataElement(dest_tree.tag)
        for el in dest_tree.iterchildren():
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
        dest_path.write_text(merged_tree.tostring())


class FolderMetadataProcessor(MetadataProcessor):
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

    def merge(
        self, path: pathlib.Path, src: "MetadataPackage", target: "MetadataPackage"
    ):
        # Copy each component's file to the corresponding path in the target package.
        members = self.collect_members(path)
        for name in members[self.type_name]:
            if "/" in name:
                item = path / (name + (self.extension or ""))
            else:
                # folder -- only need to copy the -meta.xml
                item = path / (name + "-meta.xml")
            relpath = item.relative_to(src.path)
            (target.path / relpath).parent.mkdir(parents=True, exist_ok=True)
            if not item.is_dir():
                shutil.copy(str(item), str(target.path / relpath))
            meta_xml = item.parent / (item.name + "-meta.xml")
            if meta_xml.exists():
                shutil.copy(str(meta_xml), str(target.path / relpath) + "-meta.xml")


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


class MetadataPackage:
    """A Salesforce metadata package

    https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_package.htm
    """

    def __init__(self, path: pathlib.Path, version: str = None):
        self.path = path
        self.version = version
        self._init_manifest()

    def _init_manifest(self):
        """Read package.xml (or create an empty manifest)"""
        self.manifest_path = self.path / "package.xml"
        if self.manifest_path.exists():
            self.manifest = metadata_tree.parse(self.manifest_path)
            self.version = self.manifest.version.text
        else:
            self.version = BaseGlobalConfig().package__api_version
            self.manifest = MetadataElement("Package")
            self.manifest.append("version", self.version)

    def write_manifest(self):
        """Update package.xml from actual package contents"""
        for name, members in sorted(self.collect_members().items()):
            subtree = self._get_subtree_for_manifest(name, members)
            existing_section = self.manifest.find("types", name=subtree.name.text)
            if existing_section:
                self.manifest.replace(existing_section, subtree)
            else:
                self.manifest.insert_before(self.manifest.version, subtree)
        self.manifest_path.write_text(self.manifest.tostring(xml_declaration=True))

    def collect_members(self) -> Dict[str, List[str]]:
        types = {}
        for folder_path, processor in self.iter_processors():
            types.update(processor.collect_members(folder_path))
        return types

    def _get_subtree_for_manifest(
        self, name: str, members: Iterable[str]
    ) -> MetadataElement:
        """Get the <types> section of package.xml as a MetadataTree"""
        section = MetadataElement("types")
        for member in sorted(members, key=metadata_sort_key):
            section.append("members", member)
        section.append("name", name)
        return section

    def merge_to(self, other: "MetadataPackage"):
        """Merge into another package"""
        for folder_path, processor in self.iter_processors():
            processor.merge(folder_path, self, other)

        # update target package's package.xml
        other.write_manifest()

    def iter_processors(self) -> Iterable[Tuple[pathlib.Path, MetadataProcessor]]:
        """Gets a processor for each folder in the package"""
        for item in self.path.iterdir():
            if item.name.startswith(".") or not item.is_dir():
                continue
            try:
                processors = MD_PROCESSORS[item.name]
            except KeyError:
                raise Exception(f"Unexpected folder in metadata package: {item}")
            for processor in processors:
                yield item, processor


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
