import json
from pathlib import Path

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils.schema_utils import Schema
from cumulusci.core.utils import process_list_arg


class DescribeOrg(BaseSalesforceApiTask):
    task_options = {
        "objects": {
            "description": "Which objects to fetch schema information for. Default to all (more than 800!)",
            "default": (),
        },
        "fields": {
            "description": "Which fields to fetch schema information for. Defaults to all (thouands!)",
            "default": (),
        },
        "properties": {
            "description": "Which properties to fetch schema information for",
            "default": (),
        },
        "filename": {
            "description": "Filename to put the JSON data into.",
            "default": "org_schema.json",
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.incl_objects = process_list_arg(self.options.get("objects", ())) or []
        self.incl_fields = process_list_arg(self.options.get("fields", ())) or []
        self.incl_properties = (
            process_list_arg(self.options.get("properties", ())) or []
        )
        self.filename = Path(self.options.get("filename") or "org_schema.json")

    def _run_task(self):
        with open(self.filename, "w") as f:
            data = Schema.from_api(
                self.sf,
                self.incl_objects,
                self.incl_fields,
                self.incl_properties,
                self.logger,
            )
            json.dump(data.to_dict(), f)
        self.logger.info(f"Created {self.filename}")
