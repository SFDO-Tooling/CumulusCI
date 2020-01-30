import os
import re
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce import BaseSalesforceApiTask, Deploy
from cumulusci.utils import temporary_dir

BUSINESS_PROCESS_METADATA = """<businessProcesses>
        <fullName>{record_type_developer_name}</fullName>
        <isActive>true</isActive>
        <values>
            <fullName>{stage_name}</fullName>
            <default>{default}</default>
        </values>
    </businessProcesses>"""

BUSINESS_PROCESS_LINK = (
    """<businessProcess>{record_type_developer_name}</businessProcess>"""
)

SOBJECT_METADATA = """<?xml version="1.0" encoding="utf-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    {business_process_metadata}
    <recordTypes>
        <fullName>{record_type_developer_name}</fullName>
        <active>true</active>
        {business_process_link}
        <label>{record_type_label}</label>
    </recordTypes>
</CustomObject>
"""

PACKAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>*</members>
        <name>CustomObject</name>
    </types>
    <version>45.0</version>
</Package>"""

SOBJECT_MAP = {
    "Opportunity": "StageName",
    "Lead": "Status",
    "Case": "Status",
    "Solution": "Status",
}


class EnsureRecordTypes(BaseSalesforceApiTask):
    task_options = {
        "record_type_developer_name": {
            "description": "The Developer Name of the Record Type (unique).  Must contain only alphanumeric characters and underscores.",
            "required": True,
        },
        "record_type_label": {
            "description": "The Label of the Record Type.",
            "required": True,
        },
        "sobject": {
            "description": "The sObject on which to deploy the Record Type and optional Business Process.",
            "required": True,
        },
    }
    _deploy = Deploy

    def _init_options(self, kwargs):
        super(EnsureRecordTypes, self)._init_options(kwargs)

        self.options["generate_business_process"] = False

        # Validate developer name
        if not re.match(r"^\w+$", self.options["record_type_developer_name"]):
            raise TaskOptionsError(
                "Record Type Developer Name value must contain only alphanumeric or underscore characters"
            )

        # We don't currently support standard objects
        if self.options["sobject"].endswith("__c"):
            raise TaskOptionsError("EnsureRecordTypes does not support custom objects")

    def _infer_requirements(self):
        # If our sObject is Lead, Opportunity, Case, or Solution,
        # we need to generate businessProcess metadata to make the record type deployable.

        # Regardless of sObject, we don't need to do any work if it already
        # has record types in the target org.
        sobject = self.options["sobject"]
        describe_results = getattr(self.sf, sobject).describe()

        # Check for existing record types. We ignore the record type info with master: True,
        # because it's present even if record types aren't enabled for the object.
        record_types = [
            rt for rt in describe_results["recordTypeInfos"] if not rt["master"]
        ]

        self.options["generate_record_type"] = len(record_types) == 0

        if self.options["generate_record_type"] and sobject in SOBJECT_MAP:
            self.options["generate_business_process"] = True
            # Salesforce requires that at least one picklist value be present and active
            stage_field = [
                f
                for f in describe_results["fields"]
                if f["name"] == SOBJECT_MAP[sobject]
            ][0]
            active_picklist_values = [
                value for value in stage_field["picklistValues"] if value["active"]
            ]
            self.options["stage_name"] = active_picklist_values[0]["value"]

    def _build_package(self):
        objects_app_path = "objects"
        os.mkdir(objects_app_path)
        with open(
            os.path.join(objects_app_path, self.options["sobject"] + ".object"), "w"
        ) as f:
            if self.options["generate_business_process"]:
                self.logger.info(
                    "Generating record type and business process for sObject {}".format(
                        self.options["sobject"]
                    )
                )
                # Lead, Case, and Solution require a default value in their Business Process
                # Opportunity prohibits it.
                default = (
                    "true" if self.options["sobject"] != "Opportunity" else "false"
                )

                business_process_metadata = BUSINESS_PROCESS_METADATA.format(
                    record_type_developer_name=self.options[
                        "record_type_developer_name"
                    ],
                    stage_name=self.options["stage_name"],
                    default=default,
                )
                business_process_link = BUSINESS_PROCESS_LINK.format(
                    record_type_developer_name=self.options[
                        "record_type_developer_name"
                    ]
                )
            else:
                self.logger.info(
                    "Generating record type for sObject {}".format(
                        self.options["sobject"]
                    )
                )
                business_process_metadata = business_process_link = ""

            f.write(
                SOBJECT_METADATA.format(
                    record_type_developer_name=self.options[
                        "record_type_developer_name"
                    ],
                    record_type_label=self.options["record_type_label"],
                    business_process_metadata=business_process_metadata,
                    business_process_link=business_process_link,
                )
            )
        with open("package.xml", "w") as f:
            f.write(PACKAGE_XML)

    def _run_task(self):
        self._infer_requirements()

        if not self.options["generate_record_type"]:
            self.logger.info(
                "Record types already enabled for {} in target org; no action needed".format(
                    self.options["sobject"]
                )
            )
            return

        with temporary_dir() as tempdir:
            self._build_package()
            d = self._deploy(
                self.project_config, self.task_config, self.org_config, path=tempdir
            )
            d()
