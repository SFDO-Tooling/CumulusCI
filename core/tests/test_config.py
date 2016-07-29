import os
import tempfile
import unittest

import nose
import yaml

from core.config import BaseConfig
from core.config import YamlGlobalConfig
from core.config import YamlProjectConfig
from core.exceptions import NotInProject
from core.exceptions import ProjectConfigNotFound

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

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
        config.search_path = ['_first','_middle','_last']
        config._first = {}
        config._middle = {}
        config._last = {}
        self.assertEquals(config.foo, None)
        
    def test_getattr_search_path_match_first(self):
        config = BaseConfig()
        config.search_path = ['_first','_middle','_last']
        config._first = {'foo': 'bar'}
        config._middle = {}
        config._last = {}
        self.assertEquals(config.foo, 'bar')

    def test_getattr_search_path_match_middle(self):
        config = BaseConfig()
        config.search_path = ['_first','_middle','_last']
        config._first = {}
        config._middle = {'foo': 'bar'}
        config._last = {}
        self.assertEquals(config.foo, 'bar')
        
    def test_getattr_search_path_match_last(self):
        config = BaseConfig()
        config.search_path = ['_first','_middle','_last']
        config._first = {}
        config._middle = {}
        config._last = {'foo': 'bar'}
        self.assertEquals(config.foo, 'bar')

class TestYamlGlobalConfig(unittest.TestCase):
    def test_load_global_config(self):
        config = YamlGlobalConfig()

        f_expected_config = open(__location__ + '/../../cumulusci.yml', 'r')
        expected_config = yaml.load(f_expected_config)

        self.assertEquals(config.config, expected_config)

class TestYamlProjectConfig(unittest.TestCase):

    @nose.tools.raises(NotInProject)
    def test_load_project_config_not_repo(self):
        directory = tempfile.mkdtemp()
        os.chdir(directory)
        global_config = YamlGlobalConfig()

        config = YamlProjectConfig(global_config)

    @nose.tools.raises(ProjectConfigNotFound)
    def test_load_project_config_no_config(self):
        directory = tempfile.mkdtemp()
        os.mkdir(os.path.join(directory, '.git'))
        os.chdir(directory)
        global_config = YamlGlobalConfig()

        config = YamlProjectConfig(global_config)

    def test_load_project_config_empty_config(self):
        directory = tempfile.mkdtemp()
        os.mkdir(os.path.join(directory, '.git'))
        open(os.path.join(directory, YamlProjectConfig.config_filename), 'w').write('')
        os.chdir(directory)
        global_config = YamlGlobalConfig()

        config = YamlProjectConfig(global_config)
        self.assertEquals(config.config, {})

    def test_load_project_config_valid_config(self):
        config_yaml = "project:\n    name: TestProject\n    namespace: testproject\n"
        directory = tempfile.mkdtemp()
        os.mkdir(os.path.join(directory, '.git'))
        open(os.path.join(directory, YamlProjectConfig.config_filename), 'w').write(config_yaml)
        os.chdir(directory)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)
        self.assertEquals(config.project__name, 'TestProject')
        self.assertEquals(config.project__namespace, 'testproject')
