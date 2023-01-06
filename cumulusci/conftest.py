import io
import os
import shutil
from contextlib import contextmanager
from http.client import HTTPMessage
from logging import getLogger
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pytest
import yaml
from pytest import fixture
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cumulusci.core.dependencies.utils import TaskContext
from cumulusci.core.github import get_github_api
from cumulusci.salesforce_api.org_schema_models import Base
from cumulusci.tasks.bulkdata.tests.integration_test_utils import (
    ensure_accounts,
    ensure_records,
)
from cumulusci.tasks.salesforce.tests.util import create_task_fixture
from cumulusci.tests.pytest_plugins.pytest_sf_vcr import salesforce_vcr, vcr_config
from cumulusci.tests.util import DummyKeychain, DummyOrgConfig, mock_env
from cumulusci.utils import cd

ensure_accounts = ensure_accounts
ensure_records = ensure_records


@fixture(scope="session", autouse=True)
def mock_sleep():
    """Patch time.sleep to avoid delays in unit tests"""
    with mock.patch("time.sleep"):
        yield


class MockHttpResponse(mock.Mock):
    def __init__(self, status):
        super(MockHttpResponse, self).__init__()
        self.status = status
        self.strict = 0
        self.version = 0
        self.reason = None
        self.msg = HTTPMessage(io.BytesIO())
        self.closed = True

    def read(self):  # pragma: no cover
        return b""

    def isclosed(self):
        return self.closed


@fixture
def gh_api():
    return get_github_api("TestOwner", "TestRepo")


@fixture(scope="class", autouse=True)
def restore_cwd():
    d = os.getcwd()
    try:
        yield
    finally:
        os.chdir(d)


@fixture
def mock_http_response():
    def _make_response(status):
        return MockHttpResponse(status)

    return _make_response


@fixture(scope="session")
def fallback_org_config():
    def fallback_org_config():
        return DummyOrgConfig(
            name="pytest_sf_orgconnect_dummy_org_config", keychain=DummyKeychain()
        )

    return fallback_org_config


vcr_config = fixture(vcr_config, scope="module")
vcr = fixture(salesforce_vcr, scope="module")

create_task_fixture = fixture(create_task_fixture, scope="function")


# TODO: This should also chdir to a temp directory which
#       can represent the repo-root, but that will require
#       test case changes.
@pytest.fixture(autouse=True)
def patch_home_and_env(request):
    "Patch the default home directory and $HOME environment for all tests at once."
    with TemporaryDirectory(prefix="fake_home_") as home, mock_env(home):
        Path(home, ".cumulusci").mkdir()
        Path(home, "cumulusci.yml").touch()
        yield


@pytest.fixture(scope="session")
def readonly_dummy_projdir(request, cumulusci_test_repo_root):
    """Create a cache-based project directory for tests that depend on it.

    The project is cached in .cache/TestProject persistently.

    At most once per test session it is copied to a temp folder, lazily.

    Tests that need it, can opt in to using it with the `run_in_dummy_projdir` fixture.
    """
    with TemporaryDirectory(prefix="dummy_project_") as home:
        ccitest = cumulusci_test_repo_root / ".cache/TestProject"
        if not ccitest.exists():
            (cumulusci_test_repo_root / ".cache").mkdir(exist_ok=True)
            # TODO: Change this to using CumulusCI-Test...but some work
            #       needs to be done first. CumulusCI-Test doesn't seem
            #       to have releases.
            # ccitest_url = "https://github.com/SFDO-Tooling/CumulusCI-Test.git"
            ccitest_url = "https://github.com/SFDO-Tooling/CumulusCI.git"
            os.system(f'git clone {ccitest_url} "{ccitest}"')
        shutil.rmtree(home)
        shutil.copytree(ccitest, home)
        yield home


@pytest.fixture(scope="function")
def run_in_dummy_projdir(request, readonly_dummy_projdir):
    "Run a test in a dummy CCI project"
    with cd(readonly_dummy_projdir), mock_env(readonly_dummy_projdir):
        yield


@pytest.fixture()
def temp_db():
    with TemporaryDirectory() as t:

        @contextmanager
        def open_db():
            engine = create_engine(f"sqlite:///{t}/tempfile.db")
            with engine.connect() as connection:
                Session = sessionmaker(bind=connection)
                Base.metadata.bind = engine
                Base.metadata.create_all()
                session = Session()
                yield connection, Base.metadata, session

        yield open_db


@pytest.fixture()
def delete_data_from_org(create_task):
    def delete_data_from_org(object_names):
        from cumulusci.tasks.bulkdata.delete import DeleteData

        t = create_task(DeleteData, {"objects": object_names})
        assert t.org_config.scratch
        t()

    return delete_data_from_org


@pytest.fixture(scope="session")
def cumulusci_test_repo_root():
    return Path(__file__).parent.parent


@pytest.fixture(scope="function")
def run_from_cci_root(cumulusci_test_repo_root):
    with cd(cumulusci_test_repo_root):
        yield


@pytest.fixture(scope="session")
def global_describe(cumulusci_test_repo_root):
    global_describe_file = (
        cumulusci_test_repo_root
        / "cumulusci/tests/shared_cassettes/GET_sobjects_Global_describe.yaml"
    )
    with global_describe_file.open() as f:
        data = yaml.safe_load(yaml.safe_load(f)["response"]["body"]["string"])

    def global_describe_specific_sobjects(sobjects: int = None):
        if sobjects is None:  # pragma: no cover
            subset = data.copy()
        elif isinstance(sobjects, int):
            subset = data.copy()
            subset["sobjects"] = subset["sobjects"][0:sobjects]
        elif isinstance(sobjects, (list, tuple)):  # pragma: no cover
            raise NotImplementedError(
                "We could implement a by-name subsetting here when we need it."
            )
        return subset

    return global_describe_specific_sobjects


@pytest.fixture(scope="session")
def shared_vcr_cassettes(cumulusci_test_repo_root):
    return Path(cumulusci_test_repo_root / "cumulusci/tests/shared_cassettes")


@pytest.fixture
def task_context(org_config, project_config):
    return TaskContext(
        org_config=org_config, project_config=project_config, logger=getLogger()
    )
