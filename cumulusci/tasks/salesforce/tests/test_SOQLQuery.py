import io
import mock
import os
import unittest

from cumulusci.tasks.salesforce import SOQLQuery
from cumulusci.utils import temporary_dir
from .util import create_task


class TestSOQLQuery(unittest.TestCase):
    def test_run_task(self):
        with temporary_dir() as path:
            task = create_task(
                SOQLQuery,
                {
                    "object": "Account",
                    "query": "SELECT Id FROM Account",
                    "result_file": "results.csv",
                },
            )
            task.bulk = mock.Mock()
            task.bulk.get_batch_result_iter.return_value = ["Id", "ID"]
            task()
            task.bulk.query.assert_called_once()
            task.bulk.wait_for_batch.assert_called_once()
            task.bulk.close_job.assert_called_once()
            self.assertTrue(os.path.exists(os.path.join(path, "results.csv")))
