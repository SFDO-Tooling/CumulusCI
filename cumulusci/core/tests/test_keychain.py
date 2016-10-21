import os
import shutil
import tempfile
import unittest

import mock
import nose
import yaml

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.keychain import BaseEncryptedProjectKeychain
from cumulusci.core.keychain import EncryptedFileProjectKeychain
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import ProjectConfigNotFound

__location__ = os.path.dirname(os.path.realpath(__file__))


class TestBaseProjectKeychain(unittest.TestCase):

    keychain_class = BaseProjectKeychain

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.connected_app_config = ConnectedAppOAuthConfig({'test': 'value'})
        self.org_config = OrgConfig({'foo': 'bar'})
        self.key = '0123456789123456'

    def test_init(self):
        self._test_init()

    def _test_init(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEquals(keychain.project_config, self.project_config)
        self.assertEquals(keychain.key, self.key)

    def test_change_key(self):
        self._test_change_key()

    def _test_change_key(self):
        new_key = '9876543210987654'
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org('test', self.org_config)
        keychain.set_connected_app(self.connected_app_config)
        keychain.change_key(new_key)
        self.assertEquals(keychain.key, new_key)
        self.assertEquals(keychain.get_connected_app().config, self.connected_app_config.config)
        self.assertEquals(keychain.get_org('test').config, self.org_config.config)

    def test_set_connected_app(self):
        self._test_set_connected_app()

    def _test_set_connected_app(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_connected_app(self.connected_app_config)
        self.assertEquals(keychain.get_connected_app().config, {'test': 'value'})

    def test_set_and_get_org(self):
        self._test_set_and_get_org()

    def _test_set_and_get_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org('test', self.org_config)
        self.assertEquals(keychain.orgs.keys(), ['test'])
        self.assertEquals(keychain.get_org('test').config, self.org_config.config)

    def test_get_org_not_found(self):
        self._test_get_org_not_found()

    @nose.tools.raises(OrgNotFound)
    def _test_get_org_not_found(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEquals(keychain.get_org('test'), None)

    def test_list_orgs(self):
        self._test_list_orgs()

    def _test_list_orgs(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org('test', self.org_config)
        self.assertEquals(keychain.list_orgs(), ['test'])
    
    def test_list_orgs_empty(self):
        self._test_list_orgs_empty()

    def _test_list_orgs_empty(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEquals(keychain.list_orgs(), [])


class TestBaseEncryptedProjectKeychain(TestBaseProjectKeychain):
    keychain_class = BaseEncryptedProjectKeychain

@mock.patch('os.path.expanduser')
class TestEncryptedFileProjectKeychain(TestBaseProjectKeychain):
    keychain_class = EncryptedFileProjectKeychain

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.project_name = 'TestRepo'
        self.connected_app_config = ConnectedAppOAuthConfig({'test': 'value'})
        self.org_config = OrgConfig()
        self.key = '0123456789123456'

    def _mk_temp_home(self):
        self.tempdir_home = tempfile.mkdtemp()
        global_local_dir = os.path.join(
            self.tempdir_home,
            '.cumulusci',
        )
        os.makedirs(global_local_dir)

    def _mk_temp_project(self):
        self.tempdir_project = tempfile.mkdtemp()
        git_dir = os.path.join(
            self.tempdir_project,
            '.git',
        )
        os.makedirs(git_dir)
        self._create_git_config()

    def _create_git_config(self):
        filename = os.path.join(self.tempdir_project, '.git', 'config')
        content = (
            '[remote "origin"]\n' +
            '  url = git@github.com:TestOwner/{}'.format(self.project_name)
        )
        self._write_file(filename, content)

    def _write_file(self, filename, content):
        f = open(filename, 'w')
        f.write(content)
        f.close()

    def test_init(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_init()

    def test_change_key(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_change_key()

    def test_set_connected_app(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_connected_app()

    def test_set_and_get_org(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_and_get_org()

    def test_get_org_not_found(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_get_org_not_found()

    def test_list_orgs(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_list_orgs()

    def test_list_orgs_empty(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_list_orgs_empty()
