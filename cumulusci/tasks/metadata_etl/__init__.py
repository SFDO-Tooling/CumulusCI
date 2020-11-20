from cumulusci.tasks.metadata_etl.base import (
    BaseMetadataETLTask,
    BaseMetadataSynthesisTask,
    BaseMetadataTransformTask,
    MetadataSingleEntityTransformTask,
    MetadataOperation,
    UpdateMetadataFirstChildTextTask,
)
from cumulusci.tasks.metadata_etl.duplicate_rules import SetDuplicateRuleStatus
from cumulusci.tasks.metadata_etl.layouts import AddRelatedLists
from cumulusci.tasks.metadata_etl.permissions import AddPermissionSetPermissions
from cumulusci.tasks.metadata_etl.value_sets import AddValueSetEntries
from cumulusci.tasks.metadata_etl.sharing import SetOrgWideDefaults
from cumulusci.tasks.metadata_etl.encryption import EncryptAllFields

flake8 = (
    BaseMetadataETLTask,
    BaseMetadataSynthesisTask,
    BaseMetadataTransformTask,
    MetadataSingleEntityTransformTask,
    AddRelatedLists,
    AddPermissionSetPermissions,
    AddValueSetEntries,
    EncryptAllFields,
    SetOrgWideDefaults,
    MetadataOperation,
    SetDuplicateRuleStatus,
    UpdateMetadataFirstChildTextTask,
)
