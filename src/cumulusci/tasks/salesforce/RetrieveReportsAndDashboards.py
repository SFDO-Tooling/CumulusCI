from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.metadata import ApiListMetadata, ApiRetrieveUnpackaged
from cumulusci.tasks.salesforce import BaseRetrieveMetadata
from cumulusci.utils import package_xml_from_dict

retrieve_reportsanddashboards_options = BaseRetrieveMetadata.task_options.copy()
retrieve_reportsanddashboards_options.update(
    {
        "report_folders": {
            "description": "A list of the report folders to retrieve reports.  Separate by commas for multiple folders."
        },
        "dashboard_folders": {
            "description": "A list of the dashboard folders to retrieve reports.  Separate by commas for multiple folders."
        },
        "api_version": {
            "description": "Override the API version used to list metadata"
        },
    }
)


class RetrieveReportsAndDashboards(BaseRetrieveMetadata):
    api_class = ApiRetrieveUnpackaged
    list_metadata_api_class = ApiListMetadata

    task_options = retrieve_reportsanddashboards_options

    def _init_options(self, kwargs):
        super(RetrieveReportsAndDashboards, self)._init_options(kwargs)
        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version

    def _validate_options(self):
        super(RetrieveReportsAndDashboards, self)._validate_options()
        if (
            "report_folders" not in self.options
            and "dashboard_folders" not in self.options
        ):
            raise TaskOptionsError(
                "You must provide at least one folder name for either report_folders or dashboard_folders"
            )

    def _get_api(self):
        metadata = {}
        if "report_folders" in self.options:
            for folder in self.options["report_folders"]:
                api_reports = self.list_metadata_api_class(
                    self,
                    "Report",
                    metadata=metadata,
                    folder=folder,
                    as_of_version=self.options["api_version"],
                )
                metadata = api_reports()
        if "dashboard_folders" in self.options:
            for folder in self.options["dashboard_folders"]:
                api_dashboards = self.list_metadata_api_class(
                    self,
                    "Dashboard",
                    metadata=metadata,
                    folder=folder,
                    as_of_version=self.options["api_version"],
                )
                metadata = api_dashboards()

        items = {}
        if "Report" in metadata:
            items["Report"] = []
            items["Report"].extend(self.options["report_folders"])
            for report in metadata["Report"]:
                items["Report"].append(report["fullName"])
        if "Dashboard" in metadata:
            items["Dashboard"] = []
            items["Dashboard"].extend(self.options["dashboard_folders"])
            for dashboard in metadata["Dashboard"]:
                items["Dashboard"].append(dashboard["fullName"])

        api_version = self.options["api_version"]
        package_xml = package_xml_from_dict(items, api_version)
        return self.api_class(self, package_xml, api_version)
