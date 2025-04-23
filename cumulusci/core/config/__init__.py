# IMPORT ORDER MATTERS!

# constants used by MetaCI
FAILED_TO_CREATE_SCRATCH_ORG = "Failed to create scratch org"

from cumulusci.core.config.base_config import BaseConfig
from cumulusci.core.exceptions import TaskImportError
from cumulusci.core.utils import import_global


class ConnectedAppOAuthConfig(BaseConfig):
    """Salesforce Connected App OAuth configuration"""

    client_id: str
    client_secret: str
    login_url: str
    callback_url: str


class FlowConfig(BaseConfig):
    """A flow with its configuration merged"""

    description: str
    steps: dict
    group: str
    checks: list
    project_config: "BaseProjectConfig"
    title: str
    slug: str
    tier: str
    preflight_message: str
    error_message: str
    tasks: dict  # deprecated


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
    service_name: str
    name: str
    server_domain: str

    def __init__(self, config, name=None, keychain=None):
        """Services may need access to a keychain and the alias of their service."""
        super().__init__(config, keychain)
        self.name = name if name else ""


class TaskConfig(BaseConfig):
    """A task with its configuration merged"""

    options: dict
    class_path: str
    description: str
    group: str
    ui_options: dict
    name: str
    checks: list
    project_config: "BaseProjectConfig"

    # TODO: What if an intermediate repo "allows" a downstream repo?
    #       Only the top repo should be allowed to do so.

    def get_class(self):
        try:
            return import_global(self.class_path)
        except ModuleNotFoundError as e:
            message = "Cannot load Python class for task:\n" + str(e)
            if not self.source.allow_remote_code:
                message += "\n".join(
                    (
                        "",
                        str(self.source),
                        "is not an approved source for running third party Python code.",
                        "If this task is custom Python, that would explain the problem.",
                        "Otherwise, it might just be a mistyped `class_name`.",
                        "More info: https://cumulusci.readthedocs.io/en/stable/config.html?highlight=sources#tasks-and-flows-from-a-different-project",
                    )
                )
            raise TaskImportError(message) from e

    @property
    def source(self):
        return self.project_config.source


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
