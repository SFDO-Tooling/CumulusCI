import http.client
import io
import unittest

from collections import defaultdict
from requests import Response
from xml.dom.minidom import parseString
import responses
import datetime

from cumulusci.tests.util import create_project_config
from cumulusci.tests.util import DummyOrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import ApexTestException
from cumulusci.core.tasks import BaseTask
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.salesforce_api.exceptions import MetadataParseError
from cumulusci.salesforce_api.exceptions import MetadataComponentFailure
from cumulusci.salesforce_api.metadata import BaseMetadataApiCall
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.metadata import ApiListMetadata
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.salesforce_api.metadata import ApiRetrieveInstalledPackages
from cumulusci.salesforce_api.metadata import ApiRetrievePackaged
from cumulusci.salesforce_api.package_zip import BasePackageZipBuilder
from cumulusci.salesforce_api.package_zip import CreatePackageZipBuilder
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.salesforce_api.tests.metadata_test_strings import deploy_status_envelope
from cumulusci.salesforce_api.tests.metadata_test_strings import deploy_result
from cumulusci.salesforce_api.tests.metadata_test_strings import deploy_result_failure
from cumulusci.salesforce_api.tests.metadata_test_strings import (
    list_metadata_start_envelope,
)
from cumulusci.salesforce_api.tests.metadata_test_strings import list_metadata_result
from cumulusci.salesforce_api.tests.metadata_test_strings import (
    list_metadata_result_bad_val,
)
from cumulusci.salesforce_api.tests.metadata_test_strings import (
    retrieve_packaged_start_envelope,
)
from cumulusci.salesforce_api.tests.metadata_test_strings import (
    retrieve_unpackaged_start_envelope,
)
from cumulusci.salesforce_api.tests.metadata_test_strings import retrieve_result
from cumulusci.salesforce_api.tests.metadata_test_strings import result_envelope
from cumulusci.salesforce_api.tests.metadata_test_strings import status_envelope


class DummyPackageZipBuilder(BasePackageZipBuilder):
    def _populate_zip(self):
        return


