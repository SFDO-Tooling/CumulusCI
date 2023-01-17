import csv
from collections import defaultdict
from pathlib import PurePosixPath
from typing import List, Optional, Union
from unittest.mock import Mock
from zipfile import ZipFile

from github3.repos.repo import Repository
from pydantic import BaseModel

from cumulusci.core.dependencies.dependencies import (
    Dependency,
    GitHubDynamicDependency,
    parse_dependencies,
)
from cumulusci.core.dependencies.github import (
    get_package_data,
    get_remote_project_config,
    get_repo,
)
from cumulusci.core.dependencies.resolvers import get_static_dependencies
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.utils import download_extract_github_from_repo
from cumulusci.utils.version_strings import LooseVersion
from cumulusci.utils.xml import metadata_tree


class Package(BaseModel):
    repo: Optional[Union[Repository, Mock]]
    package_name: str
    namespace: str
    prefix_release: str

    def __hash__(self) -> int:
        return self.repo.__hash__()

    class Config:
        arbitrary_types_allowed = True


class PackageVersion(BaseModel):
    package: Package
    version: LooseVersion

    class Config:
        arbitrary_types_allowed = True


class SObjectDetail(BaseModel):
    version: PackageVersion
    api_name: str
    label: str
    description: str


class FieldDetail(BaseModel):
    version: PackageVersion
    sobject: str
    api_name: str
    label: str
    type: str
    help_text: str
    description: str
    valid_values: str


# "Version number" used to represent a prerelease.
PRERELEASE_SIGIL = LooseVersion("100000001.0")


