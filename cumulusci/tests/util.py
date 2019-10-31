import copy
import random

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.config import OrgConfig


def random_sha():
    hash = random.getrandbits(128)
    return "%032x" % hash


def create_project_config(repo_name="TestRepo", repo_owner="TestOwner"):
    global_config = BaseGlobalConfig()
    project_config = DummyProjectConfig(
        global_config=global_config,
        repo_name=repo_name,
        repo_owner=repo_owner,
        config=copy.deepcopy(global_config.config),
    )
    keychain = BaseProjectKeychain(project_config, None)
    project_config.set_keychain(keychain)
    return project_config


class DummyProjectConfig(BaseProjectConfig):
    def __init__(
        self, global_config, repo_name, repo_owner, repo_commit=None, config=None
    ):
        self._repo_name = repo_name
        self._repo_owner = repo_owner
        self._repo_commit = repo_commit
        self._init_config = config
        super(DummyProjectConfig, self).__init__(global_config, config)

    @property
    def repo_name(self):
        return self._repo_name

    @property
    def repo_owner(self):
        return self._repo_owner

    @property
    def repo_commit(self):
        if not self._repo_commit:
            self._repo_commit = random_sha()
        return self._repo_commit


class DummyOrgConfig(OrgConfig):
    def __init__(self, config=None, name=None):
        if not name:
            name = "test"
        super(DummyOrgConfig, self).__init__(config, name)

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
