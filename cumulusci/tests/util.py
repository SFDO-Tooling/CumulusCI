import copy
import gc
import json
import os
import random
import sys
import tracemalloc
from contextlib import contextmanager, nullcontext
from functools import lru_cache
from pathlib import Path
from unittest import mock

import responses
import yaml
from requests import ReadTimeout

from cumulusci.core.config import (
    BaseConfig,
    BaseProjectConfig,
    OrgConfig,
    UniversalConfig,
)
from cumulusci.core.keychain import BaseProjectKeychain

CURRENT_SF_API_VERSION = "55.0"
from cumulusci.tasks.bulkdata.tests.utils import FakeBulkAPI


def random_sha():
    hash = random.getrandbits(128)
    return "%032x" % hash


def create_project_config(
    repo_name="TestRepo",
    repo_owner="TestOwner",
    repo_commit=None,
    namespace=None,
):
    universal_config = UniversalConfig()
    project_config = DummyProjectConfig(
        universal_config=universal_config,
        repo_name=repo_name,
        repo_owner=repo_owner,
        repo_commit=repo_commit,
        config=copy.deepcopy(universal_config.config),
    )
    if namespace:
        project_config.config["project"]["package"]["namespace"] = namespace
    keychain = BaseProjectKeychain(project_config, None)
    project_config.set_keychain(keychain)
    return project_config


class DummyProjectConfig(BaseProjectConfig):
    def __init__(
        self, universal_config, repo_name, repo_owner, repo_commit=None, config=None
    ):
        repo_info = {
            "owner": repo_owner,
            "name": repo_name,
            "url": f"https://github.com/{repo_owner}/{repo_name}",
            "commit": repo_commit or random_sha(),
        }
        super(DummyProjectConfig, self).__init__(
            universal_config, config, repo_info=repo_info
        )


DEFAULT_CONFIG = {
    "instance_url": "https://orgname.my.salesforce.com",
    "access_token": "pytest_sf_orgconnect_abc123",
    "id": "https://test.salesforce.com/id/00D0xORGID00000000/USERID",
    "username": "sfuser@example.com",
}


class DummyOrgConfig(OrgConfig):
    def __init__(self, config=None, name=None, keychain=None, global_org=False):
        config = {**DEFAULT_CONFIG, **(config or {})}
        name = name or "test"
        super(DummyOrgConfig, self).__init__(config, name, keychain, global_org)

    def refresh_oauth_token(self, keychain):
        pass


class DummyLogger(object):
    def __init__(self):
        self.out = []

    def log(self, msg, *args):
        self.out.append(msg % args)

    # Compatibility with various logging methods like info, warning, etc
    def __getattr__(self, name):
        return self.log

    def get_output(self):
        return "\n".join(self.out)


class DummyService(BaseConfig):
    password = "dummy_password"
    client_id = "ZOOMZOOM"

    def __init__(self, name, alias):
        self.name = name
        super().__init__()


class DummyKeychain(BaseProjectKeychain):
    def __init__(self, global_config_dir=None, cache_dir=None, project_config=None):
        self._global_config_dir = global_config_dir
        self._cache_dir = cache_dir
        if not project_config:
            project_config = create_project_config()
            project_config.keychain = self
        super().__init__(project_config, "XYZZY")

    @property
    def global_config_dir(self):
        return self._global_config_dir or Path.home() / "cumulusci"

    @property
    def cache_dir(self):
        return self._cache_dir or Path.home() / "project/.cci"

    def get_service(self, name, alias=None):
        return DummyService(name, alias)

    def set_org(self, org: OrgConfig, global_org: bool):
        pass


@contextmanager
def assert_max_memory_usage(max_usage):
    "Assert that a test does not exceed a certain memory threshold"
    tracemalloc.start()
    yield
    current, peak = tracemalloc.get_traced_memory()
    if peak > max_usage:
        big_objs(traced_only=True)
        assert peak < max_usage, ("Peak incremental memory usage was high:", peak)
    tracemalloc.stop()


def big_objs(traced_only=False):

    big_objs = (
        (sys.getsizeof(obj), obj)
        for obj in gc.get_objects()
        if sys.getsizeof(obj) > 20000
        and (tracemalloc.get_object_traceback(obj) if traced_only else True)
    )
    for size, obj in big_objs:
        print(type(obj), size, tracemalloc.get_object_traceback(obj))


class FakeSObjectProxy:
    def __init__(self, describe_data):
        self.describe_data = describe_data

    def describe(self):
        return self.describe_data