class GenerateDataDictionary(BaseGithubTask):
    task_docs = """
    Generate a data dictionary for the project by walking all GitHub releases.
    The data dictionary is output as two CSV files.
    One, in `object_path`, includes

    - Object Label
    - Object API Name
    - Object Description
    - Version Introduced

    with one row per packaged object.

    The other, in `field_path`, includes

    - Object Label
    - Object API Name
    - Field Label
    - Field API Name
    - Field Type
    - Valid Picklist Values
    - Help Text
    - Field Description
    - Version Introduced
    - Version Picklist Values Last Changed
    - Version Help Text Last Changed

    Both MDAPI and SFDX format releases are supported.
    """

    task_options = {
        "object_path": {
            "description": "Path to a CSV file to contain an sObject-level data dictionary."
        },
        "field_path": {
            "description": "Path to a CSV file to contain an field-level data dictionary."
        },
        "include_dependencies": {
            "description": "Process all of the GitHub dependencies of this project and "
            "include their schema in the data dictionary.",
            "default": True,
        },
        "additional_dependencies": {
            "description": "Include schema from additional GitHub repositories that "
            "are not explicit dependencies of this project to build a unified data dictionary. "
            "Specify as a list of dicts as in project__dependencies in cumulusci.yml. Note: only "
            "repository dependencies are supported."
        },
        "include_prerelease": {
            "description": "Treat the current branch as containing prerelease schema, "
            "and included it as Prerelease in the data dictionary. NOTE: this option "
            "cannot be used with `additional_dependencies` or `include_dependencies`."
        },
        "include_protected_schema": {
            "description": "Include Custom Objects, Custom Settings, and Custom Metadata "
            "Types that are marked as Protected. Defaults to False."
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        if self.options.get("object_path") is None:
            self.options[
                "object_path"
            ] = f"{self.project_config.project__name} Objects.csv"

        if self.options.get("field_path") is None:
            self.options[
                "field_path"
            ] = f"{self.project_config.project__name} Fields.csv"

        include_dependencies = self.options.get("include_dependencies")
        self.options["include_dependencies"] = process_bool_arg(
            True if include_dependencies is None else include_dependencies
        )

        if "additional_dependencies" in self.options:
            additional_deps = parse_dependencies(
                self.options["additional_dependencies"]
            )
            if not all(isinstance(d, GitHubDynamicDependency) for d in additional_deps):
                raise TaskOptionsError(
                    "Only GitHub dependencies are currently supported."
                )

        self.options["include_prerelease"] = process_bool_arg(
            self.options.get("include_prerelease") or False
        )

        if self.options["include_prerelease"]:
            if self.options.get("additional_dependencies"):
                raise TaskOptionsError(
                    "The additional_dependencies option cannot be used with include_prerelease."
                )

            if self.options["include_dependencies"]:
                self.logger.info(
                    "Setting include_prerelease prohibits include_dependencies; setting include_dependencies to False"
                )
                self.options["include_dependencies"] = False

        self.options["include_protected_schema"] = process_bool_arg(
            self.options.get("include_protected_schema") or False
        )

    def _get_repo_dependencies(
        self, dependencies: List[GitHubDynamicDependency]
    ) -> List[Package]:
        """Return a list of Package objects representing all of the GitHub repositories
        in this project's dependency tree. Ignore all non-GitHub dependencies."""
        github_deps = set()
        packages = []

        def log_github(some_dep: Dependency):
            if isinstance(some_dep, GitHubDynamicDependency):
                github_deps.add(some_dep)

            return True

        _ = get_static_dependencies(
            self.project_config,
            dependencies,
            resolution_strategy="production",
            filter_function=log_github,
        )

        for dependency in github_deps:
            repo = get_repo(dependency.github, self.project_config)
            config = get_remote_project_config(repo, dependency.ref)
            package_name, namespace = get_package_data(config)
            packages.append(
                Package(
                    repo=repo,
                    package_name=package_name,
                    namespace=f"{namespace}__" if namespace else "",
                    prefix_release=config.project__git__prefix_release or "release/",
                )
            )

        return packages

    def _run_task(self):
        self.logger.info("Starting data dictionary generation")

        self._init_schema()

        namespace = self.project_config.project__package__namespace
        if namespace:
            namespace = f"{namespace}__"
        repos = [
            Package(
                repo=self.get_repo(),
                package_name=self.project_config.project__package__name,
                namespace=namespace,
                prefix_release=self.project_config.project__git__prefix_release,
            )
        ]

        # Find all of our dependencies, if we're processing dependencies.
        dependencies = []
        if (
            self.options["include_dependencies"]
            and self.project_config.project__dependencies
        ):
            parsed_deps = parse_dependencies(self.project_config.project__dependencies)
            dependencies.extend(
                d for d in parsed_deps if isinstance(d, GitHubDynamicDependency)
            )
        if "additional_dependencies" in self.options:
            # init_options() required these to all be GitHubDynamicDependencies
            dependencies.extend(
                parse_dependencies(self.options["additional_dependencies"])
            )

        if dependencies:
            repos.extend(self._get_repo_dependencies(dependencies))

        for package in repos:
            self._walk_releases(package)

        self._write_results()

    def _init_schema(self):
        """Initialize the structure used for schema storage."""
        self.sobjects = defaultdict(list)
        self.fields = defaultdict(list)
        self.package_versions = defaultdict(list)
        self.omit_sobjects = set()

    def _walk_releases(self, package: Package):
        """Traverse all of the releases in this project's repository and process
        each one matching our tag (not draft/prerelease) to generate the data dictionary."""
        for release in package.repo.releases():
            # Skip this release if any are true:
            # It is a draft release
            # It is prerelease (managed beta)
            # This release's tag does not have the expected prefix,
            # meaning we don't know its version number
            if (
                release.draft
                or release.prerelease
                or not release.tag_name.startswith(package.prefix_release)
            ):
                continue

            zip_file = download_extract_github_from_repo(
                package.repo, ref=release.tag_name
            )
            version = PackageVersion(
                package=package,
                version=self._version_from_tag_name(
                    release.tag_name, package.prefix_release
                ),
            )
            self.package_versions[package].append(version.version)
            self.logger.info(
                f"Analyzing {package.package_name} version {version.version}"
            )

            self._process_zipfile(zip_file, version)

        # If we are asked to process a prerelease, do so.
        if self.options["include_prerelease"]:
            # package.repo is guaranteed to be our repo (via _init_options())
            zip_file = download_extract_github_from_repo(
                package.repo, ref=self.project_config.repo_branch
            )
            version = PackageVersion(
                package=package,
                version=PRERELEASE_SIGIL,
            )
            self.package_versions[package].append(version.version)
            self.logger.info(
                f"Analyzing {package.package_name} prerelease from {self.project_config.repo_branch}"
            )

            self._process_zipfile(zip_file, version)

    def _process_zipfile(self, zip_file: ZipFile, version: PackageVersion):
        if "src/objects/" in zip_file.namelist():
            # MDAPI format
            self._process_mdapi_release(zip_file, version)
        elif "sfdx-project.json" in zip_file.namelist():
            # SFDX format
            # Note: we check MDAPI first, because many
            # CumulusCI projects contain an sfdx-project.json
            # along with MDAPI source.
            self._process_sfdx_release(zip_file, version)

    def _process_mdapi_release(self, zip_file: ZipFile, version: PackageVersion):
        """Process an MDAPI ZIP file for objects and fields"""
        for f in zip_file.namelist():
            path = PurePosixPath(f)
            if path.parent == PurePosixPath("src/objects") and path.suffix == ".object":
                sobject_name = path.stem
                if sobject_name.count("__") == 1:
                    sobject_name = f"{version.package.namespace}{sobject_name}"

                self._process_object_element(
                    sobject_name, metadata_tree.fromstring(zip_file.read(f)), version
                )

    def _should_process_object(
        self,
        namespace: str,
        sobject_name: str,
        element: Optional[metadata_tree.MetadataElement],
    ):
        """Determine if we should track this object in the object dictionary.
        Fields may be included regardless.

        We don't process custom objects owned by other namespaces.
        It's fine for Package A to package fields on an object owned by Package B.
        We'll record the fields on their owning package (B) and the object on its (A)."""

        return (
            (
                sobject_name.endswith("__c")
                or sobject_name.endswith("__mdt")
                or sobject_name.endswith("__e")
                or sobject_name.count("__") == 0
            )
            and sobject_name.startswith(namespace)
            and (
                not self._is_protected_object(element)
                or self.options["include_protected_schema"]
            )
        )

    def _should_process_object_fields(
        self, sobject_name: str, element: Optional[metadata_tree.MetadataElement]
    ) -> bool:
        """Determine if we should track fields from this object in the field dictionary.
        The object itself may or may not be included.

        We will track any field on a custom object, Platform Event,
        Custom Setting, Custom Metadata Type, or standard entity.
        We will not track any object's fields that are protected
        in this package version."""
        return (
            sobject_name.endswith("__c")
            or sobject_name.endswith("__mdt")
            or sobject_name.endswith("__e")
            or sobject_name.count("__") == 0
        ) and (
            not self._is_protected_object(element)
            or self.options["include_protected_schema"]
        )

    def _is_protected_object(
        self, element: Optional[metadata_tree.MetadataElement]
    ) -> bool:
        if not element:
            return False

        # customSettingsVisibility is used in older API versions.
        visibility_elem = element.find("customSettingsVisibility")
        if visibility_elem:
            return visibility_elem.text != "Public"

        visibility_elem = element.find("visibility")
        if visibility_elem:
            return visibility_elem.text != "Public"

        return False

    def _process_sfdx_release(self, zip_file: ZipFile, version: PackageVersion):
        """Process an SFDX ZIP file for objects and fields"""
        for f in zip_file.namelist():
            path = PurePosixPath(f)
            # Be flexible about processing directories in SFDX context.
            # This may not be optimal if the repo contains multiple
            # 2GP package subdirectories.
            if "objects/" in f and not f.startswith("unpackaged/"):
                if path.suffixes == [".object-meta", ".xml"]:
                    sobject_name = path.name[: -len(".object-meta.xml")]
                    if sobject_name.count("__") == 1:
                        sobject_name = f"{version.package.namespace}{sobject_name}"

                    element = metadata_tree.fromstring(zip_file.read(f))

                    if self._should_process_object(
                        version.package.namespace, sobject_name, element
                    ):
                        self._process_object_element(sobject_name, element, version)
                    else:
                        # If this is an object type from which we shouldn't process any fields,
                        # track it in omit_sobjects so we can drop any fields later if we don't have
                        # the right information at time of processing.

                        # Note that the owning object may be in a dependency package, so we won't find it below.
                        if not self._should_process_object_fields(
                            sobject_name, element
                        ):
                            self.omit_sobjects.add(sobject_name)
                elif path.suffixes == [".field-meta", ".xml"]:
                    # To get the sObject name, we need to remove the `/fields/SomeField.field-meta.xml`
                    # and take the last path component

                    # Find the sObject metadata file
                    sobject_name = f"{path.parent.parent.stem}"
                    sobject_file = str(
                        path.parent.parent / f"{sobject_name}.object-meta.xml"
                    )
                    if sobject_name.count("__") == 1:
                        sobject_name = f"{version.package.namespace}{sobject_name}"

                    # If the object-meta file is locatable, load it so we can check
                    # if this is a Custom Setting.
                    if sobject_file in zip_file.namelist():
                        object_entity = metadata_tree.fromstring(
                            zip_file.read(sobject_file)
                        )
                    else:
                        object_entity = None

                    if self._should_process_object_fields(sobject_name, object_entity):
                        self._process_field_element(
                            sobject_name,
                            metadata_tree.fromstring(zip_file.read(f)),
                            version,
                        )

    def _process_object_element(
        self,
        sobject_name: str,
        element: metadata_tree.MetadataElement,
        version: PackageVersion,
    ):
        """Process a <CustomObject> metadata entity, whether SFDX or MDAPI"""
        description_elem = getattr(element, "description", None)

        # SFDX release can check this before calling us, but MDAPI can't.
        if self._should_process_object(
            version.package.namespace, sobject_name, element
        ):
            if description_elem and description_elem.text:
                description = description_elem.text
            else:
                description = ""

            self.sobjects[sobject_name].append(
                SObjectDetail(
                    version=version,
                    api_name=sobject_name,
                    label=element.label.text,
                    description=description,
                )
            )

        # For MDAPI-format elements. No-op on SFDX.
        if self._should_process_object_fields(sobject_name, element):
            for field in element.findall("fields"):
                self._process_field_element(sobject_name, field, version)
        else:
            # If this is an object type from which we shouldn't process any fields,
            # track it in omit_sobjects so we can drop any fields later if we don't have
            # the right information at time of processing.

            # Note that the owning object may be in a dependency package, so we won't find it otherwise.
            self.omit_sobjects.add(sobject_name)

    def _process_field_element(
        self,
        sobject: str,
        field: metadata_tree.MetadataElement,
        version: PackageVersion,
    ):
        """Process a field entity, which can be either a <fields> element
        in MDAPI format or a <CustomField> in SFDX"""
        # `element` may be either a `fields` element (in MDAPI)
        # or a `CustomField` (SFDX)
        # If this is a custom field, register its presence in this version
        if "__" in field.fullName.text:
            field_name = f"{version.package.namespace}{field.fullName.text}"
            # get field help text value
            help_text_elem = field.find("inlineHelpText")
            # get field description text value
            description_text_elem = field.find("description")

            field_type = field.type.text
            valid_values = ""

            length = ""

            if not field.find("formula"):
                if field_type in ["Text", "LongTextArea"]:
                    length = f" ({field.length.text})"
                elif field_type == "Number":
                    length = f" ({int(field.precision.text) - int(field.scale.text)}.{field.scale.text})"

            if field_type in ("Picklist", "MultiselectPicklist"):
                # There's two different ways of storing picklist values
                # (exclusive of Global Value Sets).
                # <picklist> is used prior to API 38.0:
                # https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_picklist.htm
                # <valueSet> is used thereafter:
                # https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_field_types.htm#meta_type_valueset
                if field.find("valueSet") is not None:
                    # Determine if this field uses a Global Value Set.
                    value_set = field.valueSet
                    if value_set.find("valueSetName") is not None:
                        value_set_name = value_set.find("valueSetName").text
                        valid_values = f"Global Value Set {value_set_name}"
                    else:
                        valueSetDefinition = value_set.valueSetDefinition
                        labels = [
                            value.find("label").text
                            if value.find("label")
                            else value.fullName.text
                            for value in valueSetDefinition.findall("value")
                        ]

                        valid_values = "; ".join(labels)
                elif field.find("picklist") is not None:
                    picklist = field.picklist
                    names = [
                        value.fullName.text
                        for value in picklist.findall("picklistValues")
                    ]

                    valid_values = "; ".join(names)
            elif field_type == "Lookup":
                target_sobject = field.referenceTo.text
                if target_sobject.count("__") == 1:
                    target_sobject = f"{version.package.namespace}{target_sobject}"
                field_type = f"Lookup to {target_sobject}"
                # Note: polymorphic custom fields are not allowed.
            elif field_type == "MasterDetail":
                target_sobject = field.referenceTo.text
                if target_sobject.count("__") == 1:
                    target_sobject = f"{version.package.namespace}{target_sobject}"
                field_type = f"Master-Detail Relationship to {target_sobject}"
                # Note: polymorphic custom fields are not allowed.

            if help_text_elem and help_text_elem.text:
                help_text = help_text_elem.text
            else:
                help_text = ""

            if description_text_elem and description_text_elem.text:
                description = description_text_elem.text
            else:
                description = ""

            fd = FieldDetail(
                version=version,
                sobject=sobject,
                api_name=field_name,
                label=field.label.text,
                type=f"{field_type}{length}",
                help_text=help_text,
                description=description,
                valid_values=valid_values,
            )
            fully_qualified_name = f"{sobject}.{fd.api_name}"
            self.fields[fully_qualified_name].append(fd)

    @staticmethod
    def _get_version_name(package_version: PackageVersion) -> str:
        if package_version.version == PRERELEASE_SIGIL:
            return "Prerelease"
        return str(package_version.version)

    def _write_object_results(self, file_handle):
        """Write to the given handle an output CSV containing the data dictionary for sObjects."""
        writer = csv.writer(file_handle, quoting=csv.QUOTE_ALL)

        writer.writerow(
            [
                "Object Label",
                "Object API Name",
                "Object Description",
                "Version Introduced",
                "Version Deleted",
            ]
        )

        for sobject_name, versions in self.sobjects.items():
            # object_version.version.version yields the LooseVersion
            # of the package version of this object version.
            versions = sorted(
                versions,
                key=lambda object_version: object_version.version.version,
                reverse=True,
            )
            first_version = versions[-1]
            last_version = versions[0]

            # Locate the version, if any, where this object was deleted.
            package_versions = sorted(
                self.package_versions[last_version.version.package]
            )
            if last_version.version.version != package_versions[-1]:
                deleted_version = package_versions[
                    package_versions.index(last_version.version.version) + 1
                ]
            else:
                deleted_version = None

            writer.writerow(
                [
                    last_version.label,
                    sobject_name,
                    last_version.description,
                    f"{first_version.version.package.package_name} {self._get_version_name(first_version.version)}",
                    ""
                    if deleted_version is None
                    else f"{first_version.version.package.package_name} {deleted_version}",
                ]
            )

    def _write_field_results(self, file_handle):
        """Write to the given handle an output CSV containing the data dictionary for fields."""
        writer = csv.writer(file_handle, quoting=csv.QUOTE_ALL)

        writer.writerow(
            [
                "Object Label",
                "Object API Name",
                "Field Label",
                "Field API Name",
                "Type",
                "Picklist Values",
                "Help Text",
                "Field Description",
                "Version Introduced",
                "Version Picklist Values Last Changed",
                "Version Help Text Last Changed",
                "Version Deleted",
            ]
        )

        for _, field_versions in self.fields.items():
            # field_version.version.version yields the LooseVersion of the package version for this field version.
            versions = sorted(
                field_versions,
                key=lambda field_version: field_version.version.version,
                reverse=True,
            )
            first_version = versions[-1]
            last_version = versions[0]

            if last_version.sobject in self.omit_sobjects:
                continue

            # Locate the last versions where the valid values and the help text changed.
            valid_values_version = None
            for (index, version) in enumerate(versions[1:]):
                if version.valid_values != last_version.valid_values:
                    valid_values_version = versions[index]
                    break

            help_text_version = None
            for (index, version) in enumerate(versions[1:]):
                if version.help_text != last_version.help_text:
                    help_text_version = versions[index]
                    break

            # Locate the version, if any, where this field was deleted.
            package_versions = sorted(
                self.package_versions[last_version.version.package]
            )
            if last_version.version.version != package_versions[-1]:
                deleted_version = package_versions[
                    package_versions.index(last_version.version.version) + 1
                ]
            else:
                deleted_version = None

            # Find the sObject name, if possible, for this field.
            if last_version.sobject in self.sobjects:
                sobject_label = sorted(
                    self.sobjects[last_version.sobject],
                    key=lambda ver: ver.version.version,
                    reverse=True,
                )[0].label
            else:
                sobject_label = last_version.sobject

            writer.writerow(
                [
                    sobject_label,
                    last_version.sobject,
                    last_version.label,
                    last_version.api_name,
                    last_version.type,
                    last_version.valid_values,
                    last_version.help_text,
                    last_version.description,
                    f"{first_version.version.package.package_name} {self._get_version_name(first_version.version)}",
                    f"{first_version.version.package.package_name} {self._get_version_name(valid_values_version.version)}"
                    if valid_values_version
                    else "",
                    f"{first_version.version.package.package_name} {self._get_version_name(help_text_version.version)}"
                    if help_text_version
                    else "",
                    ""
                    if deleted_version is None
                    else f"{first_version.version.package.package_name} {deleted_version}",
                ]
            )

    def _write_results(self):
        """Write the stored schema details to our destination CSVs"""
        with open(self.options["object_path"], "w") as object_file:
            self._write_object_results(object_file)

        with open(self.options["field_path"], "w") as field_file:
            self._write_field_results(field_file)

    def _version_from_tag_name(
        self, tag_name: str, prefix_release: str
    ) -> LooseVersion:
        """Parse a release's tag and return a LooseVersion"""
        return LooseVersion(tag_name[len(prefix_release) :])
