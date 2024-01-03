import json
import os

import requests
import sarge

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import CumulusCIException, SfdxOrgException
from cumulusci.core.sfdx import sfdx
from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.salesforce import (
    BaseRetrieveMetadata,
    BaseSalesforceApiTask,
    DescribeMetadataTypes,
)
from cumulusci.tasks.salesforce.sourcetracking import ListChanges, retrieve_components

nl = "\n"


class ListMetadatatypes(BaseSalesforceApiTask):

    task_options = {
        "api_version": {
            "description": "Override the API version used to list metadatatypes",
        },
    }

    def _init_task(self):
        super()._init_task()
        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version

    def get_types_details(self, api_version):
        url = f"https://dx-extended-coverage.my.salesforce-sites.com/services/apexrest/report?version={api_version}"
        response = requests.get(url)
        if response.status_code == 200:
            json_response = response.json()
            return json_response
        else:
            raise CumulusCIException(
                f"Failed to retrieve response with status code {response.status_code}"
            )

    def _run_task(self):
        metadatatypes_details = self.get_types_details(self.options["api_version"])[
            "types"
        ]
        all_nonsource_types = []
        for md_type, details in metadatatypes_details.items():
            if not details["channels"]:
                raise CumulusCIException(
                    f"Api version {self.options['api_version']} not supported"
                )
            if (
                details["channels"]["sourceTracking"] is False
                and details["channels"]["metadataApi"] is True
            ):
                all_nonsource_types.append(md_type)

        types_supported = DescribeMetadataTypes(
            org_config=self.org_config,
            project_config=self.project_config,
            task_config=self.task_config,
        )._run_task()

        self.return_values = []
        for md_type in all_nonsource_types:
            if md_type in types_supported:
                self.return_values.append(md_type)

        if self.return_values:
            self.return_values.sort()

        self.logger.info(
            f"Non source trackable Metadata types supported by org: \n{self.return_values}"
        )
        return self.return_values


class ListComponents(BaseSalesforceApiTask):
    task_options = {
        "api_version": {
            "description": "Override the API version used to list metadatatypes",
        },
        "include": {
            "description": "A comma-separated list of strings. "
            "Components will be included if one of these strings "
            "is part of either the metadata type or name. "
            "Example: ``-o include CustomField,Admin`` matches both "
            "``CustomField: Favorite_Color__c`` and ``Profile: Admin``"
        },
        "types": {
            "description": "A comma-separated list of metadata types to include."
        },
        "exclude": {"description": "Exclude components matching this string."},
    }

    def _init_task(self):
        super()._init_task()
        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version

    def _init_options(self, kwargs):
        super(ListComponents, self)._init_options(kwargs)
        self.options["include"] = process_list_arg(self.options.get("include", [])) + [
            f"{mdtype}:" for mdtype in process_list_arg(self.options.get("types", []))
        ]
        self.options["exclude"] = process_list_arg(self.options.get("exclude", []))
        self._include = self.options["include"]
        self._exclude = self.options["exclude"]
        self._exclude.extend(self.project_config.project__source__ignore or [])

    def _get_components(self):
        task_config = TaskConfig(
            {"options": {"api_version": self.options["api_version"]}}
        )
        metadata_types = ListMetadatatypes(
            org_config=self.org_config,
            project_config=self.project_config,
            task_config=task_config,
        )._run_task()
        list_components = []
        for md_type in metadata_types:
            p: sarge.Command = sfdx(
                "force:mdapi:listmetadata",
                access_token=self.org_config.access_token,
                log_note="Listing components",
                args=[
                    "-a",
                    str(self.options["api_version"]),
                    "-m",
                    str(md_type),
                    "--json",
                ],
                env={"SFDX_INSTANCE_URL": self.org_config.instance_url},
            )
            stdout = p.stdout_text.read()
            stderr = p.stderr_text.read()

            if p.returncode:
                message = f"\nstderr:\n{nl.join(stderr)}"
                message += f"\nstdout:\n{nl.join(stdout)}"
                raise SfdxOrgException(message)
            else:
                result = json.loads(stdout)["result"]
                if result:
                    for cmp in result:
                        change_dict = {
                            "MemberType": md_type,
                            "MemberName": cmp["fullName"],
                        }
                        if change_dict not in list_components:
                            list_components.append(change_dict)

        return list_components

    def _run_task(self):
        changes = self._get_components()
        if changes:
            self.logger.info(
                f"Found {len(changes)} non source trackable components in the org."
            )
        else:
            self.logger.info("Found no non source trackable components.")

        filtered, ignored = ListChanges._filter_changes(self, changes)
        if ignored:
            self.logger.info(f"Ignored {len(ignored)} components in the org.")
            self.logger.info(f"{len(filtered)} remaining components after filtering.")

        for change in filtered:
            self.logger.info("{MemberType}: {MemberName}".format(**change))
        self.return_values = filtered
        return self.return_values


retrieve_components_task_options = ListComponents.task_options.copy()
retrieve_components_task_options["path"] = {
    "description": "The path to write the retrieved metadata",
    "required": False,
}
retrieve_components_task_options[
    "namespace_tokenize"
] = BaseRetrieveMetadata.task_options["namespace_tokenize"]


class RetrieveComponents(ListComponents, BaseSalesforceApiTask):
    task_options = retrieve_components_task_options

    def _init_options(self, kwargs):
        super(RetrieveComponents, self)._init_options(kwargs)

        package_directories = []
        default_package_directory = None
        if os.path.exists("sfdx-project.json"):
            with open("sfdx-project.json", "r", encoding="utf-8") as f:
                sfdx_project = json.load(f)
                for package_directory in sfdx_project.get("packageDirectories", []):
                    package_directories.append(package_directory["path"])
                    if package_directory.get("default"):
                        default_package_directory = package_directory["path"]

        path = self.options.get("path")
        if path is None:
            # set default path to src for mdapi format,
            # or the default package directory from sfdx-project.json for dx format
            if (
                default_package_directory
                and self.project_config.project__source_format == "sfdx"
            ):
                path = default_package_directory
                md_format = False
            else:
                path = "src"
                md_format = True
        else:
            md_format = path not in package_directories
        self.md_format = md_format
        self.options["path"] = path

    def _run_task(self):
        changes = self._get_components()
        filtered, ignored = ListChanges._filter_changes(self, changes)
        if not filtered:
            self.logger.info("No changes to retrieve")
            return
        for change in filtered:
            self.logger.info("{MemberType}: {MemberName}".format(**change))

        target = os.path.realpath(self.options["path"])
        package_xml_opts = {}
        if self.options["path"] == "src":
            package_xml_opts.update(
                {
                    "package_name": self.project_config.project__package__name,
                    "install_class": self.project_config.project__package__install_class,
                    "uninstall_class": self.project_config.project__package__uninstall_class,
                }
            )

        retrieve_components(
            filtered,
            self.org_config,
            target,
            md_format=self.md_format,
            namespace_tokenize=self.options.get("namespace_tokenize"),
            api_version=self.options["api_version"],
            extra_package_xml_opts=package_xml_opts,
        )
