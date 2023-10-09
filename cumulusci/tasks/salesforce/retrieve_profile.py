from cumulusci.core.utils import process_list_arg
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.salesforce_api.retrieve_profile_api import RetrieveProfileApi
from cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask import (
    BaseSalesforceMetadataApiTask,
)

EXTRACT_DIR = "./unpackaged"


class RetrieveProfile(BaseSalesforceMetadataApiTask):
    api_version = "58.0"
    api_class = ApiRetrieveUnpackaged
    extract_dir = EXTRACT_DIR
    task_options = {
        "profiles": {
            "description": "List of profiles that you want to retrieve",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super(RetrieveProfile, self)._init_options(kwargs)

    def _run_task(self):

        self.profiles = process_list_arg(self.options["profiles"])
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

        # Comment the below lines if extracting all dependencies
        for file_info in zip_result.infolist():
            if file_info.filename.startswith("profiles/"):
                zip_result.extract(file_info, self.extract_dir)

        # If you wanna extract all dependencies, uncomment the below line
        # zip_result.extractall(self.extract_dir)

        self.logger.info(
            f"Profiles {', '.join(self.profiles)} unzipped into folder 'unpackaged'"
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
