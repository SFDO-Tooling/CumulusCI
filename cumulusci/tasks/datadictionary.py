import csv
import io
from pathlib import PurePosixPath
from collections import defaultdict, namedtuple

from distutils.version import StrictVersion

from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.utils import download_extract_github_from_repo
from cumulusci.utils.xml import metadata_tree
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load
from cumulusci.core.exceptions import DependencyResolutionError

Package = namedtuple("Package", ["repo", "package_name", "namespace", "prefix_release"])
PackageVersion = namedtuple("PackageVersion", ["package", "version"])
SObjectDetail = namedtuple(
    "SObjectDetail", ["version", "api_name", "label", "description"]
)

FieldDetail = namedtuple(
    "FieldDetail",
    [
        "version",
        "sobject",
        "api_name",
        "label",
        "type",
        "help_text",
        "description",
        "valid_values",
        "length",
    ],
)


class GenerateDataDictionary(BaseGithubTask):
    task_docs = """
    Generate a data dictionary for the project by walking all GitHub releases.
    The data dictionary is output as two CSV files.
    One, in `object_path`, includes the Object Name, Object Label, and Version Introduced,
    with one row per packaged object.
    The other, in `field_path`, includes Object Name, Field Name, Field Label, Field Type,
    Valid Picklist Values (if any) or a Lookup referenced table (if any), Version Introduced.
    Both MDAPI and SFDX format releases are supported. However, only force-app/main/default
    is processed for SFDX projects.
    """

    task_options = {
        "object_path": {
            "description": "Path to a CSV file to contain an sObject-level data dictionary."
        },
        "field_path": {
            "description": "Path to a CSV file to contain an field-level data dictionary."
        },
        "include_dependencies": {
            "description": "Process all of the GitHub dependencies of this project and include their schema in the data dictionary.",
            "default": True,
        },
        "additional_dependencies": {
            "description": "Include schema from additional GitHub repositories that "
            "are not explicit dependencies of this project to build a unified data dictionary. Specify as a list of URLs."
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

        self.options["include_dependencies"] = process_bool_arg(
            self.options.get("include_dependencies", True)
        )

    def _get_repo_dependencies(
        self, dependencies=None, include_beta=None, visited_repos=None
    ):
        """Return a list of Package objects representing all of the GitHub repositories
        in this project's dependency tree. Ignore all non-GitHub dependencies."""
        deps = []
        visited = visited_repos or set()

        for dependency in dependencies:
            if "github" in dependency:
                repo = self.project_config.get_repo_from_url(dependency["github"])[0]
                if repo is None:
                    raise DependencyResolutionError(
                        f"Github repository {dependency['github']} not found or not authorized."
                    )
                _, ref = self.project_config.get_ref_for_dependency(
                    repo, dependency, include_beta
                )

                contents = repo.file_contents("cumulusci.yml", ref=ref)
                cumulusci_yml = cci_safe_load(
                    io.StringIO(contents.decoded.decode("utf-8"))
                )
                project = cumulusci_yml.get("project", {})
                namespace = project.get("package", {}).get("namespace", "")
                if namespace:
                    namespace = f"{namespace}__"
                else:
                    namespace = ""

                if f"{repo.owner}/{repo.name}" in visited:
                    continue

                deps.append(
                    Package(
                        repo,
                        project.get("package", {}).get(
                            "name", f"{repo.owner}/{repo.name}"
                        ),
                        namespace,
                        project.get("git", {}).get("prefix_release", "release/"),
                    )
                )
                visited.add(f"{repo.owner}/{repo.name}")

                deps.extend(
                    self._get_repo_dependencies(
                        cumulusci_yml.get("project", {}).get("dependencies", []),
                        visited_repos=visited,
                    )
                )

        return deps

    def _run_task(self):
        self.logger.info("Starting data dictionary generation")

        self._init_schema()

        # Find all of our dependencies, if we're processing dependencies.
        dependencies = self.project_config.project__dependencies or []
        namespace = self.project_config.project__package__namespace
        if namespace:
            namespace = f"{namespace}__"
        repos = [
            Package(
                self.get_repo(),
                self.project_config.project__package__name,
                namespace,
                self.project_config.project__git__prefix_release,
            )
        ]
        if "additional_dependencies" in self.options:
            repos += self._get_repo_dependencies(
                [
                    {"github": url}
                    for url in process_list_arg(self.options["additional_dependencies"])
                ],
                include_beta=False,
            )
        if self.options["include_dependencies"]:
            repos += self._get_repo_dependencies(dependencies, include_beta=False)

        for package in repos:
            self._walk_releases(package)

        self._write_results()

    def _init_schema(self):
        """Initialize the structure used for schema storage."""
        self.sobjects = defaultdict(lambda: [])
        self.fields = defaultdict(lambda: [])
        self.package_versions = defaultdict(lambda: [])

    def _walk_releases(self, package):
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
                package,
                self._version_from_tag_name(release.tag_name, package.prefix_release),
            )
            self.package_versions[package].append(version.version)
            self.logger.info(
                f"Analyzing {package.package_name} version {version.version}"
            )

            if "src/objects/" in zip_file.namelist():
                # MDAPI format
                self._process_mdapi_release(zip_file, version)

            if "force-app/main/default/objects/" in zip_file.namelist():
                # TODO: check sfdx-project.json for directories to process.
                # SFDX format
                self._process_sfdx_release(zip_file, version)

    def _process_mdapi_release(self, zip_file, version):
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

    def _process_sfdx_release(self, zip_file, version):
        """Process an SFDX ZIP file for objects and fields"""
        for f in zip_file.namelist():
            path = PurePosixPath(f)
            if f.startswith("force-app/main/default/objects"):
                if path.suffixes == [".object-meta", ".xml"]:
                    sobject_name = path.name[: -len(".object-meta.xml")]
                    if sobject_name.count("__") == 1:
                        sobject_name = f"{version.package.namespace}{sobject_name}"

                    self._process_object_element(
                        sobject_name,
                        metadata_tree.fromstring(zip_file.read(f)),
                        version,
                    )
                elif path.suffixes == [".field-meta", ".xml"]:
                    # To get the sObject name, we need to remove the `/fields/SomeField.field-meta.xml`
                    # and take the last path component

                    # Find the sObject metadata file
                    sobject_name = f"{path.parent.parent.stem}"
                    sobject_file = str(
                        path.parent.parent / f"{sobject_name}.object-meta.xml"
                    )

                    if sobject_name.endswith("__mdt") or sobject_name.endswith("__e"):
                        continue

                    # If the object-meta file is locatable, ensure that this is not a Custom Setting.
                    if sobject_file in zip_file.namelist():
                        object_entity = metadata_tree.fromstring(
                            zip_file.read(sobject_file)
                        )
                        if object_entity.find("customSettingsType") is not None:
                            continue

                    if sobject_name.count("__") == 1:
                        sobject_name = f"{version.package.namespace}{sobject_name}"

                    self._process_field_element(
                        sobject_name,
                        metadata_tree.fromstring(zip_file.read(f)),
                        version,
                    )

    def _process_object_element(self, sobject_name, element, version):
        """Process a <CustomObject> metadata entity, whether SFDX or MDAPI"""
        # If this is a custom object, register its presence in this version

        # Don't process Custom Settings.
        if element.find("customSettingsType") is not None:
            return

        # Don't process custom objects owned by other namespaces.
        # It's fine for Package A to package fields on an object owned by Package B.
        # We'll record the fields on their owning package (B) and the object on its (A).
        if sobject_name.startswith(version.package.namespace) and sobject_name.endswith(
            "__c"
        ):
            description_elem = getattr(element, "description", None)

            self.sobjects[sobject_name].append(
                SObjectDetail(
                    version,
                    sobject_name,
                    element.label.text,
                    description_elem.text if description_elem is not None else "",
                )
            )

        # For MDAPI-format elements. No-op on SFDX.
        # No Custom Metadata Types or Platform Events.
        if sobject_name.endswith("__c"):
            for field in element.findall("fields"):
                self._process_field_element(sobject_name, field, version)

    def _process_field_element(self, sobject, field, version):
        """Process a field entity, which can be either a <fields> element
        in MDAPI format or a <CustomField> in SFDX"""
        # `element` may be either a `fields` element (in MDAPI)
        # or a `CustomField` (SFDX)
        # If this is a custom field, register its presence in this version
        field_name = f"{version.package.namespace}{field.fullName.text}"
        # get field help text value
        help_text_elem = field.find("inlineHelpText")
        # get field description text value
        description_text_elem = field.find("description")

        if "__" in field_name:
            field_type = field.type.text
            valid_values = ""

            if field_type in ("Picklist", "MultiselectPicklist"):
                # There's two different ways of storing picklist values
                # (exclusive of Global Value Sets).
                # <picklist> is used prior to API 38.0: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_picklist.htm
                # <valueSet> is used thereafter: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_field_types.htm#meta_type_valueset
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

            length = ""

            if not field.find("formula"):
                if field_type == "Text":
                    length = field.length.text
                elif field_type == "Number":
                    length = f"{int(field.precision.text) - int(field.scale.text)}.{field.scale.text}"

            fd = FieldDetail(
                version,
                sobject,
                field_name,
                field.label.text,
                field_type,
                help_text_elem.text if help_text_elem else "",
                description_text_elem.text if description_text_elem else "",
                valid_values,
                length,
            )
            fully_qualified_name = f"{sobject}.{fd.api_name}"
            self.fields[fully_qualified_name].append(fd)

    def _write_object_results(self, file_handle):
        """Write to the given handle an output CSV containing the data dictionary for sObjects."""
        writer = csv.writer(file_handle)

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
            versions = sorted(
                versions, key=lambda ver: ver.version.version, reverse=True
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

            if sobject_name.endswith("__c"):
                writer.writerow(
                    [
                        last_version.label,
                        sobject_name,
                        last_version.description,
                        f"{first_version.version.package.package_name} {first_version.version.version}",
                        ""
                        if deleted_version is None
                        else f"{first_version.version.package.package_name} {deleted_version}",
                    ]
                )

    def _write_field_results(self, file_handle):
        """Write to the given handle an output CSV containing the data dictionary for fields."""
        writer = csv.writer(file_handle)

        writer.writerow(
            [
                "Object API Name",
                "Field Label",
                "Field API Name",
                "Type",
                "Help Text",
                "Field Description",
                "Allowed Values",
                "Length",
                "Version Introduced",
                "Version Allowed Values Last Changed",
                "Version Help Text Last Changed",
                "Version Deleted",
            ]
        )

        for field_name, field_versions in self.fields.items():
            versions = sorted(
                field_versions, key=lambda ver: ver.version.version, reverse=True
            )
            first_version = versions[-1]
            last_version = versions[0]

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

            writer.writerow(
                [
                    last_version.sobject,
                    last_version.label,
                    last_version.api_name,
                    last_version.type,
                    last_version.help_text,
                    last_version.description,
                    last_version.valid_values,
                    last_version.length,
                    f"{first_version.version.package.package_name} {first_version.version.version}",
                    f"{first_version.version.package.package_name} {valid_values_version.version.version}"
                    if valid_values_version
                    else "",
                    f"{first_version.version.package.package_name} {help_text_version.version.version}"
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

    def _version_from_tag_name(self, tag_name, prefix_release):
        """Parse a release's tag and return a StrictVersion"""
        return StrictVersion(tag_name[len(prefix_release) :])
