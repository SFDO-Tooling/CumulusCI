import io
import os
from unittest import mock

from cumulusci.tasks.salesforce import SOQLQuery
from cumulusci.utils import temporary_dir

from .util import create_task


def test_run_task():
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
        task.bulk.get_all_results_for_query_batch.return_value = iter(
            [io.BytesIO(b"No results found.")]
        )
        task._run_task()

        task.bulk.query.assert_called_once()
        task.bulk.wait_for_batch.assert_called_once()
        task.bulk.close_job.assert_called_once()
        assert os.path.exists(os.path.join(path, "results.csv"))
