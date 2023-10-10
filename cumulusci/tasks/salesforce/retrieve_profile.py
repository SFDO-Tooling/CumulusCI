import os

from cumulusci.core.utils import process_list_arg
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.salesforce_api.retrieve_profile_api import RetrieveProfileApi
from cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask import (
    BaseSalesforceMetadataApiTask,
)

EXTRACT_DIR = "force-app/default/main"


class RetrieveProfile(BaseSalesforceMetadataApiTask):
    api_version = "58.0"
    api_class = ApiRetrieveUnpackaged
    task_options = {
        "profiles": {
            "description": "List of profiles that you want to retrieve",
            "required": True,
        },
        "target": {
            "description": "Target folder path. By default, it uses force-app/main/default",
        },
    }

    def _init_options(self, kwargs):
        super(RetrieveProfile, self)._init_options(kwargs)
        self.profiles = process_list_arg(self.options["profiles"])
        if not self.profiles:
            raise ValueError("At least one profile must be specified.")

        self.extract_dir = self.options.get("target", EXTRACT_DIR)

        if not os.path.exists(self.extract_dir):
            raise FileNotFoundError(
                f"The extract directory '{self.extract_dir}' does not exist."
            )

        if not os.path.isdir(self.extract_dir):
            raise NotADirectoryError(f"'{self.extract_dir}' is not a directory.")

    def _run_task(self):
        self.retrieve_profile_api_task = RetrieveProfileApi(
            project_config=self.project_config,
            task_config=self.task_config,
            org_config=self.org_config,
        )
        self.retrieve_profile_api_task._init_task()
        permissionable_entities = (
            self.retrieve_profile_api_task._retrieve_permissionable_entities(
                self.profiles
            )
        )
        entities_to_be_retrieved = {
            **permissionable_entities,
            **{"Profile": self.profiles},
        }

        self.package_xml = self._create_package_xml(entities_to_be_retrieved)
        api = self._get_api()
        zip_result = api()

        extracted_profiles = set()
        for file_info in zip_result.infolist():
            if file_info.filename.startswith(
                "profiles/"
            ) and file_info.filename.endswith(".profile"):
                extracted_profile_name, _ = os.path.splitext(
                    os.path.basename(file_info.filename)
                )
                zip_result.extract(file_info, self.extract_dir)
                extracted_profiles.add(extracted_profile_name)

        # Check for missing profiles
        missing_profiles = set(self.profiles) - extracted_profiles
        if missing_profiles:
            self.logger.warning(
                f"The following profiles were not found or could not be retrieved: {', '.join(missing_profiles)}"
            )

        self.logger.info(
            f"Profiles {', '.join(extracted_profiles)} unzipped into folder '{self.extract_dir}'"
        )

    def _get_api(self):
        return self.api_class(
            self,
            api_version=self.api_version,
            package_xml=self.package_xml,
        )

    def _create_package_xml(self, input_dict: dict, api_version: str = api_version):
        package_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        package_xml += '<Package xmlns="http://soap.sforce.com/2006/04/metadata">\n'

        for name, members in input_dict.items():
            package_xml += "    <types>\n"
            for member in members:
                package_xml += f"        <members>{member}</members>\n"
            package_xml += f"        <name>{name}</name>\n"
            package_xml += "    </types>\n"

        package_xml += f"    <version>{api_version}</version>\n"
        package_xml += "</Package>\n"

        return package_xml
