from __future__ import absolute_import
import unittest

import mock
import nose

from cumulusci.core.config import BaseConfig
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import BaseTaskFlowConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import TaskNotFoundError, FlowNotFoundError


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


class TestBaseTaskFlowConfig(unittest.TestCase):
    def setUp(self):
        self.task_flow_config = BaseTaskFlowConfig({
            'tasks': {
                'deploy': {'description': 'Deploy Task'},
                'manage': {},
                'control': {},
            },
            'flows' : {
                'coffee': {'description': 'Coffee Flow'},
                'juice': {'description': 'Juice Flow'}
            }
        })

    def test_list_tasks(self):
        tasks = self.task_flow_config.list_tasks()
        self.assertEqual(len(tasks), 3)
        deploy = [task for task in tasks if task['name'] == 'deploy'][0]
        self.assertEqual(deploy['description'], 'Deploy Task')

    def test_get_task(self):
        task = self.task_flow_config.get_task('deploy')
        self.assertIsInstance(task, BaseConfig)
        self.assertDictContainsSubset({'description': 'Deploy Task'}, task.config)

    def test_no_task(self):
        with self.assertRaises(TaskNotFoundError):
            self.task_flow_config.get_task('robotic_superstar')

    def test_get_flow(self):
        flow = self.task_flow_config.get_flow('coffee')
        self.assertIsInstance(flow, BaseConfig)
        self.assertDictContainsSubset({'description': 'Coffee Flow'}, flow.config)

    def test_no_flow(self):
        with self.assertRaises(FlowNotFoundError):
            self.task_flow_config.get_flow('water')

    def test_list_flows(self):
        flows = self.task_flow_config.list_flows()
        self.assertEqual(len(flows), 2)
        coffee = [flow for flow in flows if flow['name'] == 'coffee'][0]
        self.assertEqual(coffee['description'], 'Coffee Flow')
