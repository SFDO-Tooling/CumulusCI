import pytest  # noqa: F401
from unittest import mock
import responses
import urllib.parse
import json
from cumulusci.tasks.salesforce.tests.util import create_task

from pathlib import Path
import os
from cumulusci.tasks.salesforce.content_documents import (
    InsertContentDocument,
    to_cumulusci_exception,
)
from cumulusci.core.exceptions import TaskOptionsError, CumulusCIException
from simple_salesforce.exceptions import SalesforceMalformedRequest


def assert_call_urls(expected_call_urls, responses_calls):
    actual_call_urls = [call.request.url for call in responses_calls]
    assert_message = """URLs of calls.
Expected: {expected_call_urls_length} calls:
    {expected_call_urls}

Actual: {actual_call_urls_length} calls
    {actual_call_urls}
""".format(
        expected_call_urls_length=(len(expected_call_urls)),
        expected_call_urls=("\n    ".join(expected_call_urls)),
        actual_call_urls_length=(len(actual_call_urls)),
        actual_call_urls=("\n    ".join(actual_call_urls)),
    )
    assert expected_call_urls == actual_call_urls, assert_message


class TestToCumulusCIException:
    def test_to_cumulusci_exception(self):
        e = to_cumulusci_exception(
            SalesforceMalformedRequest(
                "url",
                "status",
                "resource_name",
                [
                    {"message": "Error message 0.", "errorCode": "ERROR_0"},
                    {"errorCode": "ERROR_1"},
                    {"message": "Error message 2.", "errorCode": "ERROR_2"},
                ],
            )
        )

        assert type(e) is CumulusCIException
        assert "Error message 0.; Unknown.; Error message 2." == e.args[0]


