import xml.etree.ElementTree as XML_ET

from datetime import datetime

from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.tasks.salesforce.metadata_etl import MetadataSingleEntityTransformTask


class SetOrgWideDefaults(MetadataSingleEntityTransformTask):
    entity = "CustomObject"
    task_options = {
        "org_wide_defaults": {
            "description": "The target Organization-Wide Defaults, "
            "organized as a list with each element containing the keys api_name, "
            "internal_sharing_model, and external_sharing_model.",
            "required": True,
        },
        "timeout": {
            "description": "The max amount of time to wait in seconds",
            "required": False,
            "default": 600,
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _init_options(self, kwargs):
        self.task_config.options["api_names"] = "dummy"
        super()._init_options(kwargs)
        self.api_names = [
            self._inject_namespace(elem["api_name"])
            for elem in self.options["org_wide_defaults"]
        ]
        self.options["timeout"] = int(self.options.get("timeout", 600))

        self.owds = {}
        for elem in self.options["org_wide_defaults"]:
            if "api_name" not in elem or (
                "internal_sharing_model" not in elem
                and "external_sharing_model" not in elem
            ):
                raise TaskOptionsError(
                    "The object api_name and at least one of "
                    "internal_sharing_model and external_sharing_model is required."
                )
            self.owds[self._inject_namespace(elem["api_name"])] = {
                "internal_sharing_model": elem.get("internal_sharing_model"),
                "external_sharing_model": elem.get("external_sharing_model"),
            }

    def _post_deploy(self, result):
        if result == "Success":
            super()._post_deploy(result)
            self.logger.info(f"Waiting for sharing enablement to complete.")
            self.time_start = datetime.now()
            self._poll()
            self.logger.info(f"Sharing enablement is complete.")

    def _transform_entity(self, metadata, api_name):
        desired_internal_model = self.owds[api_name].get("internal_sharing_model")
        desired_external_model = self.owds[api_name].get("external_sharing_model")

        if desired_external_model:
            external_model = metadata.findall(
                f".//sf:externalSharingModel", self.namespaces
            )
            if not external_model:
                external_model = [
                    XML_ET.SubElement(
                        metadata.getroot(),
                        "{%s}externalSharingModel" % (self.namespaces.get("sf")),
                    )
                ]
            external_model[0].text = desired_external_model

        if desired_internal_model:
            internal_model = metadata.findall(f".//sf:sharingModel", self.namespaces)
            if not internal_model:
                internal_model = [
                    XML_ET.SubElement(
                        metadata.getroot(),
                        "{%s}sharingModel" % (self.namespaces.get("sf")),
                    )
                ]
            internal_model[0].text = desired_internal_model

        return metadata

    def _poll_action(self):
        elapsed = datetime.now() - self.time_start
        if elapsed.total_seconds() > self.options["timeout"]:
            raise CumulusCIException(
                f'Sharing enablement not completed after {self.options["timeout"]} seconds'
            )

        for sobject in self.owds:
            result = self.sf.query(
                f"SELECT ExternalSharingModel, InternalSharingModel "
                f"FROM EntityDefinition "
                f"WHERE QualifiedApiName = '{sobject}'"
            )
            if result["totalSize"] == 1:
                record = result["records"][0]
                if (
                    self.owds[sobject]["internal_sharing_model"]
                    and record["InternalSharingModel"]
                    != self.owds[sobject]["internal_sharing_model"]
                ) or (
                    self.owds[sobject]["external_sharing_model"]
                    and record["ExternalSharingModel"]
                    != self.owds[sobject]["external_sharing_model"]
                ):
                    return
            else:
                raise CumulusCIException("Unable to determine sharing model")

        self.poll_complete = True
