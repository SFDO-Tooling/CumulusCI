import csv
import io
import xml.etree.ElementTree as ET
import zipfile

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

    def _run_task(self):
        self.schema = defaultdict(
            lambda: {"version": None, "fields": defaultdict(lambda: {"version": None})}
        )

        self._walk_releases()
        self._write_results()

    def _walk_releases(self):
        repo = self.get_repo()
        for release in repo.releases():
            if release.draft or release.prerelease:
                continue

            zip_content = io.BytesIO()
            repo.archive("zipball", zip_content, ref=release.ref)
            zip_file = zipfile.ZipFile(zip_content)
            version = self._version_from_tag_name(tag_name)

            path = zipfile.Path(zip_file, "src/objects")
            if path.exists():
                # MDAPI format
                self._process_mdapi_release(path)

            path = zipfile.Path(zip_file, "force-app/main/default/objects")
            # FIXME: check sfdx-project.json for directories to process.
            if path.exists():
                # SFDX format
                self._process_sfdx_release(path)

    def _process_mdapi_release(self, path):
        for f in path.listdir():
            if f.name.endswith(".object"):
                sobject_name = body[: len(".object")]

                self._process_object_element(
                    sobject_name, ET.fromstring(f.read_text()), version
                )

    def _process_sfdx_release(self, path):
        for obj_dir in path.listdir():
            meta_xml_file = zipfile.Path(
                zip_file,
                f"force-app/main/default/objects/{obj_dir}/{obj_dir}.object-meta.xml",
            )
            self._process_object_element(
                obj_dir, ET.fromstring(meta_xml_file.read_text()), version
            )
            fields_dir = zipfile.Path(
                zip_file, f"force-app/main/default/objects/{obj_dir}/fields"
            )
            for field_file in fields_dir.listdir():
                if field_file.name.endswith("field-meta.xml"):
                    self._process_field_element(
                        obj_dir, ET.fromstring(field_file.read_text()), version
                    )

    def _process_object_element(self, sobject_name, element, tag_name):
        # If this is a custom object, register its presence in this version
        if "__" in sobject_name:
            self._set_version_with_props(
                self.schema[sobject_name],
                {"version": version, "label": element.find("label").text},
            )

            # For MDAPI-format elements. No-op on SFDX.
            for field in element.findall("fields"):
                self._process_field_element(sobject_name, field, version)

    def _process_field_element(sobject_name, field, version):
        # `element` may be either a `fields` element (in MDAPI)
        # or a `CustomField` (SFDX)

        # If this is a custom field, register its presence in this version
        if "__" in field_name:
            self._set_version_with_props(
                self.schema[sobject_name]["fields"][field.find("fullName").text],
                {
                    "version": version,
                    "help_text": field.find("description").text,
                    "field_label": field.find("label").text,
                },
            )

    def _write_results(self):
        with open(self.options["object_path"]) as object_file:
            writer = csv.writer(object_file)

            writer.writerow(["Object Name", "Object Label", "Version Introduced"])

            for sobject_name in self.schema:
                writer.writerow(
                    [
                        sobject_name,
                        self.schema[sobject_name]["label"],
                        self.schema[sobject_name]["version"],
                    ]
                )

        with open(self.options["field_path"]) as field_file:
            writer = csv.writer(field_file)

            writer.writerow(
                ["Object Name", "Field Name", "Field Label", "Version Introduced"]
            )

            for sobject_name, sobject_data in self.schema.items():
                for field_name, field_data in sobject_data["fields"].items():
                    writer.writerow(
                        [
                            sobject_name,
                            field_name,
                            field_data["label"],
                            field_data["version"],
                        ]
                    )

    def _version_from_tag_name(self, tag_name):
        return LooseVersion(
            tag_name[len(self.project_config.project__package__git__prefix_release) :]
        )

    def _set_version_with_props(self, in_dict, props):
        if in_dict["version"] is None or in_dict["version"] < props["version"]:
            in_dict.update(props)
