import csv
import io
from pathlib import PurePosixPath
from collections import defaultdict, namedtuple

from distutils.version import LooseVersion

from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.core.utils import process_bool_arg
from cumulusci.utils import download_extract_github_from_repo
from cumulusci.utils.xml import metadata_tree
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load
from cumulusci.core.exceptions import DependencyResolutionError

Package = namedtuple("Package", ["repo", "package_name", "namespace", "prefix_release"])


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
            "description": "Process all of the GitHub dependencies of this project and include "
            "their schema in the data dictionary.",
            "default": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        if self.options.get("object_path") is None:
            self.options[
                "object_path"
            ] = f"{self.project_config.project__name} sObject Data Dictionary.csv"

        if self.options.get("field_path") is None:
            self.options[
                "field_path"
            ] = f"{self.project_config.project__name} Field Data Dictionary.csv"

        self.options["include_dependencies"] = process_bool_arg(
            self.options.get("include_dependencies", True)
        )

    def _get_repo_dependencies(self, dependencies=None, include_beta=None):
        deps = []

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

                deps.append(
                    Package(
                        repo,
                        project.get("package", {}).get(
                            "name", ""
                        ),  # FIXME: use owner/repo as default name
                        namespace,
                        project.get("git", {}).get("prefix_release", "release/"),
                    )
                )

                deps.extend(
                    self._get_repo_dependencies(
                        cumulusci_yml.get("project", {}).get("dependencies", [])
                    )
                )

        return deps

    def _run_task(self):
        self.logger.info("Starting data dictionary generation")

        self._init_schema()

        # Find all of our dependencies, if we're processing dependencies.
        dependencies = self.project_config.project__dependencies
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
        if self.options["include_dependencies"]:
            repos += self._get_repo_dependencies(dependencies, include_beta=False)

        for package in repos:
            self._walk_releases(package)

        self._write_results()

    def _init_schema(self):
        """Initialize the structure used for schema storage."""
        self.schema = defaultdict(
            lambda: {"version": None, "fields": defaultdict(lambda: {"version": None})}
        )

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
            version = self._version_from_tag_name(
                release.tag_name, package.prefix_release
            )
            self.logger.info(f"Analyzing {package.package_name} version {version}")

            if "src/objects/" in zip_file.namelist():
                # MDAPI format
                self._process_mdapi_release(zip_file, version, package)

            if "force-app/main/default/objects/" in zip_file.namelist():
                # FIXME: check sfdx-project.json for directories to process.
                # SFDX format
                self._process_sfdx_release(zip_file, version, package)

    def _process_mdapi_release(self, zip_file, version, package):
        """Process an MDAPI ZIP file for objects and fields"""
        for f in zip_file.namelist():
            path = PurePosixPath(f)
            if path.parent == PurePosixPath("src/objects") and path.suffix == ".object":
                sobject_name = path.stem

                self._process_object_element(
                    sobject_name,
                    metadata_tree.fromstring(zip_file.read(f)),
                    version,
                    package,
                )

    def _process_sfdx_release(self, zip_file, version, package):
        """Process an SFDX ZIP file for objects and fields"""
        for f in zip_file.namelist():
            path = PurePosixPath(f)
            if f.startswith("force-app/main/default/objects"):
                if path.suffixes == [".object-meta", ".xml"]:
                    sobject_name = path.name[: -len(".object-meta.xml")]
                    if sobject_name.count("__") == 1:
                        sobject_name = f"{package.namespace}{sobject_name}"

                    self._process_object_element(
                        sobject_name,
                        metadata_tree.fromstring(zip_file.read(f)),
                        version,
                        package,
                    )
                elif path.suffixes == [".field-meta", ".xml"]:
                    # To get the sObject name, we need to remove the `/fields/SomeField.field-meta.xml`
                    # and take the last path component
                    sobject_name = f"{path.parent.parent.stem}"
                    if sobject_name.count("__") == 1:
                        sobject_name = f"{package.namespace}{sobject_name}"

                    self._process_field_element(
                        sobject_name,
                        metadata_tree.fromstring(zip_file.read(f)),
                        version,
                        package,
                    )

    def _process_object_element(self, sobject_name, element, version, package):
        """Process a <CustomObject> metadata entity, whether SFDX or MDAPI"""
        # If this is a custom object, register its presence in this version
        # Don't process custom objects owned by other namespaces.

        # It's fine for Package A to package fields on an object owned by Package B.
        # We'll record the fields on their owning package (B) and the object on its (A).
        if sobject_name.startswith(package.namespace) and sobject_name.endswith("__c"):
            description_elem = getattr(element, "description", None)

            self._set_version_with_props(
                self.schema[sobject_name],
                {
                    "version": version,
                    "label": element.label.text,
                    "description": description_elem.text
                    if description_elem is not None
                    else "",
                    "owning_package": package.package_name,
                },
            )

        # For MDAPI-format elements. No-op on SFDX.
        # No Custom Metadata Types or Platform Events. FIXME: omit Custom Settings.
        if sobject_name.endswith("__c"):
            for field in element.findall("fields"):
                self._process_field_element(sobject_name, field, version, package)

    def _process_field_element(self, sobject_name, field, version, package):
        """Process a field entity, which can be either a <fields> element
        in MDAPI format or a <CustomField> in SFDX"""
        # `element` may be either a `fields` element (in MDAPI)
        # or a `CustomField` (SFDX)
        # If this is a custom field, register its presence in this version
        field_name = f"{package.namespace}{field.fullName.text}"
        # get field help text value
        help_text_elem = field.find("inlineHelpText")
        # get field description text value
        description_text_elem = field.find("description")

        if "__" in field_name:
            field_type = field.type.text
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
                            value.label.text
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
                valid_values = (
                    "->" + field.referenceTo.text
                )  # Note: polymorphic custom fields are not allowed.
            else:
                valid_values = ""

            length = ""

            if not field.find("formula"):
                if field_type == "Text":
                    length = field.length.text
                elif field_type == "Number":
                    length = f"{int(field.precision.text) - int(field.scale.text)}.{field.scale.text}"

            self._set_version_with_props(
                self.schema[sobject_name]["fields"][field_name],
                {
                    "version": version,
                    "help_text": help_text_elem.text
                    if help_text_elem is not None
                    else "",
                    "description": description_text_elem.text
                    if description_text_elem is not None
                    else "",
                    "label": field.label.text,
                    "valid_values": valid_values,
                    "length": length,
                    "type": field_type,
                    "owning_package": package.package_name,
                },
            )

    def _write_results(self):
        """Write the stored schema details to our destination CSVs"""
        with open(self.options["object_path"], "w") as object_file:
            writer = csv.writer(object_file)

            writer.writerow(["Label", "API Name", "Description", "Version Introduced"])

            for sobject_name in self.schema:
                if sobject_name.endswith("__c"):
                    writer.writerow(
                        [
                            self.schema[sobject_name]["label"],
                            sobject_name,
                            self.schema[sobject_name]["description"],
                            f"{self.schema[sobject_name]['owning_package']} {self.schema[sobject_name]['version']}",
                        ]
                    )

        with open(self.options["field_path"], "w") as field_file:
            writer = csv.writer(field_file)

            writer.writerow(
                [
                    "Object API Name",
                    "Field API Name",
                    "Label",
                    "Type",
                    "Help Text",
                    "Description",
                    "Allowed Values",
                    "Length",
                    "Version Introduced",
                    "Version Allowed Values Last Changed",
                    "Version Help Text Last Changed",
                ]
            )

            for sobject_name, sobject_data in self.schema.items():
                for field_name, field_data in sobject_data["fields"].items():
                    valid_values_version = field_data.get(
                        "valid_values_version", field_data["version"]
                    )
                    help_text_version = field_data.get(
                        "help_text_version", field_data["version"]
                    )
                    writer.writerow(
                        [
                            sobject_name,
                            field_name,
                            field_data["label"],
                            field_data["type"],
                            field_data["help_text"],
                            field_data["description"],
                            field_data["valid_values"],
                            field_data["length"],
                            f"{field_data['owning_package']} {field_data['version']}",
                            f"{field_data['owning_package']} {valid_values_version}",
                            f"{field_data['owning_package']} {help_text_version}",
                        ]
                    )

    def _version_from_tag_name(self, tag_name, prefix_release):
        """Parse a release's tag and return a LooseVersion"""
        return LooseVersion(tag_name[len(prefix_release) :])

    def _set_version_with_props(self, in_dict, props):
        """Update our schema storage with this release's details for an entity.
        Preserve the oldest known version, but store the latest metadata for the entity."""
        update_props = props.copy()

        if in_dict["version"] is None:
            pass
        elif props["version"] is None:
            return
        elif in_dict["version"] < props["version"]:
            # We track the last-modified-version of two properties: help_text and valid_values
            # (which can change if the field is a picklist)
            if (
                in_dict.get("valid_values") != props.get("valid_values")
                and props.get("type") == "Picklist"
            ):
                props["valid_values_version"] = update_props["version"]

            if in_dict.get("help_text") != props.get("help_text"):
                props["help_text_version"] = update_props["version"]

            # Update the metadata but not the version.
            del update_props["version"]
        elif in_dict["version"] > props["version"]:
            # Update the version but not the metadata.
            update_props = {"version": update_props["version"]}

        in_dict.update(update_props)
