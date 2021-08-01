import pytest
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path

from cumulusci.cli.runtime import CliRuntime
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.core.config import TaskConfig
from cumulusci.tests.util import unmock_env
import cumulusci


def pytest_addoption(parser, pluginmanager):
    parser.addoption("--org", action="store", default=None, help="org to use")
    parser.addoption(
        "--run-slow-tests",
        action="store_true",
        default=False,
        help="Include slow tests.",
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
def org_config(request, fallback_org_config):
    """Get an org config with an active access token.

    Specify the org name using the --org option when running pytest.
    Or else it will use a dummy org.
    """
    org_name = sf_pytest_orgname(request)
    if org_name:
        with unmock_env():  # restore real homedir
            runtime = CliRuntime()
            runtime.keychain._load_orgs()
            org_name, org_config = runtime.get_org(org_name)
            assert org_config.scratch, "You should only run tests against scratch orgs."
            org_config.refresh_oauth_token(runtime.keychain)
    else:
        # fallback_org_config can be defined in "conftest" based
        # on the needs of the test suite. For example, for
        # fast running test suites it might return a hardcoded
        # org and for integration test suites it might return
        # a specific default org or throw an exception.
        return fallback_org_config()

    return org_config


@pytest.fixture
def sf(request, project_config, org_config):
    """Get a simple-salesforce client for org_config."""
    sf = get_simple_salesforce_connection(project_config, org_config)
    return sf


@pytest.fixture
def create_task(request, project_config, org_config):
    """Get a task _factory_ which can be used to construct task instances."""
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
    markers = [
        "slow(): a slow test that should only be executed when requested with --slow",
        "large_vcr(): a network-based test that generates VCR cassettes too large for version control. Use --org to generate them locally.",
        "needs_org(): a test that needs an org (or at least access to the network) but should not attempt to store VCR cassettes",
    ]

    for marker in markers:
        # register additional markers
        config.addinivalue_line("markers", marker)


def vcr_cassette_name_for_item(item):
    """Name of the VCR cassette"""
    test_class = item.cls
    if test_class:
        return "{}.{}".format(test_class.__name__, item.name)
    return item.name


def pytest_runtest_setup(item):
    marker_names = set(marker.name for marker in item.iter_markers())

    if "slow" in marker_names:
        if not item.config.getoption("--run-slow-tests"):
            pytest.skip("slow: test requires --run-slow-tests")

    if "large_vcr" in marker_names:
        library_dir = Path(cumulusci.__file__).parent.parent / "large_cassettes"
        item.add_marker(pytest.mark.vcr(cassette_library_dir=str(library_dir)))

        test_name = vcr_cassette_name_for_item(item)
        test_path = Path(library_dir) / (test_name + ".yaml")
        if not (test_path.exists() or item.config.getoption("--org")):
            pytest.skip("large_vcr: test requires --org to generate large cassette")

    elif "needs_org" in marker_names and not item.config.getoption("--org"):
        pytest.skip("needs_org: test requires --org")


class SFOrgConnectionState:
    should_record = True


sf_org_connection_state = ContextVar(
    "sf_org_connection_state", default=SFOrgConnectionState()
)
org_shapes = ContextVar("org_shapes", default={})


@pytest.fixture(
    scope="module",
)
def setup_org_without_recording(request, vcr):
    def really_setup_org_without_recording(func):
        orgname = sf_pytest_orgname(request)
        # Get a thread-local copy
        sf_org_connection_state.set(SFOrgConnectionState())
        if orgname:
            sf_org_connection_state.get().should_record = False
            try:
                return func()
            finally:
                sf_org_connection_state.get().should_record = True

    return really_setup_org_without_recording


@pytest.fixture(
    scope="module",
)
def org_shape(request, vcr):
    @contextmanager
    def org_shape(config_name: str = pytest, flow_name: str = None):
        shapes = org_shapes.get()
        org_name = f"pytest__{config_name}__{flow_name}"
        org = shapes.get(org_name)
        if org:
            return org

        from cumulusci.cli.org import org_scratch
        from cumulusci.cli.flow import flow_run
        import click
        from unittest import mock

        with click.Context(command=mock.Mock(), obj=CliRuntime()):
            org_scratch.callback(
                config_name,
                org_name,
                default=False,
                devhub=None,
                days=1,
                no_password=False,
            )
            flow_run.callback(
                flow_name,
                org_name,
                delete_org=False,
                debug=False,
                o=(),
                skip=None,
                no_prompt=True,
            )
            ### UNFINISHED

    return org_shape