class TestInsertContentDocument:
    def setup_method(self):
        self.base_path = os.path.dirname(__file__)

        # Path to an existing directory (that is not a file).
        self.directory_path = Path(os.path.join(self.base_path, "mocks")).resolve()

        assert (
            self.directory_path.exists()
        ), 'A directory should exist with path "{self.directory_path}"'

        assert (
            not self.directory_path.is_file()
        ), f'directory_path "{self.directory_path}" should not be a file.'

        # Path to an existing file.
        self.file_path = Path(
            os.path.join(self.base_path, "mocks/InsertContentDocument.file.txt")
        ).resolve()

        assert (
            self.file_path.exists()
        ), 'A file should exist with path "{self.file_path}"'

        assert (
            self.file_path.is_file()
        ), f'file_path "{self.file_path}" should be a file.'

        # Resusable data
        self.content_version_id = "0681k000001YWQ5AAO"
        self.content_document_id = "0691k000001LtfEAAS"
        self.queries = [
            # Records 0 and 1
            "SELECT Id FROM Account LIMIT 2",
            # No records
            "SELECT Id FROM Account WHERE Id = null",
            # Records 1 and 2
            "SELECT Id FROM Account LIMIT 2 OFFSET 1",
        ]
        self.account_ids = [
            "001000000000000AAA",
            "001000000000001AAA",
            "001000000000002AAA",
        ]
        self.content_document_link_id = "06A000000000000EAA"

    def test_init_options__path_does_not_exist(self):
        fake_path = "not a real/path/to/a/file"
        with pytest.raises(TaskOptionsError) as e:
            create_task(
                InsertContentDocument,
                {"path": fake_path},
            )

        assert e.value.args[0] == f'Invalid "path". No file found at {fake_path}'

    def test_init_options__path_points_to_directory(self):
        with pytest.raises(TaskOptionsError) as e:
            create_task(
                InsertContentDocument,
                {"path": self.directory_path},
            )

        assert (
            e.value.args[0] == f'Invalid "path". No file found at {self.directory_path}'
        )

    def test_init_options__path_points_to_file__default_options(self):
        task = create_task(
            InsertContentDocument,
            {"path": self.file_path},
        )

        assert task.options["path"] == Path(
            self.file_path
        ), '"path" option should be a Path instance pointint to self.file_path.'

        assert (
            task.options["queries"] == []
        ), 'The default "queries" option should be an empty list.'

        assert (
            task.options["share_type"] == "I"
        ), 'The default "share_type" option should equal "I".'

        assert (
            task.options["visibility"] == "AllUsers"
        ), 'The default "visibility" option should equal "AllUsers".'

    def test_init_options__path_points_to_file__override_options(self):
        queries = ",".join(self.queries)
        share_type = "V"
        visibility = "SharedUsers"

        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": queries,
                "share_type": share_type,
                "visibility": visibility,
            },
        )

        assert task.options["path"] == Path(
            self.file_path
        ), '"path" option should be a Path instance pointint to self.file_path.'

        assert (
            task.options["queries"] == self.queries
        ), '"queries" option should be overridden.'

        assert (
            task.options["share_type"] == share_type
        ), '"share_type" option should be overridden.'

        assert (
            task.options["visibility"] == visibility
        ), '"visibility" option should be overridden.'

    @responses.activate
    def test_insert_content_document__success(self):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": self.queries,
            },
        )
        task.logger = mock.Mock()

        api_version = f"v{task.project_config.project__package__api_version}"
        data_url = f"{task.org_config.instance_url}/services/data/{api_version}"

        # Insert ContentVersion call.
        insert_content_version_url = f"{data_url}/sobjects/ContentVersion/"
        responses.add(
            responses.POST,
            insert_content_version_url,
            content_type="application/json",
            status=201,
            json={"id": self.content_version_id, "success": True, "errors": []},
        )

        # Query ContentVersion.ContentDocumentId call.
        content_version_query = f"SELECT Id, ContentDocumentId FROM ContentVersion WHERE Id = '{self.content_version_id}'"
        query_content_version_url = (
            f"{data_url}/query/?q={urllib.parse.quote_plus(content_version_query)}"
        )
        responses.add(
            responses.GET,
            query_content_version_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "ContentVersion",
                            "url": f"/services/data/{api_version}/sobjects/ContentVersion/{self.content_version_id}",
                        },
                        "Id": self.content_version_id,
                        "ContentDocumentId": self.content_document_id,
                    }
                ],
            },
        )

        # Initialize REST API
        task._init_task()

        # Execute _insert_content_document.
        assert (
            self.content_document_id == task._insert_content_document()
        ), "_insert_content_document should execute successfully and return the inserted ContentVersion.ContentDocumentId."

        assert_call_urls(
            [
                insert_content_version_url,
                query_content_version_url,
            ],
            responses.calls,
        )

        task.logger.info.assert_has_calls(
            [
                mock.call(f'Inserting ContentVersion from {task.options["path"]}'),
                mock.call(
                    f'Success!  Inserted ContentDocument "{self.content_document_id}".'
                ),
            ]
        )

    @responses.activate
    def test_insert_content_document__insert_failed(self):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": self.queries,
            },
        )
        task.logger = mock.Mock()

        api_version = f"v{task.project_config.project__package__api_version}"
        data_url = f"{task.org_config.instance_url}/services/data/{api_version}"

        # Insert ContentVersion call fails.
        insert_content_version_url = f"{data_url}/sobjects/ContentVersion/"
        responses.add(
            responses.POST,
            insert_content_version_url,
            content_type="application/json",
            status=400,
            json=[
                {
                    "message": "Invalid Title",
                    "errorCode": "FIELD_CUSTOM_VALIDATION_EXCEPTION",
                    "fields": ["Title"],
                }
            ],
        )

        # Initialize REST API
        task._init_task()

        # Execute _insert_content_document.
        with pytest.raises(SalesforceMalformedRequest):
            task._insert_content_document()

        assert_call_urls(
            [
                insert_content_version_url,
            ],
            responses.calls,
        )

        task.logger.info.assert_has_calls(
            [
                mock.call(f'Inserting ContentVersion from {task.options["path"]}'),
            ]
        )

    @responses.activate
    def test_get_record_ids_to_link__with_queries(self):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": self.queries,
            },
        )
        task.logger = mock.Mock()

        api_version = f"v{task.project_config.project__package__api_version}"
        data_url = f"{task.org_config.instance_url}/services/data/{api_version}"

        # Record query 0: Returns account_ids 0 and 1.
        query_0_url = f"{data_url}/query/?q={urllib.parse.quote_plus(self.queries[0])}"
        responses.add(
            responses.GET,
            query_0_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 2,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[0]}",
                        },
                        "Id": self.account_ids[0],
                    },
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[1]}",
                        },
                        "Id": self.account_ids[1],
                    },
                ],
            },
        )

        # Record query 1: Returns no records.
        query_1_url = f"{data_url}/query/?q={urllib.parse.quote_plus(self.queries[1])}"
        responses.add(
            responses.GET,
            query_1_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 0,
                "done": True,
                "records": [],
            },
        )

        # Record query 2: Returns account_ids 1 and 2.
        query_2_url = f"{data_url}/query/?q={urllib.parse.quote_plus(self.queries[2])}"
        responses.add(
            responses.GET,
            query_2_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 2,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[1]}",
                        },
                        "Id": self.account_ids[1],
                    },
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[2]}",
                        },
                        "Id": self.account_ids[2],
                    },
                ],
            },
        )

        # Initialize REST API
        task._init_task()

        # Execute _get_record_ids_to_link.
        assert set(self.account_ids) == set(
            task._get_record_ids_to_link()
        ), "_get_record_ids_to_link should return all self.record_ids."

        assert_call_urls(
            [
                query_0_url,
                query_1_url,
                query_2_url,
            ],
            responses.calls,
        )

        task.logger.info.assert_has_calls(
            [
                mock.call(""),
                mock.call("Querying records to link to the new ContentDocument."),
                mock.call(f"    {self.queries[0]}"),
                mock.call(f"        (2) {self.account_ids[0]}, {self.account_ids[1]}"),
                mock.call(f"    {self.queries[1]}"),
                mock.call("        🚫 No records found."),
                mock.call(f"    {self.queries[2]}"),
                mock.call(f"        (2) {self.account_ids[1]}, {self.account_ids[2]}"),
            ]
        )

    @responses.activate
    def test_get_record_ids_to_link__no_queries(self):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
            },
        )
        task.logger = mock.Mock()

        # Execute _get_record_ids_to_link
        record_ids_to_link = task._get_record_ids_to_link()
        assert 0 == len(
            record_ids_to_link
        ), f"No record IDs to link should have been queried since there are no queries.  Actual: {', '.join(record_ids_to_link)}"

        assert_call_urls(
            [],
            responses.calls,
        )

        task.logger.info.assert_has_calls(
            [
                mock.call(""),
                mock.call("Querying records to link to the new ContentDocument."),
                mock.call("    No queries specified."),
            ]
        )

    @responses.activate
    def test_link_records_to_content_document__many_records(self):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": self.queries,
            },
        )
        task.logger = mock.Mock()

        api_version = f"v{task.project_config.project__package__api_version}"
        data_url = f"{task.org_config.instance_url}/services/data/{api_version}"

        # Insert ContentVersion call.
        insert_content_document_link_url = f"{data_url}/sobjects/ContentDocumentLink/"
        responses.add(
            responses.POST,
            insert_content_document_link_url,
            content_type="application/json",
            status=201,
            json={"id": self.content_document_link_id, "success": True, "errors": []},
        )

        # Initialize REST API
        task._init_task()

        # Execute _link_records_to_content_document.
        task._link_records_to_content_document(
            self.content_document_id, self.account_ids
        )

        assert_call_urls(
            [insert_content_document_link_url for _ in self.account_ids],
            responses.calls,
        )

        share_type = task.options["share_type"]
        visibility = task.options["visibility"]

        for i, call in enumerate(responses.calls):
            body = json.loads(call.request.body)

            assert self.content_document_id == body.get(
                "ContentDocumentId"
            ), f'Invalid ContentDocumentId for call[{i}].request.body.  Expecting: {self.content_document_id}; Actual: {body.get("ContentDocumentId")}'

            assert self.account_ids[i] == body.get(
                "LinkedEntityId"
            ), f'Invalid LinkedEntityId for call[{i}].request.body.  Expecting: {self.account_ids[i]}; Actual: {body.get("LinkedEntityId")}'

            assert share_type == body.get(
                "ShareType"
            ), f'Invalid ShareType for call[{i}].request.body.  Expecting: {share_type}; Actual: {body.get("ShareType")}'

            assert visibility == body.get(
                "Visibility"
            ), f'Invalid Visibility for call[{i}].request.body.  Expecting: {visibility}; Actual: {body.get("Visibility")}'

        task.logger.info.assert_has_calls(
            [
                mock.call(""),
                mock.call(
                    "Inserting ContentDocumentLink records to link the ContentDocument."
                ),
                mock.call(f'    ShareType: "{share_type}"'),
                mock.call(f'    Visibility: "{visibility}"'),
                mock.call(
                    f'Successfully linked {len(self.account_ids)} records to Content Document "{self.content_document_id}"'
                ),
            ]
        )

    @responses.activate
    def test_link_records_to_content_document__one_record(self):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": self.queries,
            },
        )
        task.logger = mock.Mock()

        api_version = f"v{task.project_config.project__package__api_version}"
        data_url = f"{task.org_config.instance_url}/services/data/{api_version}"

        # Insert ContentVersion call.
        insert_content_document_link_url = f"{data_url}/sobjects/ContentDocumentLink/"
        responses.add(
            responses.POST,
            insert_content_document_link_url,
            content_type="application/json",
            status=201,
            json={"id": self.content_document_link_id, "success": True, "errors": []},
        )

        # Initialize REST API
        task._init_task()

        # Execute _link_records_to_content_document.
        task._link_records_to_content_document(
            self.content_document_id, [self.account_ids[0]]
        )

        assert_call_urls(
            [insert_content_document_link_url],
            responses.calls,
        )

        share_type = task.options["share_type"]
        visibility = task.options["visibility"]

        body = json.loads(responses.calls[0].request.body)

        assert self.content_document_id == body.get(
            "ContentDocumentId"
        ), f'Invalid ContentDocumentId for call[0].request.body.  Expecting: {self.content_document_id}; Actual: {body.get("ContentDocumentId")}'

        assert self.account_ids[0] == body.get(
            "LinkedEntityId"
        ), f'Invalid LinkedEntityId for call[0].request.body.  Expecting: {self.account_ids[0]}; Actual: {body.get("LinkedEntityId")}'

        assert share_type == body.get(
            "ShareType"
        ), f'Invalid ShareType for call[0].request.body.  Expecting: {share_type}; Actual: {body.get("ShareType")}'

        assert visibility == body.get(
            "Visibility"
        ), f'Invalid Visibility for call[0].request.body.  Expecting: {visibility}; Actual: {body.get("Visibility")}'

        task.logger.info.assert_has_calls(
            [
                mock.call(""),
                mock.call(
                    "Inserting ContentDocumentLink records to link the ContentDocument."
                ),
                mock.call(f'    ShareType: "{share_type}"'),
                mock.call(f'    Visibility: "{visibility}"'),
                mock.call(
                    f'Successfully linked 1 record to Content Document "{self.content_document_id}"'
                ),
            ]
        )

    @responses.activate
    def test_link_records_to_content_document__no_records(self):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": self.queries,
            },
        )
        task.logger = mock.Mock()

        # Initialize REST API
        task._init_task()

        # Execute _link_records_to_content_document.
        task._link_records_to_content_document(self.content_document_id, [])

        assert_call_urls(
            [],
            responses.calls,
        )

        task.logger.info.assert_has_calls(
            [
                mock.call(""),
                mock.call(
                    "😴 No records IDs queried. Skipping linking the Content Document to related records."
                ),
            ]
        )

    @responses.activate
    def test_task__success__linking_many_records(self):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": self.queries,
            },
        )
        task.logger = mock.Mock()

        api_version = f"v{task.project_config.project__package__api_version}"
        data_url = f"{task.org_config.instance_url}/services/data/{api_version}"

        # Insert ContentVersion call.
        insert_content_version_url = f"{data_url}/sobjects/ContentVersion/"
        responses.add(
            responses.POST,
            insert_content_version_url,
            content_type="application/json",
            status=201,
            json={"id": self.content_version_id, "success": True, "errors": []},
        )

        # Query ContentVersion.ContentDocumentId call.
        content_version_query = f"SELECT Id, ContentDocumentId FROM ContentVersion WHERE Id = '{self.content_version_id}'"
        query_content_version_url = (
            f"{data_url}/query/?q={urllib.parse.quote_plus(content_version_query)}"
        )
        responses.add(
            responses.GET,
            query_content_version_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "ContentVersion",
                            "url": f"/services/data/{api_version}/sobjects/ContentVersion/{self.content_version_id}",
                        },
                        "Id": self.content_version_id,
                        "ContentDocumentId": self.content_document_id,
                    }
                ],
            },
        )

        # Record query 0: Returns account_ids 0 and 1.
        query_0_url = f"{data_url}/query/?q={urllib.parse.quote_plus(self.queries[0])}"
        responses.add(
            responses.GET,
            query_0_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 2,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[0]}",
                        },
                        "Id": self.account_ids[0],
                    },
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[1]}",
                        },
                        "Id": self.account_ids[1],
                    },
                ],
            },
        )

        # Record query 1: Returns no records.
        query_1_url = f"{data_url}/query/?q={urllib.parse.quote_plus(self.queries[1])}"
        responses.add(
            responses.GET,
            query_1_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 0,
                "done": True,
                "records": [],
            },
        )

        # Record query 2: Returns account_ids 1 and 2.
        query_2_url = f"{data_url}/query/?q={urllib.parse.quote_plus(self.queries[2])}"
        responses.add(
            responses.GET,
            query_2_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 2,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[1]}",
                        },
                        "Id": self.account_ids[1],
                    },
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[2]}",
                        },
                        "Id": self.account_ids[2],
                    },
                ],
            },
        )

        # Insert ContentVersion call.
        insert_content_document_link_url = f"{data_url}/sobjects/ContentDocumentLink/"
        responses.add(
            responses.POST,
            insert_content_document_link_url,
            content_type="application/json",
            status=201,
            json={"id": self.content_document_link_id, "success": True, "errors": []},
        )

        # Run task.
        task()

        # Assert calls.
        assert_call_urls(
            [
                insert_content_version_url,
                query_content_version_url,
                query_0_url,
                query_1_url,
                query_2_url,
                insert_content_document_link_url,  # account_ids[0]
                insert_content_document_link_url,  # account_ids[1]
                insert_content_document_link_url,  # account_ids[2]
            ],
            responses.calls,
        )

        # Assert log.
        task.logger.info.assert_has_calls(
            [
                mock.call(f'Inserting ContentVersion from {task.options["path"]}'),
                mock.call(
                    f'Success!  Inserted ContentDocument "{self.content_document_id}".'
                ),
                mock.call(""),
                mock.call("Querying records to link to the new ContentDocument."),
                mock.call(f"    {self.queries[0]}"),
                mock.call(f"        (2) {self.account_ids[0]}, {self.account_ids[1]}"),
                mock.call(f"    {self.queries[1]}"),
                mock.call("        🚫 No records found."),
                mock.call(f"    {self.queries[2]}"),
                mock.call(f"        (2) {self.account_ids[1]}, {self.account_ids[2]}"),
                mock.call(""),
                mock.call(
                    "Inserting ContentDocumentLink records to link the ContentDocument."
                ),
                mock.call('    ShareType: "{share_type}"'.format(**task.options)),
                mock.call('    Visibility: "{visibility}"'.format(**task.options)),
                mock.call(
                    f'Successfully linked {len(self.account_ids)} records to Content Document "{self.content_document_id}"'
                ),
            ]
        )

    @responses.activate
    def test_task__fails__get_record_ids_to_link(self):
        queries = ["SELECT Id FROM Accountz LIMIT 2"]  # No Object called "Accountz"
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": queries,
            },
        )
        task.logger = mock.Mock()

        api_version = f"v{task.project_config.project__package__api_version}"
        data_url = f"{task.org_config.instance_url}/services/data/{api_version}"

        # Insert ContentVersion call.
        insert_content_version_url = f"{data_url}/sobjects/ContentVersion/"
        responses.add(
            responses.POST,
            insert_content_version_url,
            content_type="application/json",
            status=201,
            json={"id": self.content_version_id, "success": True, "errors": []},
        )

        # Query ContentVersion.ContentDocumentId call.
        content_version_query = f"SELECT Id, ContentDocumentId FROM ContentVersion WHERE Id = '{self.content_version_id}'"
        query_content_version_url = (
            f"{data_url}/query/?q={urllib.parse.quote_plus(content_version_query)}"
        )
        responses.add(
            responses.GET,
            query_content_version_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "ContentVersion",
                            "url": f"/services/data/{api_version}/sobjects/ContentVersion/{self.content_version_id}",
                        },
                        "Id": self.content_version_id,
                        "ContentDocumentId": self.content_document_id,
                    }
                ],
            },
        )

        # Record query 0: Returns account_ids 0 and 1.
        query_0_url = f"{data_url}/query/?q={urllib.parse.quote_plus(queries[0])}"
        responses.add(
            responses.GET,
            query_0_url,
            content_type="application/json",
            status=400,
            json=[
                {
                    "message": "\nSELECT Id FROM Accountz LIMIT 2\n               ^\nERROR at Row:1:Column:16\nsObject type 'Accountz' is not supported. If you are attempting to use a custom object, be sure to append the '__c' after the entity name. Please reference your WSDL or the describe call for the appropriate names.",
                    "errorCode": "INVALID_TYPE",
                }
            ],
        )

        # Run task.
        with pytest.raises(CumulusCIException):
            task()

        # Assert calls.
        assert_call_urls(
            [
                insert_content_version_url,
                query_content_version_url,
                query_0_url,  # Throws Exception
            ],
            responses.calls,
        )

        # Assert log.
        task.logger.info.assert_has_calls(
            [
                mock.call("Beginning task: InsertContentDocument"),
                mock.call(f"As user: {task.org_config.username}"),
                mock.call(f"In org: {task.org_config.org_id}"),
                mock.call(""),
                mock.call(f'Inserting ContentVersion from {task.options["path"]}'),
                mock.call(
                    f'Success!  Inserted ContentDocument "{self.content_document_id}".'
                ),
                mock.call(""),
                mock.call("Querying records to link to the new ContentDocument."),
                mock.call(f"    {queries[0]}"),
            ]
        )
        task.logger.error.assert_has_calls(
            [
                mock.call(
                    "An error occurred querying records to link to the ContentDocument."
                ),
            ]
        )

    @responses.activate
    def test_task__fails__get_record_ids_to_link__generic_exception(
        self,
    ):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
            },
        )
        task.logger = mock.Mock()
        task._insert_content_document = mock.Mock(return_value=self.content_document_id)
        task._get_record_ids_to_link = mock.Mock(side_effect=CumulusCIException)

        # Run task.
        with pytest.raises(CumulusCIException):
            task()

        # Assert method calls.
        task._insert_content_document.assert_called_once()

        task._get_record_ids_to_link.assert_called_once()

        # Assert log.
        task.logger.error.assert_has_calls(
            [
                mock.call(
                    "An error occurred querying records to link to the ContentDocument."
                ),
            ]
        )

    @responses.activate
    def test_task__fails___link_records_to_content_document(self):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
                "queries": self.queries,
            },
        )
        task.logger = mock.Mock()

        api_version = f"v{task.project_config.project__package__api_version}"
        data_url = f"{task.org_config.instance_url}/services/data/{api_version}"

        # Insert ContentVersion call.
        insert_content_version_url = f"{data_url}/sobjects/ContentVersion/"
        responses.add(
            responses.POST,
            insert_content_version_url,
            content_type="application/json",
            status=201,
            json={"id": self.content_version_id, "success": True, "errors": []},
        )

        # Query ContentVersion.ContentDocumentId call.
        content_version_query = f"SELECT Id, ContentDocumentId FROM ContentVersion WHERE Id = '{self.content_version_id}'"
        query_content_version_url = (
            f"{data_url}/query/?q={urllib.parse.quote_plus(content_version_query)}"
        )
        responses.add(
            responses.GET,
            query_content_version_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "ContentVersion",
                            "url": f"/services/data/{api_version}/sobjects/ContentVersion/{self.content_version_id}",
                        },
                        "Id": self.content_version_id,
                        "ContentDocumentId": self.content_document_id,
                    }
                ],
            },
        )

        # Record query 0: Returns account_ids 0 and 1.
        query_0_url = f"{data_url}/query/?q={urllib.parse.quote_plus(self.queries[0])}"
        responses.add(
            responses.GET,
            query_0_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 2,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[0]}",
                        },
                        "Id": self.account_ids[0],
                    },
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[1]}",
                        },
                        "Id": self.account_ids[1],
                    },
                ],
            },
        )

        # Record query 1: Returns no records.
        query_1_url = f"{data_url}/query/?q={urllib.parse.quote_plus(self.queries[1])}"
        responses.add(
            responses.GET,
            query_1_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 0,
                "done": True,
                "records": [],
            },
        )

        # Record query 2: Returns account_ids 1 and 2.
        query_2_url = f"{data_url}/query/?q={urllib.parse.quote_plus(self.queries[2])}"
        responses.add(
            responses.GET,
            query_2_url,
            content_type="application/json",
            status=201,
            json={
                "totalSize": 2,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[1]}",
                        },
                        "Id": self.account_ids[1],
                    },
                    {
                        "attributes": {
                            "type": "Account",
                            "url": f"/services/data/{api_version}/sobjects/Account/{self.account_ids[2]}",
                        },
                        "Id": self.account_ids[2],
                    },
                ],
            },
        )

        # Insert ContentVersion call fails.
        insert_content_document_link_url = f"{data_url}/sobjects/ContentDocumentLink/"
        responses.add(
            responses.POST,
            insert_content_document_link_url,
            content_type="application/json",
            status=400,
            json=[
                {
                    "message": "Required fields are missing: [ContentDocumentId]",
                    "errorCode": "REQUIRED_FIELD_MISSING",
                    "fields": ["ContentDocumentId"],
                }
            ],
        )

        # Run task.
        with pytest.raises(CumulusCIException):
            task()

        # Assert calls.
        assert_call_urls(
            [
                insert_content_version_url,
                query_content_version_url,
                query_0_url,
                query_1_url,
                query_2_url,
                insert_content_document_link_url,  # Throws Exception
            ],
            responses.calls,
        )

        # Assert log.
        task.logger.info.assert_has_calls(
            [
                mock.call(f'Inserting ContentVersion from {task.options["path"]}'),
                mock.call(
                    f'Success!  Inserted ContentDocument "{self.content_document_id}".'
                ),
                mock.call(""),
                mock.call("Querying records to link to the new ContentDocument."),
                mock.call(f"    {self.queries[0]}"),
                mock.call(f"        (2) {self.account_ids[0]}, {self.account_ids[1]}"),
                mock.call(f"    {self.queries[1]}"),
                mock.call("        🚫 No records found."),
                mock.call(f"    {self.queries[2]}"),
                mock.call(f"        (2) {self.account_ids[1]}, {self.account_ids[2]}"),
                mock.call(""),
                mock.call(
                    "Inserting ContentDocumentLink records to link the ContentDocument."
                ),
                mock.call('    ShareType: "{share_type}"'.format(**task.options)),
                mock.call('    Visibility: "{visibility}"'.format(**task.options)),
            ]
        )

        task.logger.error.assert_has_calls(
            [
                mock.call(
                    "An error occurred linking queried records to the ContentDocument."
                ),
            ]
        )

    @responses.activate
    def test_task__fails___link_records_to_content_document__generic_exception(
        self,
    ):
        task = create_task(
            InsertContentDocument,
            {
                "path": self.file_path,
            },
        )
        task.logger = mock.Mock()
        task._insert_content_document = mock.Mock(return_value=self.content_document_id)
        task._get_record_ids_to_link = mock.Mock()
        task._link_records_to_content_document = mock.Mock(
            side_effect=CumulusCIException
        )

        # Run task.
        with pytest.raises(CumulusCIException):
            task()

        # Assert method calls.
        task._insert_content_document.assert_called_once()

        task._get_record_ids_to_link.assert_called_once()

        task._link_records_to_content_document.assert_called_once_with(
            self.content_document_id,
            task._get_record_ids_to_link.return_value,
        )

        # Assert log.
        task.logger.error.assert_has_calls(
            [
                mock.call(
                    "An error occurred linking queried records to the ContentDocument."
                ),
            ]
        )
