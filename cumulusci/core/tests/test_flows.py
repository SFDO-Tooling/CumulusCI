""" Tests for the Flow engine """

import unittest

from collections import Callable

from cumulusci.core.flows import BaseFlow
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import OrgConfig


class TestBaseFlow(unittest.TestCase):
    """ Tests the expectations of a BaseFlow caller """

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.org_config = OrgConfig({'foo': 'bar'})

    def test_init(self):
        """ BaseFlow initializes and offers a logger """
        flow_config = FlowConfig({})
        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        self.assertEquals(hasattr(flow, 'logger'), True)

    def test_is_callable(self):
        """ BaseFlow exposes itself as a callable for use """
        flow_config = FlowConfig({})
        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        self.assertIsInstance(flow, Callable)

    def test_call_no_tasks(self):
        pass

    def test_call_one_task(self):
        pass

    def test_call_many_tasks(self):
        pass

    def test_call_task_not_found(self):
        pass
