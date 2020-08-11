import copy
import random

from cumulusci.core.config import UniversalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.config import OrgConfig


def random_sha():
    hash = random.getrandbits(128)
    return "%032x" % hash


def create_project_config(
    repo_name="TestRepo", repo_owner="TestOwner", repo_commit=None
):
    universal_config = UniversalConfig()
    project_config = DummyProjectConfig(
        universal_config=universal_config,
        repo_name=repo_name,
        repo_owner=repo_owner,
        repo_commit=repo_commit,
        config=copy.deepcopy(universal_config.config),
    )
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
