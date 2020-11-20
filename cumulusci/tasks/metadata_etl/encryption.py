import os
import yaml

from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask
from cumulusci.tasks.metadata_etl.base import BaseMetadataSynthesisTask
from cumulusci.utils import os_friendly_path
from cumulusci.utils.xml import metadata_tree
# from cumulusci.utils import process_list_arg


class EncryptAllFields(BaseSalesforceApiTask, BaseMetadataSynthesisTask):

    task_options = {
        "blocklist_path": {
            "description": "The path to a YAML settings file",
            "required": False,
        }
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        # inline list option version
        # self.blocklist_path = process_list_arg(self.options.get("blocklist", []))

        # yml file path version
        self.blocklist_path = os_friendly_path(
            self.options.get("blocklist_path")
        )
        if self.blocklist_path is None or not os.path.isfile(
            self.blocklist_path
        ):
            raise TaskOptionsError(
                f"File {self.blocklist_path} does not exist"
            )
        print(self.blocklist_path)


    def _is_field_encryptable(self, field):
        return (
            field["soapType"] in ["xsd:string", "xsd:dateTime", "xsd:date"]
            and field["type"] != "picklist"
        )

    def _create_sobject_element(self):
        return metadata_tree.fromstring(
            b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
</CustomObject>"""
        )

    def _synthesize(self):

        with open(self.blocklist_path, "r") as f:
            self.blocklist = yaml.safe_load(f)

        print(self.blocklist)
        print(self.sf.describe()["sobjects"][1].keys())
        for sobject in self.sf.describe()["sobjects"]:
            print(sobject.keys)
            sobject_name = sobject["name"]
            print(sobject_name)

            root_element = self._create_sobject_element()
            for field in sobject["fields"]:
                field_name = field["name"]
                print(field_name)
                if (
                    self._is_field_encryptable(field)
                    and f"{sobject_name}.{field_name}" not in self.blocklist
                ):
                    print(f"{field_name}")
                    field_element = root_element.append("fields")
                    field_element.append("fullName", text=field_name)
                    field_element.append("encryptionScheme", "ProbabilisticEncryption")

            object_dir = self.deploy_dir / "objects"
            if not object_dir.exists():
                object_dir.mkdir()

            (object_dir / f"{sobject_name}.object").write_text(
                root_element.tostring(xml_declaration=True), encoding="utf-8"
            )
