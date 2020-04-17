import pytest

from cumulusci.cli.runtime import CliRuntime
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.core.config import TaskConfig


class CCI:
    runtime = None

    def __init__(self, org_name):
        if self.runtime:
            assert (
                org_name == self.orig_origname
            ), "This class only supports a single org per process, specified on the command line"
        else:
            self.init_runtime(org_name)

    @classmethod
    def init_runtime(cls, org_name):
        cls.orig_origname = org_name
        cls.runtime = CliRuntime()
        cls.org_name, cls.org_config = cls.runtime.get_org(org_name)
        cls.org_config.refresh_oauth_token(cls.runtime.keychain)
        cls.project_config = cls.runtime.project_config


def pytest_addoption(parser, pluginmanager):
    parser.addoption("--org", action="store", default=None, help="org to use")


@pytest.fixture
def sf(request):
    org_name = request.config.getoption("--org")
    cci = CCI(org_name)

    sf = get_simple_salesforce_connection(cci.runtime.project_config, cci.org_config)
    return sf


@pytest.fixture
def create_task(request):
    org_name = request.config.getoption("--org")
    cci = CCI(org_name)

    def create_task(task_class, options=None, project_config=None, org_config=None):
        project_config = project_config or cci.project_config
        org_config = org_config or cci.org_config
        options = options or {}

        task_config = TaskConfig({"options": options})

        return task_class(project_config, task_config, org_config)

    return create_task
