# IMPORT ORDER MATTERS!

# constants used by MetaCI
FAILED_TO_CREATE_SCRATCH_ORG = 'Failed to create scratch org'

from cumulusci.core.config.BaseConfig import BaseConfig

# inherit from BaseConfig
from cumulusci.core.config.BaseTaskFlowConfig import BaseTaskFlowConfig
from cumulusci.core.config.ConnectedAppOAuthConfig import ConnectedAppOAuthConfig
from cumulusci.core.config.FlowConfig import FlowConfig
from cumulusci.core.config.OrgConfig import OrgConfig
from cumulusci.core.config.ServiceConfig import ServiceConfig
from cumulusci.core.config.TaskConfig import TaskConfig

# inherit from BaseTaskFlowConfig
from cumulusci.core.config.BaseGlobalConfig import BaseGlobalConfig
from cumulusci.core.config.BaseProjectConfig import BaseProjectConfig

# inherit from OrgConfig
from cumulusci.core.config.ScratchOrgConfig import ScratchOrgConfig

# inherit from BaseGlobalConfig
from cumulusci.core.config.YamlGlobalConfig import YamlGlobalConfig

# inherit from BaseProjectConfig
from cumulusci.core.config.YamlProjectConfig import YamlProjectConfig
