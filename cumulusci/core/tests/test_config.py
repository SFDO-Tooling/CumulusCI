from __future__ import absolute_import
from datetime import datetime
from datetime import timedelta
import io
import os
import shutil
import tempfile
import unittest

import mock
import nose
import yaml

from cumulusci.core.config import BaseConfig
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import YamlGlobalConfig
from cumulusci.core.config import YamlProjectConfig
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import ProjectConfigNotFound
from cumulusci.core.exceptions import ScratchOrgException

__location__ = os.path.dirname(os.path.realpath(__file__))


class TestBaseConfig(unittest.TestCase):

    def test_getattr_toplevel_key(self):
        config = BaseConfig()
        config.config = {'foo': 'bar'}
        self.assertEquals(config.foo, 'bar')

    def test_getattr_toplevel_key_missing(self):
        config = BaseConfig()
        config.config = {}
        self.assertEquals(config.foo, None)

    def test_getattr_child_key(self):
        config = BaseConfig()
        config.config = {'foo': {'bar': 'baz'}}
        self.assertEquals(config.foo__bar, 'baz')

    def test_getattr_child_parent_key_missing(self):
        config = BaseConfig()
        config.config = {}
        self.assertEquals(config.foo__bar, None)

    def test_getattr_child_key_missing(self):
        config = BaseConfig()
        config.config = {'foo': {}}
        self.assertEquals(config.foo__bar, None)

    def test_getattr_default_toplevel(self):
        config = BaseConfig()
        config.config = {'foo': 'bar'}
        config.defaults = {'foo': 'default'}
        self.assertEquals(config.foo, 'bar')

    def test_getattr_default_toplevel_missing_default(self):
        config = BaseConfig()
        config.config = {'foo': 'bar'}
        config.defaults = {}
        self.assertEquals(config.foo, 'bar')

    def test_getattr_default_toplevel_missing_config(self):
        config = BaseConfig()
        config.config = {}
        config.defaults = {'foo': 'default'}
        self.assertEquals(config.foo, 'default')

    def test_getattr_default_child(self):
        config = BaseConfig()
        config.config = {'foo': {'bar': 'baz'}}
        config.defaults = {'foo__bar': 'default'}
        self.assertEquals(config.foo__bar, 'baz')

    def test_getattr_default_child_missing_default(self):
        config = BaseConfig()
        config.config = {'foo': {'bar': 'baz'}}
        config.defaults = {}
        self.assertEquals(config.foo__bar, 'baz')

    def test_getattr_default_child_missing_config(self):
        config = BaseConfig()
        config.config = {}
        config.defaults = {'foo__bar': 'default'}
        self.assertEquals(config.foo__bar, 'default')

    def test_getattr_empty_search_path(self):
        config = BaseConfig()
        config.search_path = []
        self.assertEquals(config.foo, None)

    def test_getattr_search_path_no_match(self):
        config = BaseConfig()
        config.search_path = ['_first', '_middle', '_last']
        config._first = {}
        config._middle = {}
        config._last = {}
        self.assertEquals(config.foo, None)

    def test_getattr_search_path_match_first(self):
        config = BaseConfig()
        config.search_path = ['_first', '_middle', '_last']
        config._first = {'foo': 'bar'}
        config._middle = {}
        config._last = {}
        self.assertEquals(config.foo, 'bar')

    def test_getattr_search_path_match_middle(self):
        config = BaseConfig()
        config.search_path = ['_first', '_middle', '_last']
        config._first = {}
        config._middle = {'foo': 'bar'}
        config._last = {}
        self.assertEquals(config.foo, 'bar')

    def test_getattr_search_path_match_last(self):
        config = BaseConfig()
        config.search_path = ['_first', '_middle', '_last']
        config._first = {}
        config._middle = {}
        config._last = {'foo': 'bar'}
        self.assertEquals(config.foo, 'bar')


