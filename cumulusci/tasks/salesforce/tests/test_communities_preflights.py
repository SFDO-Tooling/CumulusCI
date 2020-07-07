import unittest
from unittest.mock import Mock

from cumulusci.tasks.salesforce.communities_preflights import IsCommunitiesEnabled
from .util import create_task


class TestCommunitiesPreflights(unittest.TestCase):
    def test_community_preflight__positive(self):
        task = create_task(IsCommunitiesEnabled, {})

        task._init_task = Mock()
        task.sf = Mock()
        task.sf.describe.return_value = {
            "sobjects": [{"name": "Network"}, {"name": "Account"}]
        }

        task()

        assert task.return_values is True

    def test_community_preflight__negative(self):
        task = create_task(IsCommunitiesEnabled, {})

        task._init_task = Mock()
        task.sf = Mock()
        task.sf.describe.return_value = {"sobjects": [{"name": "Account"}]}

        task()

        assert task.return_values is False
