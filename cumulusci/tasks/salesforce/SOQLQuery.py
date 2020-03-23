from cumulusci.core.utils import deprecated_import

SOQLQuery = deprecated_import("cumulusci.tasks.salesforce.soql_query.SOQLQuery")

__all__ = ["SOQLQuery"]
