from typing import Optional

from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement
from cumulusci.core.utils import process_bool_arg


class SetDuplicateRuleStatus(MetadataSingleEntityTransformTask):
    entity = "DuplicateRule"
    task_options = {
        "active": {
            "description": "Boolean value, set the Duplicate Rule to either active or inactive",
            "required": True,
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _transform_entity(
        self, metadata: MetadataElement, api_name: str
    ) -> Optional[MetadataElement]:
        status = "true" if process_bool_arg(self.options["active"]) else "false"
        metadata.find("isActive").text = status

        return metadata
