from cumulusci.core.utils import deprecated_import

RetrieveReportsAndDashboards = deprecated_import(
    "cumulusci.tasks.salesforce.retrieve_reports_and_dashboards.RetrieveReportsAndDashboards"
)

__all__ = ["RetrieveReportsAndDashboards"]