@mock.patch('os.path.expanduser')
class TestYamlGlobalConfig(unittest.TestCase):

    def setUp(self):
        self.tempdir_home = tempfile.mkdtemp()

    def _create_global_config_local(self, content):
        self.tempdir_home = tempfile.mkdtemp()
        global_local_dir = os.path.join(
            self.tempdir_home,
            '.cumulusci',
        )
        os.makedirs(global_local_dir)
        filename = os.path.join(global_local_dir,
                                YamlGlobalConfig.config_filename)
        self._write_file(filename, content)

    def _write_file(self, filename, content):
        with open(filename, 'w') as f:
            f.write(content)

    def test_load_global_config_no_local(self, mock_class):
        mock_class.return_value = self.tempdir_home
        config = YamlGlobalConfig()
        with open(__location__ + '/../../cumulusci.yml', 'r') as f_expected_config:
            expected_config = yaml.load(f_expected_config)
        self.assertEquals(config.config, expected_config)

    def test_load_global_config_empty_local(self, mock_class):
        self._create_global_config_local('')
        mock_class.return_value = self.tempdir_home

        config = YamlGlobalConfig()
        with open(__location__ + '/../../cumulusci.yml', 'r') as f_expected_config:
            expected_config = yaml.load(f_expected_config)
        self.assertEquals(config.config, expected_config)

    def test_load_global_config_with_local(self, mock_class):
        local_yaml = 'tasks:\n    newtesttask:\n        description: test description'
        self._create_global_config_local(local_yaml)
        mock_class.return_value = self.tempdir_home

        config = YamlGlobalConfig()
        with open(__location__ + '/../../cumulusci.yml', 'r') as f_expected_config:
            expected_config = yaml.load(f_expected_config)
        expected_config['tasks']['newtesttask'] = {}
        expected_config['tasks']['newtesttask'][
            'description'] = 'test description'
        self.assertEquals(config.config, expected_config)        


class DummyContents(object):
    def __init__(self, content):
        self.decoded = content

class DummyRepository(object):
    default_branch = 'master'
    _api = 'http://'

    def __init__(self, owner, name, contents):
        self.owner = owner
        self.name = name
        self.html_url = 'https://github.com/{}/{}'.format(owner, name)
        self._contents = contents

    def contents(self, path, **kw):
        try:
            return self._contents[path]
        except KeyError:
            raise AssertionError(
                'Accessed unexpected file: {}'.format(path))

    def _build_url(self, *args, **kw):
        return self._api

    def _get(self, url):
        res = mock.Mock()
        res.json.return_value = {
            'name': '2',
        }
        return res

CUMULUSCI_TEST_REPO = DummyRepository(
    'SalesforceFoundation',
    'CumulusCI-Test',
    {
        'cumulusci.yml': DummyContents("""
project:
    name: CumulusCI-Test
    package:
        name: Cumulus-Test
        namespace: ccitest
    git:
        repo_url: https://github.com/SalesforceFoundation/CumulusCI-Test
    dependencies:
        - github: https://github.com/SalesforceFoundation/CumulusCI-Test-Dep
"""),
        'unpackaged/pre': {'pre': ''},
        'src': {'src': ''},
        'unpackaged/post': {'post': ''},
    }
)

CUMULUSCI_TEST_DEP_REPO = DummyRepository(
    'SalesforceFoundation',
    'CumulusCI-Test-Dep',
    {
        'cumulusci.yml': DummyContents("""
project:
    name: CumulusCI-Test-Dep
    package:
        name: Cumulus-Test-Dep
        namespace: ccitestdep
    git:
        repo_url: https://github.com/SalesforceFoundation/CumulusCI-Test-Dep
"""),
        'unpackaged/pre': {},
        'src': {},
        'unpackaged/post': {},
    }
)

class DummyGithub(object):
    def repository(self, owner, name):
        if name == 'CumulusCI-Test':
            return CUMULUSCI_TEST_REPO
        elif name == 'CumulusCI-Test-Dep':
            return CUMULUSCI_TEST_DEP_REPO
        else:
            raise AssertionError('Unexpected repository: {}'.format(name))

class DummyService(object):
    password = 'password'

    def __init__(self, name):
        self.name = name

class DummyKeychain(object):
    def get_service(self, name):
        return DummyService(name)

class TestBaseProjectConfig(unittest.TestCase):

    def test_process_github_dependency(self):
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
        config.get_github_api = DummyGithub
        config.keychain = DummyKeychain()

        result = config.process_github_dependency({
            'github': 'https://github.com/SalesforceFoundation/CumulusCI-Test',
            'unmanaged': True,
        })
        self.assertEqual(result, [
            {
                u'headers': {u'Authorization': u'token password'},
                u'namespace_inject': None,
                u'namespace_strip': None,
                u'namespace_tokenize': None,
                u'subfolder': u'CumulusCI-Test-master/unpackaged/pre/pre',
                u'unmanaged': True,
                u'zip_url': u'https://github.com/SalesforceFoundation/CumulusCI-Test/archive/master.zip',
            },
            {u'version': '2', u'namespace': 'ccitestdep'},
            {
                u'headers': {u'Authorization': u'token password'},
                u'namespace_inject': None,
                u'namespace_strip': None,
                u'namespace_tokenize': None,
                u'subfolder': u'CumulusCI-Test-master/src',
                u'unmanaged': True,
                u'zip_url': u'https://github.com/SalesforceFoundation/CumulusCI-Test/archive/master.zip',
            },
            {
                u'headers': {u'Authorization': u'token password'},
                u'namespace_inject': 'ccitest',
                u'namespace_strip': None,
                u'namespace_tokenize': None,
                u'subfolder': u'CumulusCI-Test-master/unpackaged/post/post',
                u'unmanaged': True,
                u'zip_url': u'https://github.com/SalesforceFoundation/CumulusCI-Test/archive/master.zip',
            },
        ])