class BaseTestMetadataApi(unittest.TestCase):
    api_class = BaseMetadataApiCall
    envelope_start = None
    envelope_status = status_envelope
    envelope_result = result_envelope

    def setUp(self):

        # Set up the mock values
        self.repo_name = "TestRepo"
        self.repo_owner = "TestOwner"
        self.repo_api_url = "https://api.github.com/repos/{}/{}".format(
            self.repo_owner, self.repo_name
        )
        self.branch = "master"

        # Create the project config
        self.project_config = create_project_config(self.repo_name, self.repo_owner)

        if not self.envelope_start:
            self.envelope_start = self.api_class.soap_envelope_start

    def _create_task(self, task_config=None, org_config=None):
        if not task_config:
            task_config = {}
        if not org_config:
            org_config = {}
        task = BaseTask(
            project_config=self.project_config,
            task_config=TaskConfig(task_config),
            org_config=DummyOrgConfig(org_config),
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
            content_type="text/xml; charset=utf-8",
        )
        return response

    def _create_instance(self, task, api_version=None):
        return self.api_class(task, api_version=api_version)

    def test_init(self):
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEqual(api.task, task)
        self.assertEqual(
            api.api_version, self.project_config.project__package__api_version
        )

    def test_build_endpoint_url(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        self.assertEqual(
            api._build_endpoint_url(),
            "{}/services/Soap/m/{}/{}".format(
                org_config["instance_url"],
                self.project_config.project__package__api_version,
                task.org_config.org_id,
            ),
        )

    def test_build_endpoint_url_mydomain(self):
        org_config = {
            "instance_url": "https://test-org.na12.my.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        self.assertEqual(
            api._build_endpoint_url(),
            "https://na12.salesforce.com/services/Soap/m/{}/{}".format(
                self.project_config.project__package__api_version,
                task.org_config.org_id,
            ),
        )

    def test_build_endpoint_url_apiversion(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
        }
        task = self._create_task(org_config=org_config)
        api_version = "43.0"
        api = self._create_instance(task, api_version=api_version)
        self.assertEqual(
            api._build_endpoint_url(),
            "{}/services/Soap/m/{}/{}".format(
                org_config["instance_url"], api_version, task.org_config.org_id
            ),
        )

    def test_build_envelope_result(self):
        task = self._create_task()
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_result:
            api.soap_envelope_result = "{process_id}"
            expected = "123"
        else:
            expected = self.envelope_result.format(process_id="123")
        api.process_id = "123"
        self.assertEqual(api._build_envelope_result(), expected)

    def test_build_envelope_start(self):
        task = self._create_task()
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
            expected = str(self.project_config.project__package__api_version)
        else:
            expected = self._expected_envelope_start()

        self.assertEqual(api._build_envelope_start(), expected)

    def _expected_envelope_start(self):
        return self.envelope_start.format(
            api_version=self.project_config.project__package__api_version
        )

    def test_build_envelope_status(self):
        task = self._create_task()
        api = self._create_instance(task)
        process_id = "123"
        if not self.api_class.soap_envelope_status:
            api.soap_envelope_status = "{process_id}"
            expected = process_id
        else:
            expected = self.envelope_status.format(process_id=process_id)
        api.process_id = process_id
        self.assertEqual(api._build_envelope_status(), expected)

    def test_build_headers(self):
        action = "foo"
        message = "12345678"
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEqual(
            api._build_headers(action, message),
            {
                u"Content-Type": u"text/xml; charset=UTF-8",
                u"Content-Length": "8",
                u"SOAPAction": u"foo",
            },
        )

    @responses.activate
    def test_call_faultcode(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
        response = '<?xml version="1.0" encoding="UTF-8"?><faultcode>foo</faultcode>'
        self._mock_call_mdapi(api, response)
        with self.assertRaises(MetadataApiError):
            api()

    @responses.activate
    def test_call_success(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
        if not self.api_class.soap_envelope_status:
            api.soap_envelope_status = "{process_id}"
        if not self.api_class.soap_envelope_result:
            api.soap_envelope_result = "{process_id}"

        response = '<?xml version="1.0" encoding="UTF-8"?><id>1234567890</id>'
        self._mock_call_mdapi(api, response)
        response_status = '<?xml version="1.0" encoding="UTF-8"?><done>true</done>'
        self._mock_call_mdapi(api, response_status)
        response_result = '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>'
        response_result = self._response_call_success_result(response_result)
        self._mock_call_mdapi(api, response_result)

        resp = api()
        expected_resp = self._expected_call_success_result(response_result)

        self.assertEqual(resp, expected_resp)

    def _expected_call_success_result(self, response_result):
        return response_result

    def _response_call_success_result(self, response_result):
        return response_result

    def test_get_element_value(self):
        task = self._create_task()
        api = self._create_instance(task)
        dom = parseString("<foo>bar</foo>")
        self.assertEqual(api._get_element_value(dom, "foo"), "bar")

    def test_get_element_value_not_found(self):
        task = self._create_task()
        api = self._create_instance(task)
        dom = parseString("<foo>bar</foo>")
        self.assertEqual(api._get_element_value(dom, "baz"), None)

    def test_get_element_value_empty(self):
        task = self._create_task()
        api = self._create_instance(task)
        dom = parseString("<foo />")
        self.assertEqual(api._get_element_value(dom, "foo"), None)

    def test_get_check_interval(self):
        task = self._create_task()
        api = self._create_instance(task)
        api.check_num = 1
        self.assertEqual(api._get_check_interval(), 1)
        api.check_num = 10
        self.assertEqual(api._get_check_interval(), 4)

    @responses.activate
    def test_get_response_faultcode(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
        response = '<?xml version="1.0" encoding="UTF-8"?><faultcode>foo</faultcode>'
        self._mock_call_mdapi(api, response)
        with self.assertRaises(MetadataApiError):
            api._get_response()

    @responses.activate
    def test_get_response_faultcode_and_string(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
        response = '<?xml version="1.0" encoding="UTF-8"?>'
        response += "\n<test>"
        response += "\n  <faultcode>foo</faultcode>"
        response += "\n  <faultstring>bar</faultstring>"
        response += "\n</test>"
        self._mock_call_mdapi(api, response)
        with self.assertRaises(MetadataApiError):
            api._get_response()

    @responses.activate
    def test_get_response_faultcode_invalid_session_no_refresh(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
        response = '<?xml version="1.0" encoding="UTF-8"?><faultcode>sf:INVALID_SESSION_ID</faultcode>'
        self._mock_call_mdapi(api, response)
        with self.assertRaises(MetadataApiError):
            api._get_response()
        self.assertEqual(api.status, "Failed")

    @responses.activate
    def test_get_response_faultcode_invalid_session_refresh(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
            "refresh_token": "abcdefghij",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
        if not self.api_class.soap_envelope_status:
            api.soap_envelope_status = "{process_id}"

        mock_responses = []
        mock_responses.append(b'<?xml version="1.0" encoding="UTF-8"?><id>123</id>')
        mock_responses.append(
            b'<?xml version="1.0" encoding="UTF-8"?><faultcode>sf:INVALID_SESSION_ID</faultcode>'
        )
        mock_responses.append(b'<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>')
        for response in mock_responses:
            self._mock_call_mdapi(api, response)

        resp = api._get_response()
        self.assertEqual(resp.content, mock_responses[2])

    @responses.activate
    def test_get_response_start_error_500(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        status_code = http.client.INTERNAL_SERVER_ERROR  # HTTP Error 500
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
        if not self.api_class.soap_envelope_status:
            api.soap_envelope_status = "{process_id}"

        response = '<?xml version="1.0" encoding="UTF-8"?><foo>start</foo>'
        self._mock_call_mdapi(api, response, status_code)

        with self.assertRaises(MetadataApiError):
            api._get_response()

    @responses.activate
    def test_get_response_status_error_500(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        status_code = http.client.INTERNAL_SERVER_ERROR  # HTTP Error 500
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
        if not self.api_class.soap_envelope_status:
            api.soap_envelope_status = "{process_id}"

        response = '<?xml version="1.0" encoding="UTF-8"?><id>1234567890</id>'
        self._mock_call_mdapi(api, response)
        self._mock_call_mdapi(api, response, status_code)

        with self.assertRaises(MetadataApiError):
            api._get_response()

    @responses.activate
    def test_get_response_status_no_loop(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
        if not self.api_class.soap_envelope_status:
            api.soap_envelope_status = "{process_id}"
        if not self.api_class.soap_envelope_result:
            api.soap_envelope_result = "{process_id}"

        response = b'<?xml version="1.0" encoding="UTF-8"?><id>1234567890</id>'
        self._mock_call_mdapi(api, response)
        response_status = b'<?xml version="1.0" encoding="UTF-8"?><done>true</done>'
        self._mock_call_mdapi(api, response_status)
        response_result = b'<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>'
        self._mock_call_mdapi(api, response_result)

        resp = api._get_response()

        self.assertEqual(resp.content, response_result)

    @responses.activate
    def test_get_response_status_loop_twice(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
        if not self.api_class.soap_envelope_status:
            api.soap_envelope_status = "{process_id}"
        if not self.api_class.soap_envelope_result:
            api.soap_envelope_result = "{process_id}"
        api.check_interval = 0

        response = b'<?xml version="1.0" encoding="UTF-8"?><id>1234567890</id>'
        self._mock_call_mdapi(api, response)
        response_status = b'<?xml version="1.0" encoding="UTF-8"?><done>false</done>'
        self._mock_call_mdapi(api, response_status)
        response_status = b'<?xml version="1.0" encoding="UTF-8"?><done>false</done>'
        self._mock_call_mdapi(api, response_status)
        response_status = b'<?xml version="1.0" encoding="UTF-8"?><done>true</done>'
        self._mock_call_mdapi(api, response_status)
        response_result = b'<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>'
        self._mock_call_mdapi(api, response_result)

        resp = api._get_response()

        self.assertEqual(resp.content, response_result)

        self.assertEqual(api.status, "Done")

        self.assertEqual(api.check_num, 4)

    def test_process_response_status_no_done_element(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            b'<?xml version="1.0" encoding="UTF-8"?><foo>status</foo>'
        )
        res = api._process_response_status(response)
        self.assertEqual(api.status, "Failed")
        self.assertEqual(res.content, response.content)

    def test_process_response_status_done_is_true(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            b'<?xml version="1.0" encoding="UTF-8"?><done>true</done>'
        )
        res = api._process_response_status(response)
        self.assertEqual(api.status, "Done")
        self.assertEqual(res.content, response.content)

    def test_process_response_status_pending(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            b'<?xml version="1.0" encoding="UTF-8"?><done>false</done>'
        )
        res = api._process_response_status(response)
        self.assertEqual(api.status, "Pending")
        self.assertEqual(res.content, response.content)

    def test_process_response_status_in_progress(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            b'<?xml version="1.0" encoding="UTF-8"?><done>false</done>'
        )
        api.status = "InProgress"
        res = api._process_response_status(response)
        self.assertEqual(api.status, "InProgress")
        self.assertEqual(res.content, response.content)

    def test_process_response_status_in_progress_state_detail(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            b'<?xml version="1.0" encoding="UTF-8"?><test><done>false</done><stateDetail>Deploy log goes here</stateDetail></test>'
        )
        api.status = "InProgress"
        res = api._process_response_status(response)
        self.assertEqual(api.status, "InProgress")
        self.assertEqual(res.content, response.content)


class TestBaseMetadataApiCall(BaseTestMetadataApi):
    def test_build_envelope_start_no_envelope(self):
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEqual(api._build_envelope_start(), None)

    def test_build_envelope_status_no_envelope(self):
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEqual(api._build_envelope_status(), None)

    def test_build_envelope_result_no_envelope(self):
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEqual(api._build_envelope_result(), None)

    def test_get_response_no_start_env(self):
        task = self._create_task()
        api = self._create_instance(task)
        with self.assertRaises(NotImplementedError):
            api._get_response()

    @responses.activate
    def test_get_response_no_status(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        api.soap_envelope_start = "{api_version}"
        response = b'<?xml version="1.0" encoding="UTF-8"?><foo />'
        self._mock_call_mdapi(api, response)
        resp = api._get_response()
        self.assertEqual(resp.content, response)


class TestApiDeploy(BaseTestMetadataApi):
    api_class = ApiDeploy
    envelope_status = deploy_status_envelope

    def setUp(self):
        super(TestApiDeploy, self).setUp()
        self.package_zip = DummyPackageZipBuilder()()

    def _expected_envelope_start(self):
        return self.envelope_start.format(
            package_zip=self.package_zip,
            check_only="false",
            purge_on_delete="false",
            test_level="",
            run_tests="",
        )

    def _response_call_success_result(self, response_result):
        return deploy_result.format(status="Succeeded", extra="").encode()

    def _expected_call_success_result(self, response_result):
        return "Success"

    def _create_instance(
        self,
        task,
        api_version=None,
        purge_on_delete=None,
        check_only=None,
        test_level=None,
        run_tests=None,
    ):
        return self.api_class(
            task,
            self.package_zip,
            api_version=api_version,
            purge_on_delete=purge_on_delete,
            check_only=check_only,
            test_level=test_level,
            run_tests=run_tests,
        )

    def test_init_no_purge_on_delete(self):
        task = self._create_task()
        api = self._create_instance(task, purge_on_delete=False)
        self.assertEqual(api.purge_on_delete, "false")

    def test_init_default_check_only(self):
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEqual(api.check_only, "false")

    def test_init_check_only(self):
        task = self._create_task()
        api = self._create_instance(task, check_only=True)
        self.assertEqual(api.check_only, "true")

    def test_init_default_test_level(self):
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEqual(api.test_level, None)

    def test_init_test_level(self):
        task = self._create_task()
        api = self._create_instance(task, test_level="NoTestRun")
        self.assertEqual(api.test_level, "NoTestRun")

    def test_init_default_run_tests(self):
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEqual(api.run_tests, [])

    def test_init_run_tests(self):
        task = self._create_task()
        api = self._create_instance(task, run_tests=["TestA", "TestB"])
        self.assertEqual(api.run_tests, ["TestA", "TestB"])

    def test_build_envelope_status__run_specified_tests(self):
        task = self._create_task()
        api = self._create_instance(
            task, run_tests=["TestA", "TestB"], test_level="RunSpecifiedTests"
        )

        api.package_zip = "Test"

        envelope = api._build_envelope_start()
        assert "<runTests>TestA</runTests>" in envelope
        assert "<runTests>TestB</runTests>" in envelope
        assert "RunSpecifiedTests" in envelope

    def test_process_response_metadata_failure(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            deploy_result_failure.format(
                details="""<componentFailures>
  <problem>problem</problem>
  <problemType>Error</problemType>
  <componentType>CustomObject</componentType>
  <fileName>Test__c</fileName>
  <lineNumber>1</lineNumber>
  <columnNumber>1</columnNumber>
  <created>false</created>
  <deleted>false</deleted>
</componentFailures>"""
            ).encode()
        )
        with self.assertRaises(MetadataComponentFailure) as cm:
            api._process_response(response)
        expected = "Update of CustomObject Test__c: Error on line 1, col 1: problem"
        self.assertEqual(expected, str(cm.exception))

    def test_process_response_metadata_failure_no_lineno(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            deploy_result_failure.format(
                details="""<componentFailures>
  <problem>problem</problem>
  <problemType>Error</problemType>
  <componentType>CustomObject</componentType>
  <fileName>Test__c</fileName>
  <created>false</created>
  <deleted>false</deleted>
</componentFailures>"""
            ).encode()
        )
        with self.assertRaises(MetadataComponentFailure) as cm:
            api._process_response(response)
        expected = "Update of CustomObject Test__c: Error: problem"
        self.assertEqual(expected, str(cm.exception))

    def test_process_response_metadata_failure_no_file_name(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            deploy_result_failure.format(
                details="""<componentFailures>
  <problem>problem</problem>
  <problemType>Error</problemType>
  <componentType>CustomObject</componentType>
  <created>false</created>
  <deleted>false</deleted>
</componentFailures>"""
            ).encode()
        )
        with self.assertRaises(MetadataComponentFailure) as cm:
            api._process_response(response)
        expected = "Update of CustomObject: Error: problem"
        self.assertEqual(expected, str(cm.exception))

    def test_process_response_problem(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            deploy_result_failure.format(
                details="""<problem>problem</problem>"""
            ).encode()
        )
        with self.assertRaises(MetadataApiError) as cm:
            api._process_response(response)
        expected = "problem"
        self.assertEqual(expected, str(cm.exception))

    def test_process_response_test_failure(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            deploy_result_failure.format(
                details="""<runTestResult>
  <failures>
    <namespace>test</namespace>
    <stackTrace>stack</stackTrace>
  </failures>
</runTestResult>
"""
            ).encode()
        )
        with self.assertRaises(ApexTestException) as cm:
            api._process_response(response)
        expected = "Apex Test Failure: from namespace test: stack"
        self.assertEqual(expected, str(cm.exception))

    def test_process_response_no_status(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(b"<bogus />")
        status = api._process_response(response)
        self.assertEqual(status, "Failed")

    def test_process_response_failure_but_no_message(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(b"<status>Failed</status>")
        with self.assertRaises(MetadataApiError) as cm:
            api._process_response(response)
        self.assertEqual(response.text, str(cm.exception))

    def test_get_action(self):
        task = self._create_task()
        api = self._create_instance(task)
        self.assertEqual("Create", api._get_action(True, False))
        self.assertEqual("Delete", api._get_action(False, True))
        self.assertEqual("Update", api._get_action(False, False))


class TestApiListMetadata(BaseTestMetadataApi):
    api_class = ApiListMetadata
    envelope_start = list_metadata_start_envelope

    def setUp(self):
        super(TestApiListMetadata, self).setUp()
        self.metadata_type = "CustomObject"
        self.metadata = None
        self.folder = None
        self.api_version = self.project_config.project__package__api_version

    def _response_call_success_result(self, response_result):
        return list_metadata_result

    def _expected_call_success_result(self, response_result):
        metadata = defaultdict(list)
        metadata["CustomObject"] = [
            {
                u"createdById": None,
                u"createdByName": None,
                u"createdDate": datetime.datetime(2018, 8, 7, 16, 31, 57),
                u"fileName": None,
                u"fullName": u"Test__c",
                u"id": None,
                u"lastModifiedById": None,
                u"lastModifiedByName": None,
                u"lastModifiedDate": None,
                u"manageableState": None,
                u"namespacePrefix": None,
                u"type": "CustomObject",
            }
        ]
        return metadata

    def _create_instance(self, task, api_version=None):
        if api_version is None:
            api_version = self.api_version
        return self.api_class(
            task,
            metadata_type=self.metadata_type,
            metadata=self.metadata,
            folder=self.folder,
            as_of_version=api_version,
        )

    @responses.activate
    def test_bad_date_somehow(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)

        self._mock_call_mdapi(api, list_metadata_result_bad_val)
        with self.assertRaises(MetadataParseError):
            api()


class TestApiRetrieveUnpackaged(BaseTestMetadataApi):
    maxDiff = None
    api_class = ApiRetrieveUnpackaged
    envelope_start = retrieve_unpackaged_start_envelope

    def setUp(self):
        super(TestApiRetrieveUnpackaged, self).setUp()
        self.package_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <version>41.0</version>
</Package>"""
        self.result_zip = DummyPackageZipBuilder()

    def _response_call_success_result(self, response_result):
        return retrieve_result.format(zip=self.result_zip(), extra="").encode()

    def _expected_call_success_result(self, response_result):
        return self.result_zip.zip

    def _create_instance(self, task, api_version=None):
        return self.api_class(task, self.package_xml, api_version=api_version)

    @responses.activate
    def test_call_success(self):
        org_config = {
            "instance_url": "https://na12.salesforce.com",
            "id": "https://login.salesforce.com/id/00D000000000000ABC/005000000000000ABC",
            "access_token": "0123456789",
        }
        task = self._create_task(org_config=org_config)
        api = self._create_instance(task)
        if not self.api_class.soap_envelope_start:
            api.soap_envelope_start = "{api_version}"
        if not self.api_class.soap_envelope_status:
            api.soap_envelope_status = "{process_id}"
        if not self.api_class.soap_envelope_result:
            api.soap_envelope_result = "{process_id}"

        response = '<?xml version="1.0" encoding="UTF-8"?><id>1234567890</id>'
        self._mock_call_mdapi(api, response)
        response_status = '<?xml version="1.0" encoding="UTF-8"?><done>true</done>'
        self._mock_call_mdapi(api, response_status)
        response_result = '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>'
        response_result = self._response_call_success_result(response_result)
        self._mock_call_mdapi(api, response_result)

        zip_file = api()

        self.assertEqual(
            zip_file.namelist(),
            self._expected_call_success_result(response_result).namelist(),
        )


class TestApiRetrieveInstalledPackages(BaseTestMetadataApi):
    api_class = ApiRetrieveInstalledPackages

    def _create_instance(self, task, api_version=None):
        api = self.api_class(task, api_version)
        return api

    def _expected_call_success_result(self, result_response):
        return {}

    def test_process_response_no_zipstr(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            deploy_result.format(status="testing", extra="").encode()
        )
        resp = api._process_response(response)
        self.assertEqual(resp, {})

    def test_process_response_zipstr_no_packages(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            retrieve_result.format(
                zip=CreatePackageZipBuilder("testing", api.api_version)(), extra=""
            ).encode()
        )
        resp = api._process_response(response)
        self.assertEqual(resp, {})

    def test_process_response_zipstr_one_package(self):
        task = self._create_task()
        api = self._create_instance(task)
        response = Response()
        response.status_code = 200
        response.raw = io.BytesIO(
            retrieve_result.format(
                zip=InstallPackageZipBuilder("foo", "1.1")(), extra=""
            ).encode()
        )
        resp = api._process_response(response)
        self.assertEqual(resp, {"foo": "1.1"})


class TestApiRetrievePackaged(TestApiRetrieveUnpackaged):
    api_class = ApiRetrievePackaged
    envelope_start = retrieve_packaged_start_envelope

    def setUp(self):
        super(TestApiRetrievePackaged, self).setUp()
        self.package_name = "Test Package"

    def _expected_envelope_start(self):
        return self.envelope_start.format(
            api_version=self.project_config.project__package__api_version,
            package_name=self.package_name,
        )

    def _create_instance(self, task, api_version=None):
        return self.api_class(task, self.package_name, api_version)
