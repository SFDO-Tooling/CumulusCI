import copy
import random
from pathlib import Path

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.config import OrgConfig


def random_sha():
    hash = random.getrandbits(128)
    return "%032x" % hash


def create_project_config(
    repo_name="TestRepo", repo_owner="TestOwner", repo_commit=None
):
    global_config = BaseGlobalConfig()
    project_config = DummyProjectConfig(
        global_config=global_config,
        repo_name=repo_name,
        repo_owner=repo_owner,
        repo_commit=repo_commit,
        config=copy.deepcopy(global_config.config),
    )
    keychain = BaseProjectKeychain(project_config, None)
    project_config.set_keychain(keychain)
    return project_config


class DummyProjectConfig(BaseProjectConfig):
    def __init__(
        self, global_config, repo_name, repo_owner, repo_commit=None, config=None
    ):
        repo_info = {
            "owner": repo_owner,
            "name": repo_name,
            "url": f"https://github.com/{repo_owner}/{repo_name}",
            "commit": repo_commit or random_sha(),
        }
        super(DummyProjectConfig, self).__init__(
            global_config, config, repo_info=repo_info
        )


class DummyOrgConfig(OrgConfig):
    def __init__(self, config=None, name=None, keychain=None):
        if not name:
            name = "test"
        super(DummyOrgConfig, self).__init__(config, name, keychain)

    def refresh_oauth_token(self, keychain, save=False):
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
    def get_service(self, name):
        return DummyService(name)

    config_local_dir = Path("/home/.cumulusci")
    project_cache_dir = Path("/home/project/.cci")
