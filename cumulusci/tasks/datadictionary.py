import csv
from pathlib import PurePosixPath
from collections import defaultdict

from distutils.version import LooseVersion


from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.utils import download_extract_github_from_repo
from cumulusci.utils.xml import metadata_tree


class GenerateDataDictionary(BaseGithubTask):
    task_docs = """
    Generate a data dictionary for the project by walking all GitHub releases.
    The data dictionary is output as two CSV files.
    One, in `object_path`, includes the Object Name, Object Label, and Version Introduced,
    with one row per packaged object.
    The other, in `field_path`, includes Object Name, Field Name, Field Label, Field Type,
    Picklist Values (if any), Version Introduced.
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
        "release_prefix": {
            "description": "The tag prefix used for releases.",
            "required": True,
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

    def _run_task(self):
        self.logger.info("Starting data dictionary generation")

        self._init_schema()
        self._walk_releases()
        self._write_results()

    def _init_schema(self):
        """Initialize the structure used for schema storage."""
        self.schema = defaultdict(
            lambda: {"version": None, "fields": defaultdict(lambda: {"version": None})}
        )

    def _walk_releases(self):
        """Traverse all of the releases in this project's repository and process
        each one matching our tag (not draft/prerelease) to generate the data dictionary."""
        repo = self.get_repo()

        for release in repo.releases():
            # Skip this release if any are true:
            # It is a draft release
            # It is prerelease (managed beta)
            # This release's tag does not have the expected prefix,
            # meaning we don't know its version number
            if (
                release.draft
                or release.prerelease
                or not release.tag_name.startswith(self.options["release_prefix"])
            ):
                continue

            zip_file = download_extract_github_from_repo(repo, ref=release.tag_name)
            version = self._version_from_tag_name(release.tag_name)
            self.logger.info(f"Analyzing version {version}")

            if "src/objects/" in zip_file.namelist():
                # MDAPI format
                self._process_mdapi_release(zip_file, version)

            if "force-app/main/default/objects/" in zip_file.namelist():
                # FIXME: check sfdx-project.json for directories to process.
                # SFDX format
                self._process_sfdx_release(zip_file, version)

    def _process_mdapi_release(self, zip_file, version):
        """Process an MDAPI ZIP file for objects and fields"""
        for f in zip_file.namelist():
            path = PurePosixPath(f)
            if path.parent == PurePosixPath("src/objects") and path.suffix == ".object":
                sobject_name = path.stem

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

                    self._process_object_element(
                        sobject_name,
                        metadata_tree.fromstring(zip_file.read(f)),
                        version,
                    )
                elif path.suffixes == [".field-meta", ".xml"]:
                    # To get the sObject name, we need to remove the `/fields/SomeField.field-meta.xml`
                    # and take the last path component
                    sobject_name = path.parent.parent.stem

                    self._process_field_element(
                        sobject_name,
                        metadata_tree.fromstring(zip_file.read(f)),
                        version,
                    )

    def _process_object_element(self, sobject_name, element, version):
        """Process a <CustomObject> metadata entity, whether SFDX or MDAPI"""
        # If this is a custom object, register its presence in this version
        if sobject_name.count("__") == 1:
            help_text_elem = element.description

            self._set_version_with_props(
                self.schema[sobject_name],
                {
                    "version": version,
                    "label": element.label.text,
                    "help_text": help_text_elem.text
                    if help_text_elem is not None
                    else "",
                },
            )

        # For MDAPI-format elements. No-op on SFDX.
        for field in element.findall("fields"):
            self._process_field_element(sobject_name, field, version)

    def _process_field_element(self, sobject_name, field, version):
        """Process a field entity, which can be either a <fields> element
        in MDAPI format or a <CustomField> in SFDX"""
        # `element` may be either a `fields` element (in MDAPI)
        # or a `CustomField` (SFDX)
        # If this is a custom field, register its presence in this version
        field_name = field.fullName.text
        help_text_elem = field.find("inlineHelpText")

        if "__" in field_name:
            field_type = field.type.text
            if field_type == "Picklist":
                # There's two different ways of storing picklist values
                # (exclusive of Global Value Sets).
                # <picklist> is used prior to API 38.0: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_picklist.htm
                # <valueSet> is used thereafter: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_field_types.htm#meta_type_valueset
                if field.find("valueSet") is not None:
                    # Determine if this field uses a Global Value Set.
                    value_set = field.valueSet
                    if value_set.find("valueSetName") is not None:
                        value_set_name = value_set.find("valueSetName").text
                        picklist_values = f"Global Value Set {value_set_name}"
                    else:
                        valueSetDefinition = value_set.valueSetDefinition
                        labels = [
                            value.label.text
                            for value in valueSetDefinition.findall("value")
                        ]

                        picklist_values = "; ".join(labels)
                elif field.find("picklist") is not None:
                    picklist = field.picklist
                    names = [
                        value.fullName.text
                        for value in picklist.findall("picklistValues")
                    ]

                    picklist_values = "; ".join(names)

            else:
                picklist_values = ""

            self._set_version_with_props(
                self.schema[sobject_name]["fields"][field_name],
                {
                    "version": version,
                    "help_text": help_text_elem.text
                    if help_text_elem is not None
                    else "",
                    "label": field.label.text,
                    "picklist_values": picklist_values,
                    "type": field_type,
                },
            )

    def _write_results(self):
        """Write the stored schema details to our destination CSVs"""
        with open(self.options["object_path"], "w") as object_file:
            writer = csv.writer(object_file)

            writer.writerow(
                [
                    "Object Name",
                    "Object Label",
                    "Object Description",
                    "Version Introduced",
                ]
            )

            for sobject_name in self.schema:
                if sobject_name.count("__") == 1:
                    writer.writerow(
                        [
                            sobject_name,
                            self.schema[sobject_name]["label"],
                            self.schema[sobject_name]["help_text"],
                            self.schema[sobject_name]["version"],
                        ]
                    )

        with open(self.options["field_path"], "w") as field_file:
            writer = csv.writer(field_file)

            writer.writerow(
                [
                    "Object Name",
                    "Field Name",
                    "Field Label",
                    "Type",
                    "Field Help Text",
                    "Picklist Values",
                    "Version Introduced",
                ]
            )

            for sobject_name, sobject_data in self.schema.items():
                for field_name, field_data in sobject_data["fields"].items():
                    writer.writerow(
                        [
                            sobject_name,
                            field_name,
                            field_data["label"],
                            field_data["type"],
                            field_data["help_text"],
                            field_data["picklist_values"],
                            field_data["version"],
                        ]
                    )

    def _version_from_tag_name(self, tag_name):
        """Parse a release's tag and return a LooseVersion"""
        return LooseVersion(tag_name[len(self.options["release_prefix"]) :])

    def _set_version_with_props(self, in_dict, props):
        """Update our schema storage with this release's details for an entity.
        Preserve the oldest known version, but store the latest metadata for the entity."""
        # We want to persist the oldest known version, but show the most recent
        # label and help text in the data dictionary.
        update_props = props.copy()

        if in_dict["version"] is None:
            pass
        elif props["version"] is None:
            return
        elif in_dict["version"] < props["version"]:
            # Update the metadata but not the version.
            del update_props["version"]
        elif in_dict["version"] > props["version"]:
            # Update the version but not the metadata.
            update_props = {"version": update_props["version"]}

        in_dict.update(update_props)
