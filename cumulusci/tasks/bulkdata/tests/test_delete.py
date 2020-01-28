import unittest

from unittest import mock
import responses

from cumulusci.tasks import bulkdata
from cumulusci.tasks.bulkdata.tests.test_bulkdata import _make_task
from cumulusci.core.exceptions import TaskOptionsError

BULK_DELETE_QUERY_RESULT = b"Id\n003000000000001".splitlines()
BULK_DELETE_RESPONSE = b'<root xmlns="http://ns"><id>4</id></root>'
BULK_BATCH_RESPONSE = '<root xmlns="http://ns"><batch><state>{}</state></batch></root>'


@mock.patch("cumulusci.tasks.bulkdata.delete.time.sleep", mock.Mock())
class TestDeleteData(unittest.TestCase):
    def _configure_mocks(self, query_job, query_batch, delete_job):
        api = mock.Mock()
        api.endpoint = "http://api"
        api.jobNS = "http://ns"
        api.create_query_job.return_value = query_job
        api.query.return_value = query_batch
        api.is_batch_done.side_effect = [False, True, False, True]
        api.get_all_results_for_query_batch.return_value = [BULK_DELETE_QUERY_RESULT]
        api.create_job.return_value = delete_job
        api.headers.return_value = {}
        responses.add(
            method="POST",
            url="http://api/job/3/batch",
            body=BULK_DELETE_RESPONSE,
            status=200,
        )
        api.job_status.return_value = {
            "numberBatchesCompleted": 1,
            "numberBatchesTotal": 1,
        }
        responses.add(
            method="GET",
            url="http://api/job/3/batch",
            body=BULK_BATCH_RESPONSE.format("InProgress"),
            status=200,
        )
        responses.add(
            method="GET",
            url="http://api/job/3/batch",
            body=BULK_BATCH_RESPONSE.format("Completed"),
            status=200,
        )
        return api

    @responses.activate
    def test_run(self):
        query_job = "1"
        query_batch = "2"
        delete_job = "3"

        api = self._configure_mocks(query_job, query_batch, delete_job)
        task = _make_task(bulkdata.DeleteData, {"options": {"objects": "Contact"}})

        def _init_class():
            task.bulk = api

        task._init_class = _init_class
        task()

        api.create_query_job.assert_called_once_with("Contact", contentType="CSV")
        api.query.assert_called_once_with(query_job, "SELECT Id FROM Contact")
        api.is_batch_done.assert_has_calls(
            [mock.call(query_batch, query_job), mock.call(query_batch, query_job)]
        )
        api.create_job.assert_called_once_with("Contact", "delete")
        api.close_job.assert_has_calls([mock.call(query_job), mock.call(delete_job)])

    @responses.activate
    def test_run_with_where(self):
        query_job = "1"
        query_batch = "2"
        delete_job = "3"

        api = self._configure_mocks(query_job, query_batch, delete_job)
        task = _make_task(
            bulkdata.DeleteData,
            {"options": {"objects": "Contact", "where": "city='Goshen'"}},
        )

        def _init_class():
            task.bulk = api

        task._init_class = _init_class
        task()

        api.create_query_job.assert_called_once_with("Contact", contentType="CSV")
        api.query.assert_called_once_with(
            query_job, "SELECT Id FROM Contact WHERE city='Goshen'"
        )
        api.is_batch_done.assert_has_calls(
            [mock.call(query_batch, query_job), mock.call(query_batch, query_job)]
        )
        api.create_job.assert_called_once_with("Contact", "delete")
        api.close_job.assert_has_calls([mock.call(query_job), mock.call(delete_job)])

    def test_create_job__no_records(self):
        task = _make_task(bulkdata.DeleteData, {"options": {"objects": "Contact"}})
        task._query_salesforce_for_records_to_delete = mock.Mock(return_value=[])
        task.logger = mock.Mock()
        task._create_job("Contact")
        task.logger.info.assert_called_with(
            "  No Contact objects found, skipping delete"
        )

    def test_parse_job_state(self):
        task = _make_task(bulkdata.DeleteData, {"options": {"objects": "Contact"}})
        api = mock.Mock()
        api.jobNS = "http://ns"
        task.bulk = api
        self.assertEqual(
            ("InProgress", None),
            task._parse_job_state(
                '<root xmlns="http://ns">'
                "  <batch><state>InProgress</state></batch>"
                "  <batch><state>Failed</state><stateMessage>test</stateMessage></batch>"
                "  <batch><state>Completed</state></batch>"
                "</root>"
            ),
        )
        self.assertEqual(
            ("Failed", ["test"]),
            task._parse_job_state(
                '<root xmlns="http://ns">'
                "  <batch><state>Failed</state><stateMessage>test</stateMessage></batch>"
                "  <batch><state>Completed</state></batch>"
                "</root>"
            ),
        )
        self.assertEqual(
            ("Completed", None),
            task._parse_job_state(
                '<root xmlns="http://ns">'
                "  <batch><state>Completed</state></batch>"
                "  <batch><state>Completed</state></batch>"
                "</root>"
            ),
        )
        self.assertEqual(
            ("Aborted", None),
            task._parse_job_state(
                '<root xmlns="http://ns">'
                "  <batch><state>Not Processed</state></batch>"
                "  <batch><state>Completed</state></batch>"
                "</root>"
            ),
        )

    @responses.activate
    def test_upload_batches__error(self):
        task = _make_task(bulkdata.DeleteData, {"options": {"objects": "Contact"}})
        api = mock.Mock()
        api.endpoint = "http://api"
        api.headers.return_value = {}
        api.raise_error.side_effect = Exception

        def _init_class():
            task.bulk = api

        task._init_class = _init_class
        responses.add(responses.POST, "http://api/job/1/batch", body=b"", status=500)
        with self.assertRaises(Exception):
            list(task._upload_batches("1", [{"Id": "1"}]))

    def test_validate_options(self):
        with self.assertRaises(TaskOptionsError):
            _make_task(bulkdata.DeleteData, {"options": {"objects": ""}})

        with self.assertRaises(TaskOptionsError):
            _make_task(
                bulkdata.DeleteData, {"options": {"objects": "a,b", "where": "x='y'"}}
            )
