from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config.sfdx_org_config import SfdxOrgConfig
from cumulusci.core.exceptions import CumulusCIException, ServiceNotConfigured
from cumulusci.core.sfdx import get_default_devhub_username


def get_devhub_config(project_config: BaseProjectConfig) -> SfdxOrgConfig:
    """
    @param project_config: a base project configuration
    @return: an SfdxOrgConfig tied to the devHub
    """
    try:
        devhub_service = project_config.keychain.get_service("devhub")
    except (ServiceNotConfigured, CumulusCIException):
        devhub_username = get_default_devhub_username()
    else:
        devhub_username = devhub_service.username
    return SfdxOrgConfig({"username": devhub_username}, "devhub")