@mock.patch('os.path.expanduser')
class TestYamlProjectConfig(unittest.TestCase):

    def _create_git_config(self):

        filename = os.path.join(self.tempdir_project, '.git', 'config')
        content = (
            '[remote "origin"]\n' +
            '  url = git@github.com:TestOwner/{}'.format(self.project_name)
        )
        self._write_file(filename, content)

        filename = os.path.join(self.tempdir_project, '.git', 'HEAD')
        content = 'ref: refs/heads/{}'.format(self.current_branch)
        self._write_file(filename, content)

        dirname = os.path.join(self.tempdir_project, '.git', 'refs', 'heads')
        os.makedirs(dirname)
        filename = os.path.join(dirname, 'master')
        content = (self.current_commit)
        self._write_file(filename, content)

    def _create_project_config(self):
        filename = os.path.join(
            self.tempdir_project,
            YamlProjectConfig.config_filename,
        )
        content = (
            'project:\n' +
            '    name: TestRepo\n' +
            '    package:\n' +
            '        name: TestProject\n' +
            '        namespace: testproject\n'
        )
        self._write_file(filename, content)

    def _create_project_config_local(self, content):
        project_local_dir = os.path.join(
            self.tempdir_home,
            '.cumulusci',
            self.project_name,
        )
        os.makedirs(project_local_dir)
        filename = os.path.join(project_local_dir,
                                YamlProjectConfig.config_filename)
        self._write_file(filename, content)

    def _write_file(self, filename, content):
        with open(filename, 'w') as f:
            f.write(content)

    def setUp(self):
        self.tempdir_home = tempfile.mkdtemp()
        self.tempdir_project = tempfile.mkdtemp()
        self.project_name = 'TestRepo'
        self.current_commit = 'abcdefg1234567890'
        self.current_branch = 'master'

    def tearDown(self):
        pass

    @nose.tools.raises(NotInProject)
    def test_load_project_config_not_repo(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)

    @nose.tools.raises(ProjectConfigNotFound)
    def test_load_project_config_no_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)

    def test_load_project_config_empty_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        self._create_git_config()
        # create empty project config file
        filename = os.path.join(self.tempdir_project,
                                YamlProjectConfig.config_filename)
        content = ''
        self._write_file(filename, content)

        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)
        self.assertEquals(config.config_project, {})

    def test_load_project_config_valid_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)
        self.assertEquals(config.project__package__name, 'TestProject')
        self.assertEquals(config.project__package__namespace, 'testproject')

    def test_repo_owner(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)
        self.assertEquals(config.repo_owner, 'TestOwner')

    def test_repo_branch(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)
        self.assertEquals(config.repo_branch, self.current_branch)

    def test_repo_commit(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)
        self.assertEquals(config.repo_commit, self.current_commit)

    def test_load_project_config_local(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        # create local project config file
        content = (
            'project:\n' +
            '    package:\n' +
            '        api_version: 10\n'
        )
        self._create_project_config_local(content)

        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)
        self.assertNotEqual(config.config_project_local, {})
        self.assertEqual(config.project__package__api_version, 10)

    def test_load_additional_yaml(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        # create local project config file
        content = (
            'project:\n' +
            '    package:\n' +
            '        api_version: 10\n'
        )

        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config, additional_yaml = content)
        self.assertNotEqual(config.config_additional_yaml, {})
        self.assertEqual(config.project__package__api_version, 10)

