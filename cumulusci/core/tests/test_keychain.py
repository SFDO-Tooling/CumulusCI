from __future__ import absolute_import
import json
import os
import shutil
import tempfile
import unittest

import mock
import nose
import yaml

from cumulusci.core.tests.utils import EnvironmentVarGuard

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.keychain import BaseEncryptedProjectKeychain
from cumulusci.core.keychain import EncryptedFileProjectKeychain
from cumulusci.core.keychain import EnvironmentProjectKeychain
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import ServiceNotValid
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import ProjectConfigNotFound

__location__ = os.path.dirname(os.path.realpath(__file__))


class TestBaseProjectKeychain(unittest.TestCase):

    keychain_class = BaseProjectKeychain

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.project_config.config['services'] = {
            'connected_app': {'attributes': {'test': {'required': True}}},
            'github': {'attributes': {'name': {'required': True}, 'password': {}}},
            'mrbelvedere': {'attributes': {'mr': {'required': True}}},
            'not_configured': {'attributes': {'foo': {'required': True}}},
        }
        self.project_config.project__name = 'TestProject'
        self.services = {
            'connected_app': ServiceConfig({'test': 'value'}),
            'github': ServiceConfig({'name': 'hub'}),
            'mrbelvedere': ServiceConfig({'mr': 'belvedere'}),
        }
        self.org_config = OrgConfig({'foo': 'bar'}, 'test')
        self.scratch_org_config = ScratchOrgConfig({'foo': 'bar', 'scratch': True}, 'test_scratch')
        self.key = '0123456789123456'

    def test_init(self):
        self._test_init()

    def _test_init(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEquals(keychain.project_config, self.project_config)
        self.assertEquals(keychain.key, self.key)

    def test_set_non_existant_service(self):
        self._test_set_non_existant_service()

    def _test_set_non_existant_service(self, project=False):
        keychain = self.keychain_class(self.project_config, self.key)
        with self.assertRaises(ServiceNotValid) as context:
            keychain.set_service(
                'doesnotexist', ServiceConfig({'name': ''}), project)

    def test_set_invalid_service(self):
        self._test_set_invalid_service()

    def _test_set_invalid_service(self, project=False):
        keychain = self.keychain_class(self.project_config, self.key)
        with self.assertRaises(ServiceNotValid) as context:
            keychain.set_service(
                'github', ServiceConfig({'name': ''}), project)

    def test_get_service_not_configured(self):
        self._test_get_service_not_configured()

    def _test_get_service_not_configured(self, project=False):
        keychain = self.keychain_class(self.project_config, self.key)
        with self.assertRaises(ServiceNotConfigured) as context:
            keychain.get_service('not_configured')

    def test_change_key(self):
        self._test_change_key()

    def _test_change_key(self):
        new_key = '9876543210987654'
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.org_config)
        keychain.set_service('connected_app', self.services['connected_app'])
        keychain.set_service('github', self.services['github'])
        keychain.set_service('mrbelvedere', self.services['mrbelvedere'])
        keychain.change_key(new_key)
        self.assertEquals(keychain.key, new_key)
        self.assertEquals(keychain.get_service(
            'connected_app').config, self.services['connected_app'].config)
        self.assertEquals(keychain.get_service(
            'github').config, self.services['github'].config)
        self.assertEquals(keychain.get_service(
            'mrbelvedere').config, self.services['mrbelvedere'].config)
        self.assertEquals(keychain.get_org(
            'test').config, self.org_config.config)

    def test_set_service_github(self):
        self._test_set_service_github()

    def _test_set_service_github(self, project=False):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_service('github', self.services['github'], project)
        self.assertEquals(keychain.get_service(
            'github').config, self.services['github'].config)

    def test_set_service_mrbelvedere(self):
        self._test_set_service_mrbelvedere()

    def _test_set_service_mrbelvedere(self, project=False):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_service('mrbelvedere', self.services[
                             'mrbelvedere'], project)
        self.assertEquals(keychain.get_service(
            'mrbelvedere').config, self.services['mrbelvedere'].config)

    def test_set_and_get_org(self):
        self._test_set_and_get_org()

    def _test_set_and_get_org(self, global_org=False):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.org_config, global_org)
        self.assertEquals(list(keychain.orgs.keys()), ['test'])
        self.assertEquals(keychain.get_org(
            'test').config, self.org_config.config)

    def test_set_and_get_scratch_org(self):
        self._test_set_and_get_org()

    def _test_set_and_get_scratch_org(self, global_org=False):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.scratch_org_config, global_org)
        self.assertEquals(list(keychain.orgs.keys()), ['test_scratch'])
        org = keychain.get_org('test_scratch')
        self.assertEquals(
            org.config,
            self.scratch_org_config.config,
        )
        self.assertEquals(
            org.__class__,
            ScratchOrgConfig,
        )

    def test_load_scratch_orgs_none(self):
        self._test_load_scratch_orgs_none()

    def _test_load_scratch_orgs_none(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEquals(list(keychain.orgs), [])

    def test_load_scratch_orgs_create_one(self):
        self._test_load_scratch_orgs_create_one()

    def _test_load_scratch_orgs_create_one(self):
        self.project_config.config['orgs'] = {}
        self.project_config.config['orgs']['scratch'] = {}
        self.project_config.config['orgs']['scratch']['test_scratch_auto'] = {}
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEquals(list(keychain.orgs), ['test_scratch_auto'])

    def test_load_scratch_orgs_existing_org(self):
        self._test_load_scratch_orgs_existing_org()

    def _test_load_scratch_orgs_existing_org(self):
        self.project_config.config['orgs'] = {}
        self.project_config.config['orgs']['scratch'] = {}
        self.project_config.config['orgs']['scratch']['test'] = {}
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(OrgConfig({}, 'test'))
        self.assertEquals(list(keychain.orgs), ['test'])
        org = keychain.get_org('test')
        self.assertEquals(org.scratch, None)

    def test_get_org_not_found(self):
        self._test_get_org_not_found()

    @nose.tools.raises(OrgNotFound)
    def _test_get_org_not_found(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEquals(keychain.get_org('test'), None)

    def test_get_default_org(self):
        self._test_get_default_org()

    def _test_get_default_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        org_config = self.org_config.config.copy()
        org_config = OrgConfig(org_config, 'test')
        org_config.config['default'] = True
        keychain.set_org(org_config)
        self.assertEquals(keychain.get_default_org()[
                          1].config, org_config.config)

    def test_get_default_org_no_default(self):
        self._test_get_default_org_no_default()

    def _test_get_default_org_no_default(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEquals(keychain.get_default_org()[1], None)

    def test_set_default_org(self):
        self._test_set_default_org()

    def _test_set_default_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        org_config = self.org_config.config.copy()
        org_config = OrgConfig(org_config, 'test')
        keychain.set_org(org_config)
        keychain.set_default_org('test')
        expected_org_config = org_config.config.copy()
        expected_org_config['default'] = True
        
        self.assertEquals(
            expected_org_config,
            keychain.get_default_org()[1].config,
        )

    def test_unset_default_org(self):
        self._test_unset_default_org()

    def _test_unset_default_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        org_config = self.org_config.config.copy()
        org_config = OrgConfig(org_config, 'test')
        org_config.config['default'] = True
        keychain.set_org(org_config)
        keychain.unset_default_org()
        self.assertEquals(keychain.get_default_org()[1], None)

    def test_list_orgs(self):
        self._test_list_orgs()

    def _test_list_orgs(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.org_config)
        self.assertEquals(keychain.list_orgs(), ['test'])

    def test_list_orgs_empty(self):
        self._test_list_orgs_empty()

    def _test_list_orgs_empty(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEquals(keychain.list_orgs(), [])


class TestEnvironmentProjectKeychain(TestBaseProjectKeychain):
    keychain_class = EnvironmentProjectKeychain

    def setUp(self):
        super(TestEnvironmentProjectKeychain, self).setUp()
        self.env = EnvironmentVarGuard()
        self._clean_env(self.env)
        self.env.set(
            '{}test'.format(self.keychain_class.org_var_prefix),
            json.dumps(self.org_config.config)
        )
        self.env.set(
            '{}connected_app'.format(self.keychain_class.service_var_prefix),
            json.dumps(self.services['connected_app'].config)
        )
        self.env.set(
            '{}github'.format(self.keychain_class.service_var_prefix),
            json.dumps(self.services['github'].config)
        )
        self.env.set(
            '{}mrbelvedere'.format(self.keychain_class.service_var_prefix),
            json.dumps(self.services['mrbelvedere'].config)
        )

    def _clean_env(self, env):
        for key, value in list(env.items()):
            if key.startswith(self.keychain_class.org_var_prefix):
                del env[key]
        for key, value in list(env.items()):
            if key.startswith(self.keychain_class.service_var_prefix):
                del env[key]

    def test_get_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEquals(list(keychain.orgs.keys()), ['test'])
        self.assertEquals(keychain.get_org(
            'test').config, self.org_config.config)

    def _test_list_orgs(self):
        with self.env:
            keychain = self.keychain_class(self.project_config, self.key)
            self.assertEquals(keychain.list_orgs(), ['test'])

    def test_list_orgs_empty(self):
        with EnvironmentVarGuard() as env:
            self._clean_env(env)
            env.set(
                '{}connected_app'.format(self.keychain_class.service_var_prefix),
                json.dumps(self.services['connected_app'].config)
            )
            self._test_list_orgs_empty()
   
    def test_load_scratch_org_config(self):
        with EnvironmentVarGuard() as env:
            self._clean_env(env)
            env.set(
                '{}test'.format(self.keychain_class.org_var_prefix),
                json.dumps(self.scratch_org_config.config)
            )
            keychain = self.keychain_class(self.project_config, self.key)
            self.assertEquals(keychain.list_orgs(), ['test'])
            self.assertEquals(keychain.orgs['test'].__class__, ScratchOrgConfig)

    def test_load_scratch_orgs_none(self):
        with EnvironmentVarGuard() as env:
            self._clean_env(env)
            self._test_load_scratch_orgs_none()

    def test_load_scratch_orgs_create_one(self):
        with EnvironmentVarGuard() as env:
            self._clean_env(env)
            self._test_load_scratch_orgs_create_one()

    def test_get_org_not_found(self):
        with EnvironmentVarGuard() as env:
            self._clean_env(env)
            self._test_get_org_not_found()

    def test_get_default_org(self):
        with EnvironmentVarGuard() as env:
            self._clean_env(env)
            org_config = self.org_config.config.copy()
            org_config['default'] = True
            self.env.set(
                '{}test'.format(self.keychain_class.org_var_prefix),
                json.dumps(org_config)
            )
            self._test_get_default_org()

    def test_set_default_org(self):
        """ The EnvironmentProjectKeychain does not persist default org settings """
        with EnvironmentVarGuard() as env:
            self._clean_env(env)
            org_config = self.org_config.config.copy()
            self.env.set(
                '{}test'.format(self.keychain_class.org_var_prefix),
                json.dumps(org_config)
            )
            keychain = self.keychain_class(self.project_config, self.key)
            keychain.set_default_org('test')
            expected_org_config = self.org_config.config.copy()
            expected_org_config['default'] = True
        
            self.assertEquals(
                None,
                keychain.get_default_org()[1],
            )
            


class TestBaseEncryptedProjectKeychain(TestBaseProjectKeychain):
    keychain_class = BaseEncryptedProjectKeychain

    def test_decrypt_config_no_config(self):
        keychain = self.keychain_class(self.project_config, self.key)
        config = keychain._decrypt_config(OrgConfig, None, extra=['test'])
        self.assertEquals(config.__class__, OrgConfig)
        self.assertEquals(config.config, {})


@mock.patch('os.path.expanduser')
class TestEncryptedFileProjectKeychain(TestBaseProjectKeychain):
    keychain_class = EncryptedFileProjectKeychain

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.project_config.config['services'] = {
            'connected_app': {'attributes': {'test': {'required': True}}},
            'github': {'attributes': {'git': {'required': True}, 'password': {}}},
            'mrbelvedere': {'attributes': {'mr': {'required': True}}},
            'not_configured': {'attributes': {'foo': {'required': True}}},
        }
        self.project_config.project__name = 'TestProject'
        self.project_name = 'TestProject'
        self.org_config = OrgConfig({'foo': 'bar'}, 'test')
        self.scratch_org_config = ScratchOrgConfig({'foo': 'bar', 'scratch': True}, 'test_scratch')
        self.services = {
            'connected_app': ServiceConfig({'test': 'value'}),
            'github': ServiceConfig({'git': 'hub'}),
            'mrbelvedere': ServiceConfig({'mr': 'belvedere'}),
        }
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
        with open(filename, 'w') as f:
            f.write(content)

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

    def test_set_invalid_service(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_invalid_service()

    def test_set_non_existant_service(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_non_existant_service()

    def test_get_service_not_configured(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_get_service_not_configured()

    def test_set_service_github(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_service_github()

    def test_set_service_github_project(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_service_github(True)

    def test_set_service_mrbelvedere(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_service_mrbelvedere()

    def test_set_service_mrbelvedere_project(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_service_mrbelvedere(True)

    def test_set_and_get_org(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_and_get_org()

    def test_set_and_get_scratch_org(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_and_get_scratch_org()

    def test_load_scratch_orgs_none(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_load_scratch_orgs_none()

    def test_load_scratch_orgs_create_one(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_load_scratch_orgs_create_one()

    def test_load_scratch_orgs_existing_org(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_load_scratch_orgs_existing_org()

    def test_set_and_get_org_global(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_and_get_org(True)

    def test_get_org_not_found(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_get_org_not_found()

    def test_get_default_org(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_get_default_org()

    def test_get_default_org_no_default(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_get_default_org_no_default()

    def test_set_default_org(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_set_default_org()

    def test_unset_default_org(self, mock_class):
        self._mk_temp_home()
        self._mk_temp_project()
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        self._test_unset_default_org()

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
