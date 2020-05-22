import pytest

from cumulusci.cli.logger import init_logger
from cumulusci.cli.runtime import CliRuntime
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.core.config import TaskConfig


def pytest_addoption(parser, pluginmanager):
    parser.addoption("--org", action="store", default=None, help="org to use")


@pytest.fixture(scope="session")
def runtime():
    """Get the CumulusCI runtime for the current working directory."""
    init_logger()
    return CliRuntime()


@pytest.fixture(scope="session")
def project_config(runtime):
    """Get the project config for the current working directory."""
    return runtime.project_config


@pytest.fixture(scope="session")
def org_config(request, runtime):
    """Get an org config with an active access token.

    Specify the org name using the --org option when running pytest.
    Or else it will use your default CCI org.
    """
    org_name = request.config.getoption("--org")
    org_name, org_config = runtime.get_org(org_name)
    org_config.refresh_oauth_token(runtime.keychain)
    return org_config


@pytest.fixture
def sf(request, project_config, org_config):
    """Get a simple-salesforce client for org_config."""
    sf = get_simple_salesforce_connection(project_config, org_config)
    return sf


@pytest.fixture
def create_task(request, project_config, org_config):
    """Get a task _factory_ which can be used to construct task instances.
    """
    session_project_config = project_config
    session_org_config = org_config

    def create_task(task_class, options=None, project_config=None, org_config=None):
        project_config = project_config or session_project_config
        org_config = org_config or session_org_config
        options = options or {}

        task_config = TaskConfig({"options": options})

        return task_class(project_config, task_config, org_config)

    return create_task
