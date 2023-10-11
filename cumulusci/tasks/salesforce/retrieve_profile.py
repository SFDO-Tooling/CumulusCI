import os

from cumulusci.core.utils import process_bool_arg, process_list_arg
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
        "strict_mode": {
            "description": "When set to False, enables leniency by ignoring missing profiles when provided with a list of profiles."
            " When set to True, enforces strict validation, causing a failure if any profile is not present in the list."
            " Default is True",
            "required": False,
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

        self.strictMode = process_bool_arg(self.options.get("strict_mode", True))

    def _check_existing_profiles(self, retrieve_profile_api_task):
        # Check for existing profiles
        self.existing_profiles = retrieve_profile_api_task._retrieve_existing_profiles(
            self.profiles
        )
        self.missing_profiles = set(self.profiles) - set(self.existing_profiles)

        # Handle for strictMode
        if self.missing_profiles:
            self.logger.warning(
                f"The following profiles were not found or could not be retrieved: '{', '.join(self.missing_profiles)}'\n"
            )
            if self.strictMode:
                raise RuntimeError(
                    "Operation failed due to missing profiles. Set strictMode to False if you want to ignore missing profiles."
                )

        # Handle for no existing profiles
        if not self.existing_profiles:
            raise RuntimeError("None of the profiles given were found.")

    def _run_task(self):
        self.retrieve_profile_api_task = RetrieveProfileApi(
            project_config=self.project_config,
            task_config=self.task_config,
            org_config=self.org_config,
        )
        self.retrieve_profile_api_task._init_task()
        self._check_existing_profiles(self.retrieve_profile_api_task)
        permissionable_entities = (
            self.retrieve_profile_api_task._retrieve_permissionable_entities(
                self.existing_profiles
            )
        )
        entities_to_be_retrieved = {
            **permissionable_entities,
            **{"Profile": self.existing_profiles},
        }

        self.package_xml = self._create_package_xml(entities_to_be_retrieved)
        api = self._get_api()
        zip_result = api()

        for file_info in zip_result.infolist():
            if file_info.filename.startswith(
                "profiles/"
            ) and file_info.filename.endswith(".profile"):
                extracted_profile_name, _ = os.path.splitext(
                    os.path.basename(file_info.filename)
                )
                zip_result.extract(file_info, self.extract_dir)

        self.logger.info(
            f"Profiles {', '.join(self.existing_profiles)} unzipped into folder '{self.extract_dir}'"
        )

    def _get_api(self):
        # Logs
        self.logger.info("Retrieving all entities from org:")

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
