import json
import os

import requests

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.utils import process_list_arg
from cumulusci.salesforce_api.metadata import ApiListMetadata
from cumulusci.tasks.salesforce import (
    BaseRetrieveMetadata,
    BaseSalesforceApiTask,
    DescribeMetadataTypes,
)
from cumulusci.tasks.salesforce.sourcetracking import ListChanges, retrieve_components

nl = "\n"


class ListNonSourceTrackable(BaseSalesforceApiTask):

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
        # The Metadata coverage report: https://developer.salesforce.com/docs/metadata-coverage/{version} is created from
        # the below URL. (So the api versions are allowed based on those report ranges)
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
    api_class = ApiListMetadata
    task_options = {
        "api_version": {
            "description": "Override the API version used to list metadatatypes",
        },
        "metadata_types": {"description": "A comma-separated list of metadata types."},
    }

    def _init_task(self):
        super()._init_task()

    def _init_options(self, kwargs):
        super(ListComponents, self)._init_options(kwargs)
        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version
        if "metadata_types" not in self.options:
            self.options["metadata_types"] = ListNonSourceTrackable(
                org_config=self.org_config,
                project_config=self.project_config,
                task_config=TaskConfig(
                    {"options": {"api_version": self.options["api_version"]}}
                ),
            )._run_task()
        else:
            self.options["metadata_types"] = process_list_arg(
                self.options.get("metadata_types")
            )

    def _get_components(self):
        list_components = []
        for md_type in self.options["metadata_types"]:
            api_object = self.api_class(
                self, metadata_type=md_type, as_of_version=self.options["api_version"]
            )
            components = api_object()
            for temp in components[md_type]:
                cmp = {
                    "MemberType": md_type,
                    "MemberName": temp["fullName"],
                    "lastModifiedByName": temp["lastModifiedByName"],
                    "lastModifiedDate": temp["lastModifiedDate"],
                }
                if cmp not in list_components:
                    list_components.append(cmp)
        return list_components

    def _run_task(self):
        self.return_values = self._get_components()
        self.logger.info(
            f"Found {len(self.return_values)} non source trackable components in the org for the given types."
        )
        for change in self.return_values:
            self.logger.info("{MemberType}: {MemberName}".format(**change))
        return self.return_values


retrieve_components_task_options = ListComponents.task_options.copy()
retrieve_components_task_options["path"] = {
    "description": "The path to write the retrieved metadata",
    "required": False,
}
retrieve_components_task_options["include"] = {
    "description": "Components will be included if one of these names"
    "is part of either the metadata type or name. "
    "Example: ``-o include CustomField,Admin`` matches both "
    "``CustomField: Favorite_Color__c`` and ``Profile: Admin``"
}
retrieve_components_task_options["exclude"] = {
    "description": "Exclude components matching this name."
}
retrieve_components_task_options[
    "namespace_tokenize"
] = BaseRetrieveMetadata.task_options["namespace_tokenize"]


class RetrieveComponents(ListComponents, BaseSalesforceApiTask):
    task_options = retrieve_components_task_options

    def _init_options(self, kwargs):
        super(RetrieveComponents, self)._init_options(kwargs)
        self.options["include"] = process_list_arg(self.options.get("include", []))
        self.options["exclude"] = process_list_arg(self.options.get("exclude", []))
        self._include = self.options["include"]
        self._exclude = self.options["exclude"]
        self._exclude.extend(self.project_config.project__source__ignore or [])

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
        components = self._get_components()
        filtered, ignored = ListChanges._filter_changes(self, components)
        if not filtered:
            self.logger.info("No components to retrieve")
            return
        for cmp in filtered:
            self.logger.info("{MemberType}: {MemberName}".format(**cmp))

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
