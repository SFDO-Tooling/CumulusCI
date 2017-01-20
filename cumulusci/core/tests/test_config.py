import os
import shutil
import tempfile
import unittest

import mock
import nose
import yaml

from cumulusci.core.config import BaseConfig
from cumulusci.core.config import YamlGlobalConfig
from cumulusci.core.config import YamlProjectConfig
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import ProjectConfigNotFound

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
        expected_config['tasks']['newtesttask']['description'] = 'test description'
        self.assertEquals(config.config, expected_config)


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
        shutil.rmtree(self.tempdir_home)
        shutil.rmtree(self.tempdir_project)

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
            '        name: TestProject2\n'
        )
        self._create_project_config_local(content)

        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)
        self.assertNotEqual(config.config_project_local, {})
        self.assertEqual(config.project__package__name, 'TestProject2')
        self.assertEqual(config.project__package__namespace, 'testproject')
