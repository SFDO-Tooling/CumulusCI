import ast
import httplib
import os
import shutil
import tempfile
import unittest
import urllib

from xml.dom.minidom import parseString

import requests
import responses

from nose.tools import raises

from cumulusci.tests.util import create_project_config
from cumulusci.tests.util import DummyOrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.tasks import BaseTask
from cumulusci.salesforce_api.metadata import BaseMetadataApiCall
from cumulusci.salesforce_api.exceptions import MetadataApiError

class DummyResponse(object):
    pass

class TestBaseMetadataApiCall(unittest.TestCase):

    def setUp(self):

        # Set up the mock values
        self.repo_name = 'TestRepo'
        self.repo_owner = 'TestOwner'
        self.repo_api_url = 'https://api.github.com/repos/{}/{}'.format(
            self.repo_owner,
            self.repo_name,
        )
        self.branch = 'master'

        # Create the project config
        self.project_config = create_project_config(
            self.repo_name,
            self.repo_owner,
        )

    def _create_task(self, task_config=None, org_config=None):
        if not task_config:
            task_config = {}
        if not org_config:
            org_config = {}
        task = BaseTask(
            project_config = self.project_config,
            task_config = TaskConfig(task_config),
            org_config = DummyOrgConfig(org_config),
        )
        return task

    def _mock_call_mdapi(self, api, response, status_code=None):
        if not status_code:
            status_code = 200
        responses.add(
            method=responses.POST,
            url=api._build_endpoint_url(),
            body=response,
            status=status_code,
            content_type='text/xml; charset=utf-8',
        )
        return response

    def _create_instance(self, task, api_version=None):
        return BaseMetadataApiCall(
            task,
            api_version = api_version,
        )

    def test_init(self):
        task = self._create_task()
        api = self._create_instance(task) 
        self.assertEquals(api.task, task)
        self.assertEquals(api.api_version, self.project_config.project__package__api_version)

    def test_build_endpoint_url(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task) 
        self.assertEquals(
            api._build_endpoint_url(),
            '{}/services/Soap/m/{}/{}'.format(
                org_config['instance_url'],
                self.project_config.project__package__api_version,
                task.org_config.org_id,
            )
        )
        
    def test_build_endpoint_url_mydomain(self):
        org_config = {
            'instance_url': 'https://test-org.na12.my.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task) 
        self.assertEquals(
            api._build_endpoint_url(),
            'https://na12.salesforce.com/services/Soap/m/{}/{}'.format(
                self.project_config.project__package__api_version,
                task.org_config.org_id,
            )
        )
    
    def test_build_endpoint_url_apiversion(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
        }
        task = self._create_task(org_config=org_config)
        api_version = "41.0"
        api = self._create_instance(task, api_version=api_version) 
        self.assertEquals(
            api._build_endpoint_url(),
            '{}/services/Soap/m/{}/{}'.format(
                org_config['instance_url'],
                api_version,
                task.org_config.org_id,
            )
        )

    def test_build_envelope_result(self):
        task = self._create_task()
        api = self._create_instance(task)
        api.soap_envelope_result = '%(process_id)s'
        api.process_id = '123'
        self.assertEquals(
            api._build_envelope_result(),
            api.process_id,
        )

    def test_build_envelope_result_no_envelope(self):
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEquals(
            api._build_envelope_result(),
            None,
        )
        
    def test_build_envelope_start(self):
        task = self._create_task()
        api = self._create_instance(task)
        api.soap_envelope_start = '{api_version}'
        self.assertEquals(
            api._build_envelope_start(),
            str(self.project_config.project__package__api_version),
        )

    def test_build_envelope_start_no_envelope(self):
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEquals(
            api._build_envelope_start(),
            None,
        )

    def test_build_envelope_status(self):
        task = self._create_task()
        api = self._create_instance(task)
        api.soap_envelope_status = '%(process_id)s'
        api.process_id = '123'
        self.assertEquals(
            api._build_envelope_status(),
            api.process_id,
        )

    def test_build_envelope_status_no_envelope(self):
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEquals(
            api._build_envelope_status(),
            None,
        )

    def test_build_headers(self):
        action = 'foo'
        message = '12345678'
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEquals(
            api._build_headers(action, message),
            {
                u'Content-Type': u'text/xml; charset=UTF-8',
                u'Content-Length': '8',
                u'SOAPAction': u'foo',
            }
        )

    def test_get_element_value(self):
        task = self._create_task()
        api = self._create_instance(task)
        dom = parseString('<foo>bar</foo>')
        self.assertEquals(
            api._get_element_value(dom, 'foo'),
            'bar',
        )
        
    def test_get_element_value_not_found(self):
        task = self._create_task()
        api = self._create_instance(task)
        dom = parseString('<foo>bar</foo>')
        self.assertEquals(
            api._get_element_value(dom, 'baz'),
            None,
        )
        
    def test_get_element_value_empty(self):
        task = self._create_task()
        api = self._create_instance(task)
        dom = parseString('<foo />')
        self.assertEquals(
            api._get_element_value(dom, 'foo'),
            None,
        )

    def test_get_check_interval(self):
        task = self._create_task()
        api = self._create_instance(task)
        api.check_num = 1
        self.assertEquals(
            api._get_check_interval(),
            1,
        )
        api.check_num = 10
        self.assertEquals(
            api._get_check_interval(),
            4,
        )
        
    @raises(NotImplementedError)    
    def test_get_response_no_start_env(self):
        task = self._create_task()
        api = self._create_instance(task)
        api._get_response()
       
    @responses.activate 
    def test_get_response_no_status(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
            'access_token': '0123456789',
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        api.soap_envelope_start = '{api_version}'
        response = '<?xml version="1.0" encoding="UTF-8"?><foo />'
        self._mock_call_mdapi(api, response)
        resp = api._get_response()
        self.assertEquals(
            resp.content,
            response
        )
        
    @responses.activate
    @raises(MetadataApiError) 
    def test_get_response_faultcode(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
            'access_token': '0123456789',
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        api.soap_envelope_start = '{api_version}'
        response = '<?xml version="1.0" encoding="UTF-8"?><faultcode>foo</faultcode>'
        self._mock_call_mdapi(api, response)
        resp = api._get_response()

    @responses.activate
    @raises(MetadataApiError) 
    def test_get_response_faultcode_and_string(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
            'access_token': '0123456789',
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        api.soap_envelope_start = '{api_version}'
        response = '<?xml version="1.0" encoding="UTF-8"?>'
        response += '\n<test>'
        response += '\n  <faultcode>foo</faultcode>'
        response += '\n  <faultstring>bar</faultstring>'
        response += '\n</test>'
        self._mock_call_mdapi(api, response)
        resp = api._get_response()

    @responses.activate
    @raises(MetadataApiError) 
    def test_get_response_faultcode_invalid_session_no_refresh(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
            'access_token': '0123456789',
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        api.soap_envelope_start = '{api_version}'
        response = '<?xml version="1.0" encoding="UTF-8"?><faultcode>sf:INVALID_SESSION_ID</faultcode>'
        self._mock_call_mdapi(api, response)
        resp = api._get_response()
        self.assertEquals(
            api.status,
            'Failed',
        )

    @responses.activate
    def test_get_response_faultcode_invalid_session_refresh(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
            'access_token': '0123456789',
            'refresh_token': 'abcdefghij',
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        api.soap_envelope_start = '{api_version}'
        response1 = '<?xml version="1.0" encoding="UTF-8"?><faultcode>sf:INVALID_SESSION_ID</faultcode>'
        self._mock_call_mdapi(api, response1)
        response2 = '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>'
        self._mock_call_mdapi(api, response2)
        resp = api._get_response()
        self.assertEquals(
            resp.content,
            response2,
        )

    @responses.activate
    @raises(MetadataApiError)
    def test_get_response_start_error_500(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
            'access_token': '0123456789',
        }
        status_code = httplib.INTERNAL_SERVER_ERROR # HTTP Error 500
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        api.soap_envelope_start = '{api_version}'
        api.soap_envelope_status = '%(process_id)s'

        response = '<?xml version="1.0" encoding="UTF-8"?><foo>start</foo>'
        self._mock_call_mdapi(api, response, status_code)

        resp = api._get_response()

    @responses.activate
    @raises(MetadataApiError)
    def test_get_response_status_error_500(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
            'access_token': '0123456789',
        }
        status_code = httplib.INTERNAL_SERVER_ERROR # HTTP Error 500
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        api.soap_envelope_start = '{api_version}'
        api.soap_envelope_status = '%(process_id)s'

        response = '<?xml version="1.0" encoding="UTF-8"?><id>1234567890</id>'
        self._mock_call_mdapi(api, response)
        response_status = '<?xml version="1.0" encoding="UTF-8"?><foo>status</foo>'
        self._mock_call_mdapi(api, response, status_code)

        resp = api._get_response()

    @responses.activate
    @raises(MetadataApiError)
    def test_get_response_status_error_500(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
            'access_token': '0123456789',
        }
        status_code = httplib.INTERNAL_SERVER_ERROR # HTTP Error 500
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        api.soap_envelope_start = '{api_version}'
        api.soap_envelope_status = '%(process_id)s'

        response = '<?xml version="1.0" encoding="UTF-8"?><id>1234567890</id>'
        self._mock_call_mdapi(api, response)
        response_status = '<?xml version="1.0" encoding="UTF-8"?><foo>status</foo>'
        self._mock_call_mdapi(api, response, status_code)

        resp = api._get_response()

    @responses.activate
    def test_get_response_status_no_loop(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
            'access_token': '0123456789',
        }
        status_code = httplib.INTERNAL_SERVER_ERROR # HTTP Error 500
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        api.soap_envelope_start = '{api_version}'
        api.soap_envelope_status = '%(process_id)s'
        api.soap_envelope_result = '%(process_id)s'

        response = '<?xml version="1.0" encoding="UTF-8"?><id>1234567890</id>'
        self._mock_call_mdapi(api, response)
        response_status = '<?xml version="1.0" encoding="UTF-8"?><done>true</done>'
        self._mock_call_mdapi(api, response_status)
        response_result = '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>'
        self._mock_call_mdapi(api, response_result)

        resp = api._get_response()

        self.assertEquals(
            resp.content,
            response_result,
        )

    @responses.activate
    def test_get_response_status_loop_twice(self):
        org_config = {
            'instance_url': 'https://na12.salesforce.com',
            'id': 'https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC',
            'access_token': '0123456789',
        }
        status_code = httplib.INTERNAL_SERVER_ERROR # HTTP Error 500
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        api.soap_envelope_start = '{api_version}'
        api.soap_envelope_status = '%(process_id)s'
        api.soap_envelope_result = '%(process_id)s'
        api.check_interval = 0

        response = '<?xml version="1.0" encoding="UTF-8"?><id>1234567890</id>'
        self._mock_call_mdapi(api, response)
        response_status = '<?xml version="1.0" encoding="UTF-8"?><done>false</done>'
        self._mock_call_mdapi(api, response_status)
        response_status = '<?xml version="1.0" encoding="UTF-8"?><done>false</done>'
        self._mock_call_mdapi(api, response_status)
        response_status = '<?xml version="1.0" encoding="UTF-8"?><done>true</done>'
        self._mock_call_mdapi(api, response_status)
        response_result = '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>'
        self._mock_call_mdapi(api, response_result)

        resp = api._get_response()

        self.assertEquals(
            resp.content,
            response_result,
        )

        self.assertEquals(
            api.status,
            'Done',
        )

        self.assertEquals(
            api.check_num,
            4,
        )

    def test_process_response_status_no_done_element(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = DummyResponse()
        response.status_code = 200
        response.content = '<?xml version="1.0" encoding="UTF-8"?><foo>status</foo>'
        res = api._process_response_status(response)
        self.assertEquals(
            api.status,
            'Failed',
        )
        self.assertEquals(
            res.content,
            response.content,
        )

    def test_process_response_status_done_is_true(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = DummyResponse()
        response.status_code = 200
        response.content = '<?xml version="1.0" encoding="UTF-8"?><done>true</done>'
        res = api._process_response_status(response)
        self.assertEquals(
            api.status,
            'Done',
        )
        self.assertEquals(
            res.content,
            response.content,
        )

    def test_process_response_status_pending(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = DummyResponse()
        response.status_code = 200
        response.content = '<?xml version="1.0" encoding="UTF-8"?><done>false</done>'
        res = api._process_response_status(response)
        self.assertEquals(
            api.status,
            'Pending',
        )
        self.assertEquals(
            res.content,
            response.content,
        )

    def test_process_response_status_in_progress(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = DummyResponse()
        response.status_code = 200
        response.content = '<?xml version="1.0" encoding="UTF-8"?><done>false</done>'
        api.status = 'InProgress'
        res = api._process_response_status(response)
        self.assertEquals(
            api.status,
            'InProgress',
        )
        self.assertEquals(
            res.content,
            response.content,
        )

    def test_process_response_status_in_progress_state_detail(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = DummyResponse()
        response.status_code = 200
        response.content = '<?xml version="1.0" encoding="UTF-8"?><test><done>false</done><stateDetail>Deploy log goes here</stateDetail></test>'
        api.status = 'InProgress'
        res = api._process_response_status(response)
        self.assertEquals(
            api.status,
            'InProgress',
        )
        self.assertEquals(
            res.content,
            response.content,
        )
