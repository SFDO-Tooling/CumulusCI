from datetime import datetime
import json
import os
import shutil
import unittest

import mock
import responses

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.tasks import bulkdata
from cumulusci.tests.util import DummyOrgConfig
from cumulusci.utils import temporary_dir

class TestEpochType(unittest.TestCase):

    def test_process_bind_param(self):
        obj = bulkdata.EpochType()
        dt = datetime(1970, 1, 1, 0, 0, 1)
        result = obj.process_bind_param(dt, None)
        self.assertEquals(1000, result)

    def test_process_result_value(self):
        obj = bulkdata.EpochType()
        result = obj.process_result_value(1000, None)
        self.assertEquals(datetime(1970, 1, 1, 0, 0, 1), result)

BULK_DELETE_QUERY_RESULT = b'Id\n003000000000001'.splitlines()
BULK_DELETE_RESPONSE = b'<root xmlns="http://ns"><id>4</id></root>'

def _make_task(task_class, task_config):
    task_config = TaskConfig(task_config)
    global_config = BaseGlobalConfig()
    project_config = BaseProjectConfig(global_config)
    org_config = DummyOrgConfig({
        'instance_url': 'example.com',
        'access_token': 'abc123',
    }, 'test')
    return task_class(project_config, task_config, org_config)

class TestDeleteData(unittest.TestCase):

    @responses.activate
    def test_run(self):
        api = mock.Mock()
        api.endpoint = 'http://api'
        api.jobNS = 'http://ns'
        api.create_query_job.return_value = query_job = '1'
        api.query.return_value = query_batch = '2'
        api.is_batch_done.side_effect = [False, True, False, True]
        api.get_all_results_for_query_batch.return_value = [BULK_DELETE_QUERY_RESULT]
        api.create_delete_job.return_value = delete_job = '3'
        api.headers.return_value = {}
        delete_batch = '4'
        responses.add(
            method='POST',
            url='http://api/job/3/batch',
            body=BULK_DELETE_RESPONSE,
            status=200,
        )

        task = _make_task(bulkdata.DeleteData, {
            'options': {
                'objects': 'Contact'
            }
        })
        task.bulk = api

        task()

        api.create_query_job.assert_called_once_with('Contact', contentType='CSV')
        api.query.assert_called_once_with(query_job, "select Id from Contact")
        api.is_batch_done.assert_has_calls([
            mock.call(query_batch, query_job),
            mock.call(query_batch, query_job),
            mock.call(delete_batch, delete_job),
            mock.call(delete_batch, delete_job),
        ])
        api.create_delete_job.assert_called_once_with('Contact', contentType='CSV')
        api.close_job.assert_has_calls([
            mock.call(query_job),
            mock.call(delete_job),
        ])


class TestLoadData(unittest.TestCase):

    @responses.activate
    def test_run(self):
        api = mock.Mock()
        api.endpoint = 'http://api'
        api.create_insert_job.side_effect = ['1', '3']
        api.post_batch.side_effect = ['2', '4']
        api.is_batch_done.side_effect = [False, True, True]
        api.headers.return_value = {}
        responses.add(
            method='GET',
            url='http://api/job/1/batch/2/result',
            body=b'Id\n1',
            status=200,
        )
        responses.add(
            method='GET',
            url='https://example.com/services/data/vNone/query/?q=SELECT+Id+FROM+RecordType+WHERE+SObjectType%3D%27Account%27AND+DeveloperName+%3D+%27HH_Account%27+LIMIT+1',
            body=json.dumps({
                'records': [
                    {
                        'Id': '1',
                    }
                ]
            }),
            status=200,
        )
        responses.add(
            method='GET',
            url='http://api/job/3/batch/4/result',
            body=b'Id\n1',
            status=200,
        )

        base_path = os.path.dirname(__file__)
        db_path = os.path.join(base_path, 'testdata.db')
        mapping_path = os.path.join(base_path, 'mapping.yml')
        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, 'testdata.db')
            shutil.copyfile(db_path, tmp_db_path)

            task = _make_task(bulkdata.LoadData, {
                'options': {
                    'database_url': 'sqlite:///{}'.format(tmp_db_path),
                    'mapping': mapping_path,
                }
            })
            task.bulk = api
            task()

            contact = task.session.query(task.tables['contacts']).one()
            self.assertEquals('1', contact.sf_id)
            task.session.close()


HOUSEHOLD_QUERY_RESULT = b'Id\n1'.splitlines()
CONTACT_QUERY_RESULT = b'Id,AccountId\n2,1'.splitlines()

class TestQueryData(unittest.TestCase):

    @responses.activate
    def test_run(self):
        api = mock.Mock()
        api.endpoint = 'http://api'
        api.create_query_job.side_effect = ['1', '3']
        api.query.side_effect = ['2', '4']
        api.get_all_results_for_query_batch.side_effect = [
            [HOUSEHOLD_QUERY_RESULT],
            [CONTACT_QUERY_RESULT],
        ]

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, 'mapping.yml')

        task = _make_task(bulkdata.QueryData, {
            'options': {
                'database_url': 'sqlite://',  # in memory
                'mapping': mapping_path,
            }
        })
        task.bulk = api
        task()

        contact = task.session.query(task.models['contacts']).one()
        self.assertEquals('2', contact.sf_id)
        self.assertEquals('1', contact.household_id)
