import unittest
from cumulusci.core.flows import BaseFlow
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import OrgConfig

class TestBaseFlow(unittest.TestCase):
    flow_class = BaseFlow

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.org_config = OrgConfig({'foo': 'bar'})

    def test_init(self):
        self._test_init()

    def _test_init(self):
        flow_config = FlowConfig({})
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        self.assertEquals(hasattr(flow, 'logger'), True)

    def test_call_no_tasks(self):
        self._test_call_no_tasks()

    def _test_call_no_tasks(self):
        pass

    def test_call_one_task(self):
        self._test_call_no_tasks()

    def _test_call_no_tasks(self):
        pass

    def test_call_many_tasks(self):
        self._test_call_many_tasks()

    def _test_call_many_tasks(self):
        pass

    def test_call_task_not_found(self):
        self._test_call_task_not_found()

    def _test_call_task_not_found(self):
        pass