class FakeSF:
    """Simplistic mock of the Simple-Salesforce API

    Can be improved as needed over time.
    """

    fakes = {}
    headers = {}
    session = mock.Mock()
    base_url = "https://fakesf.example.org/"

    def describe(self):
        return self._get_json("Global")

    @property
    def sf_version(self):
        return CURRENT_SF_API_VERSION

    def _get_json(self, fake_dataset):
        self.fakes[fake_dataset] = self.fakes.get(fake_dataset, None) or json.loads(
            read_mock(fake_dataset)
        )
        return self.fakes[fake_dataset]

    def __getattr__(self, name):
        return FakeSObjectProxy(self._get_json(name))


@lru_cache  # change to @cache when Python 3.9 is allowed
def read_mock(name: str):
    base_path = Path(__file__).parent.parent / "tests/shared_cassettes"

    with (base_path / f"GET_sobjects_{name}_describe.yaml").open("r") as f:
        return yaml.safe_load(f)["response"]["body"]["string"]


def mock_describe_calls(domain="example.com", version=CURRENT_SF_API_VERSION):
    def mock_sobject_describe(name: str):
        responses.add(
            method="GET",
            url=f"https://{domain}/services/data/v{version}/sobjects/{name}/describe",
            body=read_mock(name),
            status=200,
        )

    responses.add(
        method="GET",
        url=f"https://{domain}/services/data",
        body=json.dumps([{"version": version}]),
        status=200,
    )
    responses.add(
        method="GET",
        url=f"https://{domain}/services/data",
        body=json.dumps([{"version": version}]),
        status=200,
    )

    responses.add(
        method="GET",
        url=f"https://{domain}/services/data/v{version}/sobjects",
        body=read_mock("Global"),
        status=200,
    )

    for sobject in [
        "Account",
        "Contact",
        "Opportunity",
        "OpportunityContactRole",
        "Case",
    ]:
        mock_sobject_describe(sobject)


@contextmanager
def mock_salesforce_client(task, *, is_person_accounts_enabled=False):
    mock_describe_calls("test.salesforce.com")

    real_init = task._init_task
    salesforce_client = FakeSF()

    def _init_task():
        real_init()
        task.bulk = FakeBulkAPI()
        task.sf = salesforce_client

    with mock.patch(
        "cumulusci.core.config.org_config.OrgConfig.is_person_accounts_enabled",
        lambda: is_person_accounts_enabled,
    ), mock.patch.object(task, "_init_task", _init_task):
        yield


@contextmanager
def mock_env(home, cumulusci_key="0123456789ABCDEF"):
    real_homedir = str(Path.home())
    patches = {
        "HOME": home,
        "USERPROFILE": home,
        "REAL_HOME": real_homedir,
        "CUMULUSCI_SYSTEM_CERTS": "True",
    }

    with mock.patch("pathlib.Path.home", lambda: Path(home)), mock.patch.dict(
        os.environ, patches
    ):
        # don't use the real CUMULUSCI_KEY for tests
        if "CUMULUSCI_KEY" in os.environ:
            del os.environ["CUMULUSCI_KEY"]
        if cumulusci_key is not None:
            # do use a fake one, if it was supplied
            os.environ["REAL_CUMULUSCI_KEY"] = os.environ.get("CUMULUSCI_KEY", "")
            os.environ["CUMULUSCI_KEY"] = cumulusci_key

        yield


def unmock_env():
    """Reset homedir and CCI environment variable or leave them if they weren't changed"""
    if "REAL_HOME" in os.environ:
        cci_key = os.environ.get("REAL_CUMULUSCI_KEY") or None
        homedir = os.environ["REAL_HOME"]
        return mock_env(homedir, cci_key)
    else:
        return nullcontext()


class FakeUnreliableRequestHandler:
    """Fake a request handler which fails its second request."""

    counter = 0

    def __init__(self, response=None, exception=ReadTimeout):
        self.response = response
        self.exception = exception

    def request_callback(self, request):
        should_return_error = self.counter == 1  # fail the second request of X
        self.counter += 1
        if should_return_error:
            raise self.exception()
        else:
            return (
                200,
                {"Last-Modified": "Wed, 01 Jan 2000 01:01:01 GMT"},
                json.dumps(self.real_reliable_request_callback(request)),
            )

    def real_reliable_request_callback(self, request):
        return self.response


CURRENT_SF_API_VERSION = (
    CURRENT_SF_API_VERSION  # quiet linter and export to other modules
)
