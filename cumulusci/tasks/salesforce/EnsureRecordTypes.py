from cumulusci.core.utils import deprecated_import

EnsureRecordTypes = deprecated_import(
    "cumulusci.tasks.salesforce.ensure_record_types.EnsureRecordTypes"
)

__all__ = ["EnsureRecordTypes"]
