from __future__ import annotations

import abc
import functools
import io
import os
import typing as T
import zipfile
from logging import Logger
from zipfile import ZipFile

from pydantic import BaseModel

from cumulusci.utils import (
    cd,
    inject_namespace,
    strip_namespace,
    temporary_dir,
    tokenize_namespace,
    zip_clean_metaxml,
)
from cumulusci.utils.xml import metadata_tree
from cumulusci.utils.ziputils import process_text_in_zipfile


class SourceTransform(abc.ABC):
    """Abstract base class for a transformation applied to a Metadata API deployment package"""

    options_model: T.Optional[T.Type[BaseModel]]
    identifier: str

    def __init__(self):
        ...

    @abc.abstractmethod
    def process(self, zf: ZipFile, logger: Logger) -> ZipFile:
        ...


class NamespaceInjectionOptions(BaseModel):
    namespace_tokenize: T.Optional[str]
    namespace_inject: T.Optional[str]
    namespace_strip: T.Optional[str]
    unmanaged: bool = True
    namespaced_org: bool = False


class NamespaceInjectionTransform(SourceTransform):
    """Source transform that applies namespace injection, stripping, and tokenization."""

    options_model = NamespaceInjectionOptions
    options: NamespaceInjectionOptions

    identifier = "inject_namespace"

    def __init__(self, options: NamespaceInjectionOptions):
        self.options = options

    def process(self, zf: ZipFile, logger: Logger) -> ZipFile:
        if self.options.namespace_tokenize:
            logger.info(
                f"Tokenizing namespace prefix {self.options.namespace_tokenize}__"
            )
            zf = process_text_in_zipfile(
                zf,
                functools.partial(
                    tokenize_namespace,
                    namespace=self.options.namespace_tokenize,
                    logger=logger,
                ),
            )
        if self.options.namespace_inject:
            managed = not self.options.unmanaged
            if managed:
                logger.info(
                    "Replacing namespace tokens from metadata with namespace prefix  "
                    f"{self.options.namespace_inject}__"
                )
            else:
                logger.info(
                    "Stripping namespace tokens from metadata for unmanaged deployment"
                )
            zf = process_text_in_zipfile(
                zf,
                functools.partial(
                    inject_namespace,
                    namespace=self.options.namespace_inject,
                    managed=managed,
                    namespaced_org=self.options.namespaced_org,
                    logger=logger,
                ),
            )
        if self.options.namespace_strip:
            logger.info("Stripping namespace tokens from metadata")
            zf = process_text_in_zipfile(
                zf,
                functools.partial(
                    strip_namespace,
                    namespace=self.options.namespace_strip,
                    logger=logger,
                ),
            )

        return zf


class RemoveFeatureParametersTransform(SourceTransform):
    """Source transform that removes Feature Parameters. Intended for use on Unlocked Package builds."""

    options_model = None

    identifier = "remove_feature_parameters"

    def process(self, zf: ZipFile, logger: Logger) -> ZipFile:
        package_xml = None
        zip_dest = ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
        for name in zf.namelist():
            if name == "package.xml":
                package_xml = zf.open(name)
            elif name.startswith("featureParameters/"):
                # skip feature parameters
                logger.info(f"Skipping {name} because Feature Parameters are omitted.")
            else:
                content = zf.read(name)
                zip_dest.writestr(name, content)

        # Remove from package.xml
        if package_xml is not None:
            package = metadata_tree.parse(package_xml)
            for mdtype in (
                "FeatureParameterInteger",
                "FeatureParameterBoolean",
                "FeatureParameterDate",
            ):
                section = package.find("types", name=mdtype)
                if section is not None:
                    package.remove(section)
            package_xml = package.tostring(xml_declaration=True)
            zip_dest.writestr("package.xml", package_xml)

        return zip_dest


class CleanMetaXMLTransform(SourceTransform):
    """Source transform that cleans *-meta.xml files of references to specific package versions."""

    options_model = None

    identifier = "clean_meta_xml"

    def process(self, zf: ZipFile, logger: Logger) -> ZipFile:
        logger.info("Cleaning meta.xml files of packageVersion elements for deploy")
        return zip_clean_metaxml(zf)


class BundleStaticResourcesOptions(BaseModel):
    static_resource_path: str


class BundleStaticResourcesTransform(SourceTransform):
    """Source transform that zips static resource content from an external path"""

    options_model = BundleStaticResourcesOptions
    options: BundleStaticResourcesOptions
    identifier = "bundle_static_resources"

    def __init__(self, options: BundleStaticResourcesOptions):
        self.options = options

    def process(self, zf: ZipFile, logger: Logger) -> ZipFile:
        path = os.path.realpath(self.options.static_resource_path)

        # Copy existing files to new zipfile
        zip_dest = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
        package_xml = None
        for name in zf.namelist():
            if name == "package.xml":
                package_xml = zf.open(name)
            else:
                content = zf.read(name)
                zip_dest.writestr(name, content)

        if not package_xml:
            raise Exception("No package.xml found; cannot zip Static Resources")

        # Build static resource bundles and add to package
        with temporary_dir():
            os.mkdir("staticresources")
            bundles = []
            for name in os.listdir(path):
                bundle_relpath = os.path.join(self.options.static_resource_path, name)
                bundle_path = os.path.join(path, name)
                if not os.path.isdir(bundle_path):
                    continue
                logger.info(f"Zipping {bundle_relpath} to add to staticresources")

                # Add resource-meta.xml file
                meta_name = f"{name}.resource-meta.xml"
                meta_path = os.path.join(path, meta_name)
                with open(meta_path, "rb") as f:
                    zip_dest.writestr(f"staticresources/{meta_name}", f.read())

                # Add bundle
                zip_path = os.path.join("staticresources", f"{name}.resource")
                with open(zip_path, "wb") as bundle_fp:
                    bundle_zip = zipfile.ZipFile(bundle_fp, "w", zipfile.ZIP_DEFLATED)
                    with cd(bundle_path):
                        for root, _, files in os.walk("."):
                            for f in files:
                                resource_file = os.path.join(root, f)
                                bundle_zip.write(resource_file)
                    bundle_zip.close()
                zip_dest.write(zip_path)
                bundles.append(name)

        # Update package.xml
        package = metadata_tree.parse(package_xml)
        sections = package.findall("types", name="StaticResource")
        section = sections[0] if sections else None
        if not section:
            section = package.append("types")
            section.append("name", text="StaticResource")
        for name in sorted(bundles):
            section.insert_before(section.find("name"), tag="members", text=name)
        package_xml = package.tostring(xml_declaration=True)
        zip_dest.writestr("package.xml", package_xml)

        return zip_dest


def get_available_transforms() -> T.Dict[str, T.Type[SourceTransform]]:
    """Get a mapping of identifiers (usable in cumulusci.yml) to transform classes"""
    return {
        cls.identifier: cls
        for cls in [
            CleanMetaXMLTransform,
            NamespaceInjectionTransform,
            RemoveFeatureParametersTransform,
            BundleStaticResourcesTransform,
        ]
    }
