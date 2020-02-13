from cumulusci.tasks.salesforce.metadata_etl.base import (
    BaseMetadataETLTask,
    BaseMetadataSynthesisTask,
    BaseMetadataTransformTask,
    MetadataSingleEntityTransformTask,
    get_new_tag_index,
    MD,
)
from cumulusci.tasks.salesforce.metadata_etl.layouts import AddRelatedLists
from cumulusci.tasks.salesforce.metadata_etl.permissions import AddPermissions
from cumulusci.tasks.salesforce.metadata_etl.value_sets import AddValueSetEntries
from cumulusci.tasks.salesforce.metadata_etl.sharing import SetOrgWideDefaults

flake8 = (
    BaseMetadataETLTask,
    BaseMetadataSynthesisTask,
    BaseMetadataTransformTask,
    MetadataSingleEntityTransformTask,
    AddRelatedLists,
    AddPermissions,
    AddValueSetEntries,
    SetOrgWideDefaults,
    get_new_tag_index,
    MD,
)
