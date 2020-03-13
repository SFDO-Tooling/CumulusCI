import unittest

from cumulusci.tasks.salesforce import DeployAndWaitForSharingRecalculation
from .util import create_task


class TestDeploy(unittest.TestCase):
    def test_init_options_sets_default_timeout(self):
        task = create_task(
            DeployAndWaitForSharingRecalculation,
            {
                "path": "path",
                "namespace_tokenize": "ns",
                "namespace_inject": "ns",
                "namespace_strip": "ns",
            },
        )

        self.assertEqual(int("600"), task.options.get("timeout"))

    def test_init_options_sets_timeout_as_int(self):
        timeout = "1234"
        task = create_task(
            DeployAndWaitForSharingRecalculation,
            {
                "timeout": timeout,
                "path": "path",
                "namespace_tokenize": "ns",
                "namespace_inject": "ns",
                "namespace_strip": "ns",
            },
        )

        self.assertEqual(int(timeout), task.options.get("timeout"))
