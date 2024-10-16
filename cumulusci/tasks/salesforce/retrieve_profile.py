from pathlib import Path

from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.salesforce_api.retrieve_profile_api import RetrieveProfileApi
from cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask import (
    BaseSalesforceMetadataApiTask,
)


class RetrieveProfile(BaseSalesforceMetadataApiTask):
    api_class = ApiRetrieveUnpackaged
    task_options = {
        "profiles": {
            "description": "List of profile API names that you want to retrieve",
            "required": True,
        },
        "path": {
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
        self.api_version = self.project_config.config["project"]["package"][
            "api_version"
        ]
        self.profiles = process_list_arg(self.options["profiles"])
        if not self.profiles:
            raise ValueError("At least one profile must be specified.")

        self.extract_dir = self.options.get("path", "force-app")
        extract_path = Path(self.extract_dir)

        if not extract_path.exists():
            raise FileNotFoundError(
                f"The extract directory '{self.extract_dir}' does not exist."
            )
        if not extract_path.is_dir():
            raise NotADirectoryError(f"'{self.extract_dir}' is not a directory.")

        # If extract_dir is force-app and main/default is not present
        if self.extract_dir == "force-app":
            if not (extract_path / "main" / "default").exists():
                (extract_path / "main" / "default").mkdir(parents=True, exist_ok=True)
            self.extract_dir = "force-app/main/default"

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

    def add_flow_accesses(self, profile_content, flows):
        # Find the position of the closing </Profile> tag
        profile_end_position = profile_content.find("</Profile>")

        if profile_end_position != -1:
            flow_accesses_xml = "".join(
                [
                    f"    <flowAccesses>\n"
                    f"        <enabled>true</enabled>\n"
                    f"        <flow>{flow}</flow>\n"
                    f"    </flowAccesses>\n"
                    for flow in flows
                ]
            )
            modified_content = (
                profile_content[:profile_end_position]
                + flow_accesses_xml
                + profile_content[profile_end_position:]
            )
            return modified_content

        return profile_content

    def save_profile_file(self, extract_dir, filename, content):
        profile_path = Path(extract_dir) / filename
        profile_meta_xml_path = Path(extract_dir) / f"{filename}-meta.xml"

        # Check if either the profile file or metadata file exists
        if profile_path.exists():
            self.update_file_content(profile_path, content)
        elif profile_meta_xml_path.exists():
            self.update_file_content(profile_meta_xml_path, content)
        else:
            # Neither file exists, create the profile file
            profile_meta_xml_path.parent.mkdir(parents=True, exist_ok=True)
            with profile_meta_xml_path.open(
                mode="w", encoding="utf-8"
            ) as updated_profile_file:
                updated_profile_file.write(content)

    def update_file_content(self, file_path, content):
        with open(file_path, "w", encoding="utf-8") as updated_file:
            updated_file.write(content)

    def _run_task(self):
        self.retrieve_profile_api_task = RetrieveProfileApi(
            project_config=self.project_config,
            task_config=self.task_config,
            org_config=self.org_config,
        )
        self.retrieve_profile_api_task._init_task()
        self._check_existing_profiles(self.retrieve_profile_api_task)
        (
            permissionable_entities,
            profile_flows,
        ) = self.retrieve_profile_api_task._retrieve_permissionable_entities(
            self.existing_profiles
        )
        entities_to_be_retrieved = {
            **permissionable_entities,
            **{"Profile": self.existing_profiles},
        }

        self.package_xml = self._create_package_xml(
            entities_to_be_retrieved, self.api_version
        )
        api = self._get_api()
        zip_result = api()

        for file_info in zip_result.infolist():
            if file_info.filename.startswith(
                "profiles/"
            ) and file_info.filename.endswith(".profile"):
                with zip_result.open(file_info) as profile_file:
                    profile_content = profile_file.read().decode("utf-8")
                    profile_name = profile_name = Path(file_info.filename).stem

                    if profile_name in profile_flows:
                        profile_content = self.add_flow_accesses(
                            profile_content, profile_flows[profile_name]
                        )

                    self.save_profile_file(
                        self.extract_dir, file_info.filename, profile_content
                    )

        # zip_result.extractall('./unpackaged')
        self.existing_profiles.remove(
            "Admin"
        ) if "Admin" in self.existing_profiles else None
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

    def _create_package_xml(self, input_dict: dict, api_version: str):
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
