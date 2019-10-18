# IMPORT ORDER MATTERS!

# constants used by MetaCI
FAILED_TO_CREATE_SCRATCH_ORG = "Failed to create scratch org"

from cumulusci.core.config.base_config import BaseConfig

# inherit from BaseConfig


class ConnectedAppOAuthConfig(BaseConfig):
    """ Salesforce Connected App OAuth configuration """

    pass


class FlowConfig(BaseConfig):
    """ A flow with its configuration merged """

    pass


from cumulusci.core.config.org_config import OrgConfig


class ServiceConfig(BaseConfig):
    pass


class TaskConfig(BaseConfig):
    """ A task with its configuration merged """

    pass


from cumulusci.core.config.base_task_flow_config import BaseTaskFlowConfig


# inherit from BaseTaskFlowConfig
from cumulusci.core.config.project_config import BaseProjectConfig

# inherit from OrgConfig
from cumulusci.core.config.scratch_org_config import ScratchOrgConfig

# inherit from BaseProjectConfig
from cumulusci.core.config.global_config import BaseGlobalConfig


__all__ = [
    "BaseConfig",
    "ConnectedAppOAuthConfig",
    "FlowConfig",
    "OrgConfig",
    "ServiceConfig",
    "TaskConfig",
    "BaseTaskFlowConfig",
    "BaseProjectConfig",
    "ScratchOrgConfig",
    "BaseGlobalConfig",
]
