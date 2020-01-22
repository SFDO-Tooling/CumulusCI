from cumulusci.tasks.bulkdata.step import (
    Operation,
    Status,
    Result,
    download_file,
    BulkJobTaskMixin,
    QueryStep,
    BulkApiQueryStep,
    DmlStep,
    BulkApiDmlStep,
)

import io
import unittest
from unittest import mock


class test_download_file(unittest.TestCase):
    pass


class test_BulkDataJobTaskMixin(unittest.TestCase):
    pass


class test_BulkApiQueryStep(unittest.TestCase):
    def test_query(self):
        context = mock.Mock()
        query = BulkApiQueryStep("Contact", {}, context, "SELECT Id FROM Contact")

        query.query()

        context.bulk.create_query_job.assert_called_once_with(
            "Contact", contentType="CSV"
        )
        context.bulk.query.assert_called_once_with(
            context.bulk.create_query_job.return_value, "SELECT Id FROM Contact"
        )
        context.bulk.wait_for_batch.assert_called_once_with(
            context.bulk.create_query_job.return_value, context.bulk.query.return_value
        )
        context.bulk.close_job.assert_called_once_with(
            context.bulk.create_query_job.return_value
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_get_results(self, download_mock):
        context = mock.Mock()
        context.bulk.endpoint = "https://test"
        context.bulk.create_query_job.return_value = "JOB"
        context.bulk.query.return_value = "BATCH"
        context.bulk.get_query_batch_result_ids.return_value = "RESULT"

        download_mock.return_value = io.StringIO(
            """
        Id
        003000000000001
        003000000000002
        003000000000003
        """
        )
        query = BulkApiQueryStep("Contact", {}, context, "SELECT Id FROM Contact")
        query.query()

        results = list(query.get_results())

        context.bulk.get_query_batch_result_ids.assert_called_once_with(
            "BATCH", job_id="JOB"
        )
        download_mock.assert_called_once_with(
            f"https://test/job/JOB/batch/BATCH/result/RESULT"
        )

        assert results == [
            ["003000000000001"],
            ["003000000000002"],
            ["003000000000003"],
        ]
