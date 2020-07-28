import pytest
import os.path

from cumulusci.cli.runtime import CliRuntime
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.core.config import TaskConfig


def pytest_addoption(parser, pluginmanager):
    parser.addoption("--org", action="store", default=None, help="org to use")
    parser.addoption(
        "--accelerate-integration-tests",
        action="store_true",
        default=False,
        help="DO run integration tests. Do NOT make calls to a real org. This will error out if you have not run with '--org blah' so that you have cached org output.",
    )


def sf_pytest_orgname(request):
    return request.config.getoption("--org")


@pytest.fixture(scope="session")
def runtime():
    """Get the CumulusCI runtime for the current working directory."""
    return CliRuntime()


@pytest.fixture(scope="session")
def project_config(runtime):
    """Get the project config for the current working directory."""
    return runtime.project_config


@pytest.fixture(scope="session")
def org_config(request, runtime, fallback_orgconfig):
    """Get an org config with an active access token.

    Specify the org name using the --org option when running pytest.
    Or else it will use a dummy org.
    """
    org_name = sf_pytest_orgname(request)
    if org_name:
        org_name, org_config = runtime.get_org(org_name)
        assert org_config.scratch, "You should only run tests against scratch orgs."
        org_config.refresh_oauth_token(runtime.keychain)
    else:
        # fallback_orgconfig can be defined in "conftest" based
        # on the needs of the test suite. For example, for
        # fast running test suites it might return a hardcoded
        # org and for integration test suites it might return
        # a specific default org or throw an exception.
        return fallback_orgconfig()

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


def pytest_configure(config):
    # register an additional marker
    config.addinivalue_line(
        "markers",
        "integration_test(): an integration test that should only be executed when requested",
    )


def pytest_runtest_setup(item):
    is_integration_test = any(item.iter_markers(name="integration_test"))
    if is_integration_test:
        if not item.config.getoption(
            "--accelerate-integration-tests"
        ) and not item.config.getoption("--org"):
            pytest.skip("test requires --org or --accelerate-integration-tests")


@pytest.fixture(scope="module")
def vcr_cassette_dir(request):
    is_integration_test = any(request.node.iter_markers(name="integration_test"))
    test_dir = request.node.fspath.dirname
    if is_integration_test:
        return os.path.join(test_dir, "large_cassettes")  # 8-tracks
    else:  # standard behaviour from
        # https://github.com/ktosiek/pytest-vcr/blob/master/pytest_vcr.py
        return os.path.join(test_dir, "cassettes")
