from cumulusci.tasks.metadata_etl.base import BaseMetadataSynthesisTask
from cumulusci.tasks import metadata_tree
from cumulusci.utils import process_list_arg


class EncryptAllFields(BaseMetadataSynthesisTask):
    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.blocklist = process_list_arg(self.options.get("blocklist", []))

    def _is_field_encryptable(self, field):
        return (
            field["soapType"] in ["xsd:string", "xsd:dateTime", "xsd:date"]
            and field["type"] != "picklist"
        )

    def _create_sobject_element(self):
        return metadata_tree.fromstring(
            b"""<?xml version="1.0" encoding="UTF-8"?>
    ... <CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    ... </CustomObject>"""
        )

    def _synthesize(self):
        for sobject in self.sf.describe()["sobjects"]:
            sobject_name = sobject["name"]

            root_element = self._create_sobject_element()

            for field in sobject["fields"]:
                field_name = field["name"]
                if (
                    self._is_field_encryptable(field)
                    and f"{sobject_name}.{field_name}" not in self.blocklist
                ):
                    field_element = root_element.append("fields")
                    field_element.append("fullName", text=field_name)
                    field_element.append("encryptionScheme", "ProbabilisticEncryption")

            root_element.write(self.deploy_dir / f"{sobject_name}.object")
