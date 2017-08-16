import os

import hiyapyco

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.config import OrgConfig
from cumulusci import __location__


def get_base_config():
    path = os.path.abspath(os.path.join(
            __location__,
            'cumulusci.yml'
        ))
    return hiyapyco.load(path)

def create_project_config(repo_name, repo_owner):
    base_config = get_base_config()
    global_config = BaseGlobalConfig(base_config)
    project_config = DummyProjectConfig(
        global_config, 
        repo_name,
        repo_owner,
        base_config,
    )
    keychain = BaseProjectKeychain(project_config, None)
    project_config.set_keychain(keychain)
    return project_config

class DummyProjectConfig(BaseProjectConfig):
    def __init__(self, global_config, repo_name, repo_owner, config=None):
        self._repo_name = repo_name
        self._repo_owner = repo_owner
        super(DummyProjectConfig, self).__init__(global_config, config)

    @property
    def repo_name(self):
        return self._repo_name

    @property
    def repo_owner(self):
        return self._repo_owner
        
class DummyOrgConfig(OrgConfig):
    def refresh_oauth_token(self):
        pass
