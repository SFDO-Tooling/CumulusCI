import typing as T
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest

import cumulusci
from cumulusci.cli.org import org_remove, org_scratch, org_scratch_delete
from cumulusci.cli.runtime import CliRuntime
from cumulusci.core.config import OrgConfig, TaskConfig
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.tests.util import CURRENT_SF_API_VERSION, unmock_env


def pytest_addoption(parser, pluginmanager):
    """Pytest magic method: add --org, --replace-vcrs and --run-slow-tests features"""
    parser.addoption("--org", action="store", default=None, help="org to use")
    parser.addoption(
        "--run-slow-tests",
        action="store_true",
        default=False,
        help="Include slow tests.",
    )
    parser.addoption(
        "--replace-vcrs",
        action="store_true",
        default=False,
        help="Replace VCR files.",
    )
    parser.addoption(
        "--opt-in",
        action="store_true",
        default=False,
        help="disable custom_skip marks",
    )


def pytest_configure(config):
    """Pytest magic method: add pytest markers/decorators"""
    markers = [
        "slow(): a slow test that should only be executed when requested with --run-slow-tests",
        "large_vcr(): a network-based test that generates VCR cassettes too large for version control. Use --org to generate them locally.",
        "needs_org(): a test that needs an org (or at least access to the network) but should not attempt to store VCR cassettes",
        "org_shape(org_name, init_flow): a test that needs a particular org shape",
        "opt_in(): a test that is 'off' by default (perhaps because it depends on some setup)",
    ]

    for marker in markers:
        # register additional markers
        config.addinivalue_line("markers", marker)


def pytest_runtest_setup(item):
    """Pytest magic method"""
    marker_names = set(marker.name for marker in item.iter_markers())
    classify_and_modify_test(item, marker_names)


def sf_pytest_cli_orgname(request):
    """Helper to see what org the user has asked for"""
    return request.config.getoption("--org")


@pytest.fixture(scope="session")
def user_requested_network_access(request):
    """Did the user ask to enable network access by specifying an org?"""
    return bool(sf_pytest_cli_orgname(request))


@pytest.fixture(scope="session")
def user_requested_cassette_replacement(request):
    """Did the user ask to delete VCR cassettes?"""
    return request.config.getoption("--replace-vcrs")


@pytest.fixture(scope="session")
def runtime():
    """Get the CumulusCI runtime for the current working directory."""
    return CliRuntime()


@pytest.fixture(scope="session")
def project_config(runtime):
    """Get the project config for the current working directory."""
    return runtime.project_config


@pytest.fixture(scope="session")
def cli_org_config(request):
    """What org did the user specify on the CLI or pytest options?"""
    cli_org_name = sf_pytest_cli_orgname(request)
    if cli_org_name:
        with unmock_env():  # restore real homedir
            runtime = CliRuntime()
            runtime.keychain._load_orgs()
            org_name, org_config = runtime.get_org(cli_org_name)
            assert org_config.scratch, "You should only run tests against scratch orgs."
            org_config.refresh_oauth_token(runtime.keychain)
            return org_config


@pytest.fixture(scope="function")
def org_config(request, current_org_shape, cli_org_config, fallback_org_config):
    """Get an org config with an active access token.

    If an org was requested by the org_shape feature, it is used.

    Otherwise, you can specify the org name using the --org option when running pytest.

    If there was no org provided by those mechanisms, it will use a dummy org.
    """
    org_config = current_org_shape.org_config or cli_org_config
    if org_config:
        org_config.user_specified = True
    else:
        org_config = fallback_org_config()

    # fallback_org_config can be defined in "conftest" based
    # on the needs of the test suite. For example, for
    # fast running test suites it might return a hardcoded
    # org and for integration test suites it might return
    # a specific default org or throw an exception.
    with mock.patch.object(
        OrgConfig, "latest_api_version", CURRENT_SF_API_VERSION
    ), mock.patch.object(OrgConfig, "refresh_oauth_token"):
        yield org_config


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

        t = task_class(project_config, task_config, org_config)
        t._update_credentials = mock.Mock()
        return t

    return create_task


def vcr_cassette_name_for_item(item):
    """Name of the VCR cassette"""
    test_class = item.cls
    if test_class:
        return "{}.{}".format(test_class.__name__, item.name)
    return item.name


def classify_and_modify_test(item, marker_names):
    if "opt_in" in marker_names and not item.config.getoption("--opt-in"):
        pytest.skip("Skip by default turned on")

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


class CurrentOrg:
    __slots__ = ("org_config",)

    def __init__(self):
        self.org_config = None


@pytest.fixture(scope="session")
def org_shapes():
    org_shapes = {}
    try:
        yield org_shapes
    finally:
        cleanup_org_shapes(org_shapes)


def cleanup_org_shapes(org_shapes: dict):
    runtime = CliRuntime(load_keychain=True)
    errors = []
    for org_name in org_shapes:
        cleanup_org(runtime, org_name, errors)

    if errors:
        raise AssertionError(str(errors))


def cleanup_org(runtime, org_name, errors):
    try:
        org_scratch_delete.callback.__wrapped__(
            runtime,
            org_name,
        )
    except Exception as e:
        print(f"EXCEPTION deleting org {e}")
        errors.append(e)
    try:
        org_remove.callback.__wrapped__(runtime, org_name, False)
    except Exception:
        pass


@pytest.fixture(scope="session")
def current_org_shape(request):
    """Internal: shared state for fixtures"""
    org = CurrentOrg()
    return org


@pytest.fixture(scope="function", autouse=True)
def _change_org_shape(request, current_org_shape, org_shapes):
    """Select an org_shape for a test
    e.g.:

        @pytest.mark.org_shape("qa", "qa_org")
        def test_foo(create_task);
            t = create_task(Foo)
            t()

    Switch the current org to an org created with
    org template "qa" after running flow "qa_org".

    Clean up any changes you make, because this org may be reused by
    other tests.
    """
    marker = request.node.get_closest_marker("org_shape")
    if marker:
        config_name, flow_name = marker.args
        with change_org_shape(
            current_org_shape, config_name, flow_name, org_shapes
        ) as org_config:
            yield org_config
    else:
        yield None


@contextmanager
def change_org_shape(
    current_org_shape, config_name: str, flow_name: T.Optional[str], org_shapes: dict
):

    # I don't love that we're using the user's real keychain
    # but otherwise we have no devhub connection
    with unmock_env():
        org_name = f"pytest__{config_name}__{flow_name}"
        org_config = org_shapes.get(org_name)
        if not org_config:
            org_config = _create_org(org_name, config_name, flow_name)
            org_shapes[org_name] = org_config
            org_config.sfdx_info  # generate and cache sfdx info
    with mock.patch.object(current_org_shape, "org_config", org_config):
        yield org_config


def _create_org(org_name: str, config_name: str, flow_name: str = None):
    runtime = CliRuntime(load_keychain=True)
    try:
        org, org_config = runtime.get_org(org_name)
    except OrgNotFound:
        org = None
    if org:
        cleanup_org_shapes([org_name])
    try:
        org_scratch.callback.__wrapped__(
            runtime,
            config_name,
            org_name,
            default=False,
            devhub=None,
            days=1,
            no_password=False,
        )
        org, org_config = runtime.get_org(org_name)

        if flow_name:
            coordinator = runtime.get_flow(flow_name)
            coordinator.run(org_config)
    except Exception:
        if runtime.get_org(org_name, fail_if_missing=False):
            org_scratch_delete.callback.__wrapped__(runtime, org_name)
        raise
    return org_config
