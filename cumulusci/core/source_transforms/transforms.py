import abc
import enum
import functools
import io
import os
import shutil
import typing as T
import zipfile
from pathlib import Path
from zipfile import ZipFile

from pydantic import BaseModel, root_validator

from cumulusci.core.dependencies.utils import TaskContext
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.tasks.metadata.package import RemoveSourceComponents
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
    def process(self, zf: ZipFile, context: TaskContext) -> ZipFile:
        ...


class SourceTransformSpec(BaseModel):
    transform: str
    options: T.Optional[dict]

    def parsed_options(self) -> T.Optional[BaseModel]:
        transform_cls = get_available_transforms()[self.transform]
        if transform_cls.options_model:
            return transform_cls.options_model.parse_obj(self.options or {})

        return None

    @root_validator
    def validate_spec(cls, values):
        transform = values.get("transform")
        if transform not in get_available_transforms():
            raise ValueError(f"Transform {transform} is not valid")

        transform_cls = get_available_transforms()[transform]

        if transform_cls.options_model:
            transform_cls.options_model.parse_obj(values.get("options"))

        return values

    def as_transform(self) -> SourceTransform:
        transform_cls = get_available_transforms()[self.transform]
        if transform_cls.options_model:
            return transform_cls(self.parsed_options())  # type: ignore
        else:
            return transform_cls()


class SourceTransformList(BaseModel):
    __root__: T.List[SourceTransformSpec]

    @root_validator(pre=True)
    def validate_spec_list(cls, values):
        values["__root__"] = [
            {"transform": s} if isinstance(s, str) else s for s in values["__root__"]
        ]

        return values

    def as_transforms(self) -> T.List[SourceTransform]:
        return [
            get_available_transforms()[t]() if isinstance(t, str) else t.as_transform()
            for t in self.__root__
        ]


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

    def process(self, zf: ZipFile, context: TaskContext) -> ZipFile:
        if self.options.namespace_tokenize:
            context.logger.info(
                f"Tokenizing namespace prefix {self.options.namespace_tokenize}__"
            )
            zf = process_text_in_zipfile(
                zf,
                functools.partial(
                    tokenize_namespace,
                    namespace=self.options.namespace_tokenize,
                    logger=context.logger,
                ),
            )
        if self.options.namespace_inject:
            managed = not self.options.unmanaged
            if managed:
                context.logger.info(
                    "Replacing namespace tokens from metadata with namespace prefix  "
                    f"{self.options.namespace_inject}__"
                )
            else:
                context.logger.info(
                    "Stripping namespace tokens from metadata for unmanaged deployment"
                )
            zf = process_text_in_zipfile(
                zf,
                functools.partial(
                    inject_namespace,
                    namespace=self.options.namespace_inject,
                    managed=managed,
                    namespaced_org=self.options.namespaced_org,
                    logger=context.logger,
                ),
            )
        if self.options.namespace_strip:
            context.logger.info("Stripping namespace tokens from metadata")
            zf = process_text_in_zipfile(
                zf,
                functools.partial(
                    strip_namespace,
                    namespace=self.options.namespace_strip,
                    logger=context.logger,
                ),
            )

        return zf


class RemoveFeatureParametersTransform(SourceTransform):
    """Source transform that removes Feature Parameters. Intended for use on Unlocked Package builds."""

    options_model = None

    identifier = "remove_feature_parameters"

    def process(self, zf: ZipFile, context: TaskContext) -> ZipFile:
        package_xml = None
        zip_dest = ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
        for name in zf.namelist():
            if name == "package.xml":
                package_xml = zf.open(name)
            elif name.startswith("featureParameters/"):
                # skip feature parameters
                context.logger.info(
                    f"Skipping {name} because Feature Parameters are omitted."
                )
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

    def process(self, zf: ZipFile, context: TaskContext) -> ZipFile:
        context.logger.info(
            "Cleaning meta.xml files of packageVersion elements for deploy"
        )
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

    def process(self, zf: ZipFile, context: TaskContext) -> ZipFile:
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
                context.logger.info(
                    f"Zipping {bundle_relpath} to add to staticresources"
                )

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


