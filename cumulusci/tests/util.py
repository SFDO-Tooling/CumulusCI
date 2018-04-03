from __future__ import unicode_literals
import os
import random
import tempfile
import zipfile

import yaml

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.config import OrgConfig
from cumulusci import __location__


def create_source_files():
    """."""
    path = tempfile.mkdtemp()
    with open(os.path.join(path, 'cumulusci.yml'), 'w') as f:
        f.write('foo')
    d = os.path.join(path, 'src', 'classes')
    os.makedirs(d)
    with open(os.path.join(d, 'foo.cls'), 'w') as f:
        f.write('foo')
    with open(os.path.join(d, 'foo-meta.xml'), 'w') as f:
        f.write('foo')
    return path

def create_zip_file(path):
    """Create a zip file in memory from a given path."""
    f_temp = tempfile.TemporaryFile()
    zip = zipfile.ZipFile(f_temp, 'w', zipfile.ZIP_DEFLATED)
    pwd = os.getcwd()
    os.chdir(path)
    for root, dirs, files in os.walk('.'):
        for file in files:
            zip.write(os.path.join(root, file))
    os.chdir(pwd)
    return zip

def random_sha():
    hash = random.getrandbits(128)
    return "%032x" % hash

def get_base_config():
    path = os.path.abspath(os.path.join(
            __location__,
            'cumulusci.yml'
        ))
    with open(path, 'r') as f:
        return yaml.load(f)

def create_project_config(repo_name, repo_owner):
    base_config = get_base_config()
    global_config = BaseGlobalConfig(base_config)
    project_config = DummyProjectConfig(
        global_config = global_config, 
        repo_name = repo_name,
        repo_owner = repo_owner,
        config = base_config,
    )
    keychain = BaseProjectKeychain(project_config, None)
    project_config.set_keychain(keychain)
    return project_config

class DummyProjectConfig(BaseProjectConfig):
    def __init__(self, global_config, repo_name, repo_owner, repo_commit=None, config=None):
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
            name = 'test'
        super(DummyOrgConfig, self).__init__(config, name)

    def refresh_oauth_token(self):
        pass