@mock.patch('sarge.Command')
class TestScratchOrgConfig(unittest.TestCase):

    def test_scratch_info(self, Command):
        result = b'''{
    "result": {
        "instanceUrl": "url",
        "accessToken": "access!token",
        "username": "username",
        "password": "password"
    }
}'''
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b''),
            stdout=io.BytesIO(result),
            returncode=0,
        )

        config = ScratchOrgConfig({'username': 'test'}, 'test')
        info = config.scratch_info

        self.assertEqual(info, {
            'access_token': 'access!token',
            'instance_url': 'url',
            'org_id': 'access',
            'password': 'password',
            'username': 'username',
        })
        self.assertIs(info, config._scratch_info)
        self.assertDictContainsSubset(info, config.config)
        self.assertTrue(config._scratch_info_date)

    def test_scratch_info_memoized(self, Command):
        config = ScratchOrgConfig({'username': 'test'}, 'test')
        config._scratch_info = _marker = object()
        info = config.scratch_info
        self.assertIs(info, _marker)

    def test_scratch_info_non_json_response(self, Command):
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b''),
            stdout=io.BytesIO(b'<html></html>'),
            returncode=0,
        )

        config = ScratchOrgConfig({'username': 'test'}, 'test')
        with self.assertRaises(ScratchOrgException):
            config.scratch_info

    def test_scratch_info_command_error(self, Command):
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b'error'),
            stdout=io.BytesIO(b'out'),
            returncode=1,
        )

        config = ScratchOrgConfig({'username': 'test'}, 'test')

        try:
            config.scratch_info
        except ScratchOrgException as err:
            self.assertEqual(str(err), '\nstderr:\nerror\nstdout:\nout')
        else:
            self.fail('Expected ScratchOrgException')

    def test_scratch_info_password_from_config(self, Command):
        result = b'''{
    "result": {
        "instanceUrl": "url",
        "accessToken": "access!token",
        "username": "username"
    }
}'''
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b''),
            stdout=io.BytesIO(result),
            returncode=0,
        )

        config = ScratchOrgConfig({
                'username': 'test',
                'password': 'password'
            }, 'test')
        info = config.scratch_info

        self.assertEqual(info['password'], 'password')

    def test_access_token(self, Command):
        config = ScratchOrgConfig({}, 'test')
        _marker = object()
        config._scratch_info = {
            'access_token': _marker,
        }
        self.assertIs(config.access_token, _marker)

    def test_instance_url(self, Command):
        config = ScratchOrgConfig({}, 'test')
        _marker = object()
        config._scratch_info = {
            'instance_url': _marker,
        }
        self.assertIs(config.instance_url, _marker)

    def test_org_id_from_config(self, Command):
        config = ScratchOrgConfig({'org_id': 'test'}, 'test')
        self.assertEqual(config.org_id, 'test')

    def test_org_id_from_scratch_info(self, Command):
        config = ScratchOrgConfig({}, 'test')
        _marker = object()
        config._scratch_info = {
            'org_id': _marker
        }
        self.assertIs(config.org_id, _marker)

    def test_user_id_from_config(self, Command):
        config = ScratchOrgConfig({'user_id': 'test'}, 'test')
        self.assertEqual(config.user_id, 'test')

    def test_user_id_from_org(self, Command):
        sf = mock.Mock()
        sf.query_all.return_value = {
            'records': [
                {
                    'Id': 'test',
                },
            ],
        }

        config = ScratchOrgConfig({'username': 'test_username'}, 'test')
        config._scratch_info = {
            'instance_url': 'test_instance',
            'access_token': 'token',
        }
        # This is ugly...since ScratchOrgConfig is in a module
        # with the same name that is imported in cumulusci.core.config's
        # __init__.py, we have no way to externally grab the
        # module without going through the function's globals.
        with mock.patch.dict(
                ScratchOrgConfig.user_id.fget.__globals__,
                Salesforce=mock.Mock(return_value=sf)):
            self.assertEqual(config.user_id, 'test')

    def test_password_from_config(self, Command):
        config = ScratchOrgConfig({'password': 'test'}, 'test')
        self.assertEqual(config.password, 'test')

    def test_pasword_from_scratch_info(self, Command):
        config = ScratchOrgConfig({}, 'test')
        _marker = object()
        config._scratch_info = {
            'password': _marker
        }
        self.assertIs(config.password, _marker)

    def test_days(self, Command):
        config = ScratchOrgConfig({'days': 2}, 'test')
        self.assertEqual(config.days, 2)

    def test_days_default(self, Command):
        config = ScratchOrgConfig({}, 'test')
        self.assertEqual(config.days, 1)

    def test_expired(self, Command):
        config = ScratchOrgConfig({'days': 1}, 'test')
        now = datetime.now()
        config.date_created = now
        self.assertFalse(config.expired)
        config.date_created = now - timedelta(days=2)
        self.assertTrue(config.expired)

    def test_expires(self, Command):
        config = ScratchOrgConfig({'days': 1}, 'test')
        now = datetime.now()
        config.date_created = now
        self.assertEquals(config.expires, now + timedelta(days=1))

    def test_days_alive(self, Command):
        config = ScratchOrgConfig({}, 'test')
        config.date_created = datetime.now()
        self.assertEquals(config.days_alive, 1)

    def test_create_org(self, Command):
        out = b'Successfully created scratch org: ORG_ID, username: USERNAME'
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(out),
            stderr=io.BytesIO(b''),
            returncode=0,
        )

        config = ScratchOrgConfig({
                'config_file': 'tmp',
                'set_password': True,
            }, 'test')
        config.generate_password = mock.Mock()
        config.create_org()

        p.run.assert_called_once()
        self.assertEqual(config.config['org_id'], 'ORG_ID')
        self.assertEqual(config.config['username'], 'USERNAME')
        self.assertIn('date_created', config.config)
        config.generate_password.assert_called_once()
        self.assertTrue(config.config['created'])
        self.assertEqual(config.scratch_org_type, 'workspace')

    def test_create_org_no_config_file(self, Command):
        config = ScratchOrgConfig({}, 'test')
        self.assertEqual(config.create_org(), None)
        Command.assert_not_called()

    def test_create_org_command_error(self, Command):
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(b''),
            stderr=io.BytesIO(b'error'),
            returncode=1,
        )

        config = ScratchOrgConfig({'config_file': 'tmp'}, 'test')
        with self.assertRaises(ScratchOrgException):
            config.create_org()

    def test_generate_password(self, Command):
        p = mock.Mock(
            stderr=io.BytesIO(b'error'),
            stdout=io.BytesIO(b'out'),
            returncode=0,
        )
        Command.return_value = p

        config = ScratchOrgConfig({'username': 'test'}, 'test')
        config.generate_password()

        p.run.assert_called_once()

    def test_generate_password_failed(self, Command):
        p = mock.Mock()
        p.stderr = io.BytesIO(b'error')
        p.stdout = io.BytesIO(b'out')
        p.returncode = 1
        Command.return_value = p

        config = ScratchOrgConfig({'username': 'test'}, 'test')
        config.logger = mock.Mock()
        config.generate_password()

        config.logger.warn.assert_called_once()

    def test_generate_password_skips_if_failed(self, Command):
        config = ScratchOrgConfig({'username': 'test'}, 'test')
        config.password_failed = True
        config.generate_password()
        Command.assert_not_called()

    def test_delete_org(self, Command):
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(b'info'),
            stderr=io.BytesIO(b''),
            returncode=0,
        )

        config = ScratchOrgConfig({'username': 'test', 'created': True}, 'test')
        config.delete_org()

        self.assertFalse(config.config['created'])
        self.assertIs(config.config['username'], None)

    def test_delete_org_not_created(self, Command):
        config = ScratchOrgConfig({'created': False}, 'test')
        config.delete_org()
        Command.assert_not_called()

    def test_delete_org_error(self, Command):
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(b'An error occurred deleting this org'),
            stderr=io.BytesIO(b''),
            returncode=1,
        )

        config = ScratchOrgConfig({'username': 'test', 'created': True}, 'test')
        with self.assertRaises(ScratchOrgException):
            config.delete_org()

    def test_force_refresh_oauth_token(self, Command):
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(b''),
            stderr=io.BytesIO(b''),
            returncode=0,
        )

        config = ScratchOrgConfig({'username': 'test'}, 'test')
        config.force_refresh_oauth_token()

        p.run.assert_called_once()

    def test_force_refresh_oauth_token_error(self, Command):
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(b'error'),
            stderr=io.BytesIO(b''),
            returncode=1,
        )

        config = ScratchOrgConfig({'username': 'test'}, 'test')
        with self.assertRaises(ScratchOrgException):
            config.force_refresh_oauth_token()

    def test_refresh_oauth_token(self, Command):
        result = b'''{
    "result": {
        "instanceUrl": "url",
        "accessToken": "access!token",
        "username": "username",
        "password": "password"
    }
}'''
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(result),
            stderr=io.BytesIO(b''),
            returncode=0
        )

        config = ScratchOrgConfig({'username': 'test'}, 'test')
        config._scratch_info = {}
        config._scratch_info_date = datetime.now() - timedelta(days=1)
        config.force_refresh_oauth_token = mock.Mock()

        config.refresh_oauth_token(keychain=None)

        config.force_refresh_oauth_token.assert_called_once()
        self.assertTrue(config._scratch_info)
