import io
import os
from contextlib import contextmanager, nullcontext
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


@fixture(scope="function")
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

    use_real_env = request.node.get_closest_marker("use_real_env")

    with TemporaryDirectory(prefix="fake_home_") as home:
        if use_real_env:
            mock_env_cm = nullcontext()
        else:
            mock_env_cm = mock_env(home)

        with mock_env_cm:
            Path(home, ".cumulusci").mkdir()
            Path(home, ".cumulusci/cumulusci.yml").touch()
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