class FindReplaceBaseSpec(BaseModel, abc.ABC):
    find: str
    paths: T.Optional[T.List[Path]] = None

    @abc.abstractmethod
    def get_replace_string(self, context: TaskContext) -> str:
        ...


class FindReplaceSpec(FindReplaceBaseSpec):
    replace: str

    def get_replace_string(self, context: TaskContext) -> str:
        return self.replace


class FindReplaceEnvSpec(FindReplaceBaseSpec):
    replace_env: str

    def get_replace_string(self, context: TaskContext) -> str:
        try:
            return os.environ[self.replace_env]
        except KeyError:
            raise TaskOptionsError(
                f"Transform {FindReplaceTransform.identifier} could not get replacement value from environment variable {self.replace_env}"
            )


class FindReplaceIdAPI(str, enum.Enum):
    REST = "rest"
    TOOLING = "tooling"


class FindReplaceIdSpec(FindReplaceBaseSpec):
    replace_record_id_query: str
    api: FindReplaceIdAPI = FindReplaceIdAPI.REST

    def get_replace_string(self, context: TaskContext) -> str:
        org = context.org_config

        if self.api is FindReplaceIdAPI.REST:
            results = org.salesforce_client.query(self.replace_record_id_query)
        else:
            results = org.tooling.query(self.replace_record_id_query)

        if results["totalSize"] != 1:
            raise CumulusCIException(
                f"The find-replace query {self.replace_record_id_query} returned {results['totalSize']} results. Exactly 1 result is required"
            )

        try:
            record_id = results["records"][0]["Id"]
        except KeyError:
            raise CumulusCIException(
                "Results from the replace_record_id_query did not include an 'Id'. Please ensure the 'Id' field is included in your query's SELECT clause."
            )
        return record_id


class FindReplaceCurrentUserSpec(FindReplaceBaseSpec):
    inject_username: bool = True

    def get_replace_string(self, context: TaskContext) -> str:
        if not self.inject_username:  # pragma: no cover
            self.logger.warning(
                "The inject_username value for the find_replace transform is set to False. Skipping transform."
            )
            return self.find
        return context.org_config.username


class FindReplaceTransformOptions(BaseModel):
    patterns: T.List[
        T.Union[
            FindReplaceSpec,
            FindReplaceEnvSpec,
            FindReplaceIdSpec,
            FindReplaceCurrentUserSpec,
        ]
    ]


class FindReplaceTransform(SourceTransform):
    """Source transform that applies one or more find-and-replace patterns."""

    options_model = FindReplaceTransformOptions
    options: FindReplaceTransformOptions

    identifier = "find_replace"

    def __init__(self, options: FindReplaceTransformOptions):
        self.options = options

    def process(self, zf: ZipFile, context: TaskContext) -> ZipFile:
        def process_file(filename: str, content: str) -> T.Tuple[str, str]:
            path = Path(filename)
            for spec in self.options.patterns:
                if not spec.paths or any(
                    parent in path.parents for parent in spec.paths
                ):
                    content = content.replace(
                        spec.find, spec.get_replace_string(context)
                    )

            return (filename, content)

        return process_text_in_zipfile(zf, process_file)


class StripUnwantedComponentsOptions(BaseModel):
    package_xml: str


class StripUnwantedComponentTransform(SourceTransform):
    options_model = StripUnwantedComponentsOptions
    options: StripUnwantedComponentsOptions
    identifier = "strip_unwanted_components"

    def __init__(self, options: StripUnwantedComponentsOptions):
        self.options = options

    def process(self, zf: ZipFile, context: TaskContext) -> ZipFile:
        package_xml_path = os.path.abspath(os.path.expanduser(self.options.package_xml))

        zip_dest = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
        with temporary_dir():
            zf.extractall()
            RemoveSourceComponents(
                os.getcwd(), package_xml_path, api_version=None, logger=context.logger
            )()
            shutil.copy(package_xml_path, "package.xml")
            for root, _, files in os.walk("."):
                for f in files:
                    file = os.path.join(root, f)
                    zip_dest.write(file)

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
            FindReplaceTransform,
            StripUnwantedComponentTransform,
        ]
    }
