import copy
import gc
import json
import os
import random
import sys
import tracemalloc
from contextlib import contextmanager, nullcontext
from pathlib import Path
from unittest import mock

import responses
from requests import ReadTimeout

from cumulusci.core.config import BaseProjectConfig, OrgConfig, UniversalConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.bulkdata.tests import utils as bulkdata_utils


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


class DummyOrgConfig(OrgConfig):
    def __init__(self, config=None, name=None, keychain=None, global_org=False):
        if config is None:
            config = {
                "instance_url": "https://orgname.my.salesforce.com",
                "access_token": "pytest_sf_orgconnect_abc123",
                "id": "https://test.salesforce.com/id/00D0xORGID00000000/USERID",
                "username": "sfuser@example.com",
            }

        if not name:
            name = "test"
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


class DummyService(object):
    password = "password"

    def __init__(self, name):
        self.name = name


class DummyKeychain(object):
    def __init__(self, global_config_dir=None, cache_dir=None):
        self._global_config_dir = global_config_dir
        self._cache_dir = cache_dir

    @property
    def global_config_dir(self):
        return self._global_config_dir or Path.home() / "cumulusci"

    @property
    def cache_dir(self):
        return self._cache_dir or Path.home() / "project/.cci"

    def get_service(self, name):
        return DummyService(name)

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


class FakeSF:
    """Extremely simplistic mock of the Simple-Salesforce API

    Can be improved as needed over time.
    In particular, __getattr__ is not implemented yet.
    """

    fakes = {}

    def describe(self):
        return self._get_json("global_describe")

    @property
    def sf_version(self):
        return "47.0"

    def _get_json(self, fake_dataset):
        self.fakes[fake_dataset] = self.fakes.get("sobjname", None) or read_mock(
            fake_dataset
        )
        return self.fakes[fake_dataset]


def read_mock(name: str):
    base_path = Path(__file__).parent.parent / "tasks/bulkdata/tests"

    with (base_path / f"{name}.json").open("r") as f:
        return f.read()


def mock_describe_calls(domain="example.com"):
    def mock_sobject_describe(name: str):
        responses.add(
            method="GET",
            url=f"https://{domain}/services/data/v48.0/sobjects/{name}/describe",
            body=read_mock(name),
            status=200,
        )

    responses.add(
        method="GET",
        url=f"https://{domain}/services/data",
        body=json.dumps([{"version": "40.0"}, {"version": "48.0"}]),
        status=200,
    )
    responses.add(
        method="GET",
        url=f"https://{domain}/services/data",
        body=json.dumps([{"version": "40.0"}, {"version": "48.0"}]),
        status=200,
    )

    responses.add(
        method="GET",
        url=f"https://{domain}/services/data/v48.0/sobjects",
        body=read_mock("global_describe"),
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
        task.bulk = bulkdata_utils.FakeBulkAPI()
        task.sf = salesforce_client

    with mock.patch(
        "cumulusci.core.config.OrgConfig.is_person_accounts_enabled",
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
