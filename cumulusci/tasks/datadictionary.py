import csv
import io
import os
import xml.etree.ElementTree as ET
import zipfile

from collections import defaultdict
from cumulusci.tasks.github.base import BaseGithubTask
from distutils.version import LooseVersion


class GenerateDataDictionary(BaseGithubTask):
    task_docs = """
    Generate a data dictionary for the project. The data dictionary is output as two CSV files.
    One, in `object_path`, includes the Object Name, Object Label, and Version Introduced,
    with one row per packaged object.
    The other, in `field_path`, includes Object Name, Field Name, Field Label, and Version Introduced.
    """
    task_options = {
        "object_path": {
            "description": "Path to a CSV file to contain an sObject-level data dictionary.",
            "default": "sObject Data Dictionary.csv",
        },
        "field_path": {
            "description": "Path to a CSV file to contain an field-level data dictionary.",
            "default": "Field Data Dictionary.csv",
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.options["object_path"] = (
            self.options.get("object_path") or "sObject Data Dictionary.csv"
        )
        self.options["field_path"] = (
            self.options.get("field_path") or "Field Data Dictionary.csv"
        )

    def _run_task(self):
        self.logger.info("Starting data dictionary generation")

        self._init_schema()
        self._walk_releases()
        self._write_results()

    def _init_schema(self):
        self.schema = defaultdict(
            lambda: {"version": None, "fields": defaultdict(lambda: {"version": None})}
        )

    def _walk_releases(self):
        repo = self.get_repo()

        for release in repo.releases():
            if release.draft or release.prerelease:
                continue

            zip_content = io.BytesIO()
            repo.archive("zipball", zip_content, ref=release.tag_name)
            zip_file = zipfile.ZipFile(zip_content)
            version = self._version_from_tag_name(release.tag_name)

            self.logger.info(f"Analyzing version {version}")

            # The zip file's manifest entries start with a single path component
            # representing the repo's name, owner, and commit SHA.
            # Strip that off so we can inspect paths directly.
            zip_name_list = zip_file.namelist()
            self.zip_prefix = os.path.normpath(zip_name_list[-1]).split(os.sep)[0]
            self.name_list = [
                os.path.join(os.path.sep, *os.path.normpath(p).split(os.sep)[1:]).strip(
                    os.path.sep
                )
                for p in zip_name_list
            ]
            if "src/objects" in self.name_list:
                # MDAPI format
                self._process_mdapi_release(zip_file, version)

            if "force-app/main/default/objects" in self.name_list:
                # FIXME: check sfdx-project.json for directories to process.
                # SFDX format
                self._process_sfdx_release(zip_file, version)

    def _process_mdapi_release(self, zip_file, version):
        for f in self.name_list:
            if f.startswith("src/objects") and f.endswith(".object"):
                sobject_name = os.path.splitext(os.path.split(f)[1])[0]

                self._process_object_element(
                    sobject_name,
                    ET.fromstring(
                        zip_file.read(
                            os.path.join(os.path.sep, self.zip_prefix, f).strip(
                                os.path.sep
                            )
                        )
                    ),
                    version,
                )

    def _process_sfdx_release(self, zip_file, version):
        for obj_file in self.name_list:
            if obj_file.startswith("force-app/main/default/objects"):
                if obj_file.endswith(".object-meta.xml"):
                    sobject_name = os.path.basename(os.path.split(obj_file)[1])[
                        : -len(".object-meta.xml")
                    ]

                    self._process_object_element(
                        sobject_name,
                        ET.fromstring(
                            zip_file.read(
                                os.path.join(
                                    os.path.sep, self.zip_prefix, obj_file
                                ).strip(os.path.sep)
                            )
                        ),
                        version,
                    )
                elif obj_file.endswith(".field-meta.xml"):
                    # To get the sObject name, we need to remove the `/fields/SomeField.field-meta.xml`
                    # and take the last path component
                    sobject_name = os.path.basename(
                        os.path.split(obj_file)[0][: -len("fields")].strip(os.path.sep)
                    )

                    self._process_field_element(
                        sobject_name,
                        ET.fromstring(
                            zip_file.read(
                                os.path.join(
                                    os.path.sep, self.zip_prefix, obj_file
                                ).strip(os.path.sep)
                            )
                        ),
                        version,
                    )

    def _process_object_element(self, sobject_name, element, version):
        # If this is a custom object, register its presence in this version
        namespaces = {"ns": "http://soap.sforce.com/2006/04/metadata"}

        if sobject_name.count("__") == 1:
            help_text_elem = element.find("ns:description", namespaces=namespaces)

            self._set_version_with_props(
                self.schema[sobject_name],
                {
                    "version": version,
                    "label": element.find("ns:label", namespaces=namespaces).text,
                    "help_text": help_text_elem.text
                    if help_text_elem is not None
                    else "",
                },
            )

        # For MDAPI-format elements. No-op on SFDX.
        for field in element.findall("ns:fields", namespaces=namespaces):
            self._process_field_element(sobject_name, field, version)

    def _process_field_element(self, sobject_name, field, version):
        # `element` may be either a `fields` element (in MDAPI)
        # or a `CustomField` (SFDX)
        namespaces = {"ns": "http://soap.sforce.com/2006/04/metadata"}

        # If this is a custom field, register its presence in this version
        field_name = field.find("ns:fullName", namespaces=namespaces).text
        help_text_elem = field.find("ns:inlineHelpText", namespaces=namespaces)

        if "__" in field_name:
            if field.find("ns:type", namespaces=namespaces).text == "Picklist":
                # There's two different ways of storing picklist values
                # (exclusive of Global Value Sets).
                # <picklist> is used prior to API 38.0: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_picklist.htm
                # <valueSet> is used thereafter: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_field_types.htm#meta_type_valueset
                if field.find("ns:valueSet", namespaces=namespaces) is not None:
                    # Determine if this field uses a Global Value Set.
                    value_set = field.find("ns:valueSet", namespaces=namespaces)
                    if (
                        value_set.find("valueSetName", namespaces=namespaces)
                        is not None
                    ):
                        value_set_name = value_set.find(
                            "ns:valueSetName", namespaces=namespaces
                        ).text
                        picklist_values = f"Global Value Set {value_set_name}"
                    else:
                        picklist_values = "; ".join(
                            [
                                x.text
                                for x in value_set.findall(
                                    "ns:valueSetDefinition/ns:value/ns:label",
                                    namespaces=namespaces,
                                )
                            ]
                        )
                elif field.find("ns:picklist", namespaces=namespaces) is not None:
                    picklist_values = "; ".join(
                        [
                            x.text
                            for x in field.findall(
                                "ns:picklist/ns:picklistValues/ns:fullName",
                                namespaces=namespaces,
                            )
                        ]
                    )

            else:
                picklist_values = ""

            self._set_version_with_props(
                self.schema[sobject_name]["fields"][field_name],
                {
                    "version": version,
                    "help_text": help_text_elem.text
                    if help_text_elem is not None
                    else "",
                    "label": field.find("ns:label", namespaces=namespaces).text,
                    "picklist_values": picklist_values,
                },
            )

    def _write_results(self):
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
                            field_data["help_text"],
                            field_data["picklist_values"],
                            field_data["version"],
                        ]
                    )

    def _version_from_tag_name(self, tag_name):
        return LooseVersion(
            tag_name[len(self.project_config.project__git__prefix_release) :]
        )

    def _set_version_with_props(self, in_dict, props):
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
