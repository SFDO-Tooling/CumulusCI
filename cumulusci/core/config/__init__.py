# IMPORT ORDER MATTERS!

# constants used by MetaCI
FAILED_TO_CREATE_SCRATCH_ORG = "Failed to create scratch org"

from cumulusci.core.config.base_config import BaseConfig

# inherit from BaseConfig


class ConnectedAppOAuthConfig(BaseConfig):
    """Salesforce Connected App OAuth configuration"""

    client_id: str
    client_secret: str
    login_url: str
    callback_url: str


class FlowConfig(BaseConfig):
    """A flow with its configuration merged"""

    description: str
    steps: list
    group: str
    checks: list
    project_config: BaseConfig


from cumulusci.core.config.org_config import OrgConfig


class ServiceConfig(BaseConfig):
    url: str
    username: str
    password: str
    token: str
    email: str
    client_id: str
    client_secret: str
    token_uri: str
    callback_url: str
    login_url: str

    def __init__(self, config, name=None, keychain=None):
        """Services may need access to a keychain and the alias of their service."""
        super().__init__(config, keychain)


class TaskConfig(BaseConfig):
    """A task with its configuration merged"""

    options: str
    class_path: str
    description: str
    group: str
    ui_options: str
    name: str
    checks: str
    project_config: str

    pass


from cumulusci.core.config.base_task_flow_config import BaseTaskFlowConfig

# inherit from BaseTaskFlowConfig
from cumulusci.core.config.project_config import BaseProjectConfig

# inherit from SfdxOrgConfig
from cumulusci.core.config.scratch_org_config import ScratchOrgConfig

# inherit from OrgConfig
from cumulusci.core.config.sfdx_org_config import SfdxOrgConfig

# inherit from BaseProjectConfig
from cumulusci.core.config.universal_config import UniversalConfig

__all__ = (
    "FAILED_TO_CREATE_SCRATCH_ORG",
    "BaseConfig",
    "ConnectedAppOAuthConfig",
    "FlowConfig",
    "OrgConfig",
    "ServiceConfig",
    "TaskConfig",
    "BaseTaskFlowConfig",
    "BaseProjectConfig",
    "SfdxOrgConfig",
    "ScratchOrgConfig",
    "UniversalConfig",
)
