import re
from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata import LoadData
from cumulusci.tasks.bulkdata.step import DataApi, DataOperationStatus
from cumulusci.tests.util import CURRENT_SF_API_VERSION, mock_describe_calls


class TestUpsert:
    # Would be nice to slim down this VCR further. It's still 50kb.
    # The next step of VCR compression would be to have some templates
    # for XML that can be reused when matched.
    # gzip would be another (albeit binary) answer.
    @pytest.mark.vcr()
    def test_upsert_external_id_field(
        self,
        create_task,
        cumulusci_test_repo_root,
        sf,
        delete_data_from_org,
        run_code_without_recording,
    ):
        run_code_without_recording(
            lambda: delete_data_from_org(
                ["Entitlement", "Opportunity", "Contact", "Account"]
            )
        )
        self._test_two_upserts_and_check_results(
            "bulk", create_task, cumulusci_test_repo_root, sf
        )

    @pytest.mark.vcr()
    def test_simple_upsert__rest(
        self,
        create_task,
        cumulusci_test_repo_root,
        run_code_without_recording,
        delete_data_from_org,
        sf,
    ):

        run_code_without_recording(
            lambda: delete_data_from_org(
                ["Entitlement", "Opportunity", "Contact", "Account"]
            )
        )
        self._test_two_upserts_and_check_results(
            "rest",
            create_task,
            cumulusci_test_repo_root,
            sf,
        )

    def _test_two_upserts_and_check_results(
        self, api, create_task, cumulusci_test_repo_root, sf
    ):
        # seed sample data, using a mixture of inserts and
        # upserts-into-empty (which should behave as inserts)
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/upsert/upsert_before_data.sql",
                "mapping": cumulusci_test_repo_root
                / f"datasets/upsert/upsert_mapping_{api}.yml",
                "ignore_row_errors": True,
                "set_recently_viewed": False,
            },
        )

        # load the data and double-check that it loaded as expected
        with mock.patch.object(task.logger, "info"):
            task()
            assert "UPSERT" in str(task.logger.info.mock_calls)

        # check that the right steps were executed
        result = task.return_values
        assert result == {
            "step_results": {
                "Insert Accounts": {
                    "sobject": "Account",
                    "record_type": None,
                    "status": DataOperationStatus.SUCCESS,
                    "job_errors": [],
                    "records_processed": 1,
                    "total_row_errors": 0,
                },
                "Upsert Contacts": {
                    "sobject": "Contact",
                    "record_type": None,
                    "status": DataOperationStatus.SUCCESS,
                    "job_errors": [],
                    "records_processed": 16,
                    "total_row_errors": 0,
                },
                "Insert Opportunities": {
                    "sobject": "Opportunity",
                    "record_type": None,
                    "status": DataOperationStatus.SUCCESS,
                    "job_errors": [],
                    "records_processed": 0,
                    "total_row_errors": 0,
                },
            }
        }, result

        # check that Salesforce contains what we expectdd
        accounts = sf.query("select Name from Account")
        accounts = {account["Name"] for account in accounts["records"]}
        assert "Sitwell-Bluth" in accounts
        contacts = sf.query("select FirstName from Contact")["records"]
        firstnames = {contact["FirstName"] for contact in contacts}
        assert "Nichael" not in firstnames
        assert "George Oscar" not in firstnames

        # Upsert against the data we already created
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/upsert/upsert_example_2.sql",
                "mapping": cumulusci_test_repo_root
                / f"datasets/upsert/upsert_mapping_{api}.yml",
                "ignore_row_errors": True,
                "set_recently_viewed": False,
            },
        )
        task()

        # check that the right data was loaded
        contacts = sf.query(
            "select FirstName,(select Name from Opportunities) from Contact"
        )["records"]
        firstnames = {contact["FirstName"] for contact in contacts}

        assert "Nichael" in firstnames
        assert "George Oscar" in firstnames
        opportunity_names = [
            contact["Opportunities"]["records"][0]["Name"]
            for contact in contacts
            if contact["Opportunities"]
        ]
        assert set(opportunity_names) == set(
            ["Espionage Opportunity", "Illusional Opportunity"]
        ), set(opportunity_names)

    @responses.activate
    def test_upsert_rest__faked(
        self, create_task, cumulusci_test_repo_root, org_config
    ):
        domain = org_config.get_domain()
        ver = CURRENT_SF_API_VERSION
        responses.add(
            method="PATCH",
            url=f"https://{domain}/services/data/v{ver}/composite/sobjects/Contact/Email",
            status=200,
            json=[
                {
                    "id": "003P000001Y5exdIAB",
                    "success": True,
                    "errors": [],
                    "created": True,
                },
                {
                    "id": "003P000001Y5exXIAR",
                    "success": True,
                    "errors": [],
                    "created": False,
                },
                {
                    "id": "003P000001Y5exYIAR",
                    "success": True,
                    "errors": [],
                    "created": False,
                },
            ],
        )
        responses.add(
            method="POST",
            url=f"https://{domain}/services/data/v{ver}/composite/sobjects",
            status=200,
            json=[{"id": "001J000002jcjvnIAA", "success": True, "errors": []}],
        )
        mock_describe_calls(domain=domain, version=CURRENT_SF_API_VERSION)
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/upsert/upsert_example_2.sql",
                "mapping": cumulusci_test_repo_root
                / "datasets/upsert/upsert_mapping_rest.yml",
                "ignore_row_errors": True,
                "set_recently_viewed": False,
            },
        )
        task._update_credentials = mock.Mock()
        with mock.patch.object(task.logger, "debug"):
            rc = task()
            assert rc == {
                "step_results": {
                    "Insert Accounts": {
                        "sobject": "Account",
                        "record_type": None,
                        "status": DataOperationStatus.SUCCESS,
                        "job_errors": [],
                        "records_processed": 0,
                        "total_row_errors": 0,
                    },
                    "Upsert Contacts": {
                        "sobject": "Contact",
                        "record_type": None,
                        "status": DataOperationStatus.SUCCESS,
                        "job_errors": [],
                        "records_processed": 3,
                        "total_row_errors": 0,
                    },
                    "Insert Opportunities": {
                        "sobject": "Opportunity",
                        "record_type": None,
                        "status": DataOperationStatus.SUCCESS,
                        "job_errors": [],
                        "records_processed": 1,
                        "total_row_errors": 0,
                    },
                }
            }, rc

            relevant_debug_statement = look_for_operation_creation_debug_statement(
                task.logger.debug.mock_calls
            )
            assert relevant_debug_statement == str(
                DataApi.REST
            ), relevant_debug_statement

    def _mock_bulk(self, domain):
        responses.add(
            method="GET",
            url=f"https://{domain}/services/data/v52.0/limits/recordCount?sObjects=Contact",
            status=200,
            json={"sObjects": []},
        )

        responses.add(
            method="POST",
            url=f"https://{domain}/services/async/{CURRENT_SF_API_VERSION}/job",
            status=200,
            body=f"""<?xml version="1.0" encoding="UTF-8"?>
            <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
        <id>750P0000005mX3LIAU</id>
        <operation>insert</operation>
        <object>Account</object>
        <createdById>005P0000009ajX7IAI</createdById>
        <createdDate>2022-03-02T04:14:43.000Z</createdDate>
        <systemModstamp>2022-03-02T04:14:43.000Z</systemModstamp>
        <state>Open</state>
        <concurrencyMode>Parallel</concurrencyMode>
        <contentType>CSV</contentType>
        <numberBatchesQueued>0</numberBatchesQueued>
        <numberBatchesInProgress>0</numberBatchesInProgress>
        <numberBatchesCompleted>0</numberBatchesCompleted>
        <numberBatchesFailed>0</numberBatchesFailed>
        <numberBatchesTotal>0</numberBatchesTotal>
        <numberRecordsProcessed>0</numberRecordsProcessed>
        <numberRetries>0</numberRetries>
        <apiVersion>v{CURRENT_SF_API_VERSION}</apiVersion>
        <numberRecordsFailed>0</numberRecordsFailed>
        <totalProcessingTime>0</totalProcessingTime>
        <apiActiveProcessingTime>0</apiActiveProcessingTime>
        <apexProcessingTime>0</apexProcessingTime>
        </jobInfo>""",
        )
        responses.add(
            method="POST",
            url=f"https://{domain}/services/async/{CURRENT_SF_API_VERSION}/job/750P0000005mX3LIAU",
            status=200,
            body=f""""<?xml version="1.0" encoding="UTF-8"?>
            <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
            <id>750P0000005mX3LIAU</id>
            <operation>insert</operation>
            <object>Account</object>
            <createdById>005P0000009ajX7IAI</createdById>
            <createdDate>2022-03-02T04:14:43.000Z</createdDate>
            <systemModstamp>2022-03-02T04:14:43.000Z</systemModstamp>
            <state>Closed</state>
            <concurrencyMode>Parallel</concurrencyMode>
            <contentType>CSV</contentType>
            <numberBatchesQueued>0</numberBatchesQueued>
            <numberBatchesInProgress>0</numberBatchesInProgress>
            <numberBatchesCompleted>0</numberBatchesCompleted>
            <numberBatchesFailed>0</numberBatchesFailed>
            <numberBatchesTotal>0</numberBatchesTotal>
            <numberRecordsProcessed>0</numberRecordsProcessed>
            <numberRetries>0</numberRetries>
            <apiVersion>v{CURRENT_SF_API_VERSION}.0</apiVersion>
            <numberRecordsFailed>0</numberRecordsFailed>
            <totalProcessingTime>0</totalProcessingTime>
            <apiActiveProcessingTime>0</apiActiveProcessingTime>
            <apexProcessingTime>0</apexProcessingTime>
            </jobInfo>""",
        )

        responses.add(
            method="GET",
            url=f"https://{domain}/services/async/{CURRENT_SF_API_VERSION}/job/750P0000005mX3LIAU",
            status=200,
            body="""<?xml version="1.0" encoding="UTF-8"?>
            <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
            <id>750P0000005mX3LIAU</id>
            <operation>insert</operation>
            <object>Account</object>
            <createdById>005P0000009ajX7IAI</createdById>
            <createdDate>2022-03-02T04:14:43.000Z</createdDate>
            <systemModstamp>2022-03-02T04:14:43.000Z</systemModstamp>
            <state>Closed</state>
            <concurrencyMode>Parallel</concurrencyMode>
            <contentType>CSV</contentType>
            <numberBatchesQueued>0</numberBatchesQueued>
            <numberBatchesInProgress>0</numberBatchesInProgress>
            <numberBatchesCompleted>0</numberBatchesCompleted>
            <numberBatchesFailed>0</numberBatchesFailed>
            <numberBatchesTotal>0</numberBatchesTotal>
            <numberRecordsProcessed>4</numberRecordsProcessed>
            <numberRetries>0</numberRetries>
            <apiVersion>vxx.0</apiVersion>
            <numberRecordsFailed>0</numberRecordsFailed>
            <totalProcessingTime>0</totalProcessingTime>
            <apiActiveProcessingTime>0</apiActiveProcessingTime>
            <apexProcessingTime>0</apexProcessingTime>
            </jobInfo>""",
        )
        responses.add(
            method="GET",
            url=f"https://{domain}/services/async/{CURRENT_SF_API_VERSION}/job/750P0000005mX3LIAU/batch",
            status=200,
            body="""<?xml version="1.0" encoding="UTF-8"?>
            <batchInfoList xmlns="http://www.force.com/2009/06/asyncapi/dataload"/>""",
        )

        responses.add(
            method="POST",
            url=f"https://{domain}/services/async/{CURRENT_SF_API_VERSION}/job/750P0000005mX3LIAU/batch",
            status=200,
            body="""<?xml version="1.0" encoding="UTF-8"?>
            <batchInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
        <id>751P0000006fIUAIA2</id>
        <jobId>750P0000005mX2wIAE</jobId>
        <state>Queued</state>
        <createdDate>2022-03-02T04:14:44.000Z</createdDate>
        <systemModstamp>2022-03-02T04:14:44.000Z</systemModstamp>
        <numberRecordsProcessed>4</numberRecordsProcessed>
        <numberRecordsFailed>0</numberRecordsFailed>
        <totalProcessingTime>0</totalProcessingTime>
        <apiActiveProcessingTime>0</apiActiveProcessingTime>
        <apexProcessingTime>0</apexProcessingTime>
        </batchInfo>""",
        )

        responses.add(
            method="GET",
            url=f"https://{domain}/services/async/{CURRENT_SF_API_VERSION}/job/750P0000005mX3LIAU/batch/751P0000006fIUAIA2/result",
            status=200,
            body="""""Id","Success","Created","Error"
        "003P000001Y5yvdIAB","True","false",""
        "003P000001Y5ywMIAR","True","false",""
        "003P000001Y5ywNIAR","True","false",""
        "003P000001Y5ywOIAR","True","false","" """,
        )

    @responses.activate
    def test_upsert__fake_bulk(self, create_task, cumulusci_test_repo_root, org_config):
        domain = org_config.get_domain()
        mock_describe_calls(domain=domain, version=CURRENT_SF_API_VERSION)
        self._mock_bulk(domain)
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/upsert/upsert_example_2.sql",
                "mapping": cumulusci_test_repo_root
                / "datasets/upsert/upsert_mapping_bulk.yml",
                "ignore_row_errors": True,
                "set_recently_viewed": False,
            },
        )
        task._update_credentials = mock.Mock()

        with mock.patch.object(task.logger, "debug"):
            ret = task()
            assert ret == {
                "step_results": {
                    "Insert Accounts": {
                        "sobject": "Account",
                        "record_type": None,
                        "status": DataOperationStatus.SUCCESS,
                        "job_errors": [],
                        "records_processed": 0,
                        "total_row_errors": 0,
                    },
                    "Upsert Contacts": {
                        "sobject": "Contact",
                        "record_type": None,
                        "status": DataOperationStatus.SUCCESS,
                        "job_errors": [],
                        "records_processed": 0,  # change here and above to 4 to match data
                        "total_row_errors": 0,
                    },
                    "Insert Opportunities": {
                        "sobject": "Opportunity",
                        "record_type": None,
                        "status": DataOperationStatus.SUCCESS,
                        "job_errors": [],
                        "records_processed": 0,
                        "total_row_errors": 0,
                    },
                }
            }, ret
            relevant_debug_statement = look_for_operation_creation_debug_statement(
                task.logger.debug.mock_calls
            )
            assert relevant_debug_statement == str(
                DataApi.BULK
            ), relevant_debug_statement

    def _test_two_upserts_and_check_results__complex(
        self, api, create_task, cumulusci_test_repo_root, sf
    ):
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/upsert/upsert_before_data.sql",
                "mapping": cumulusci_test_repo_root
                / f"datasets/upsert/upsert_mapping_{api}_complex.yml",
                "set_recently_viewed": False,
            },
        )
        task()
        result = task.return_values
        assert all(
            val["status"] == DataOperationStatus.SUCCESS
            for val in result["step_results"].values()
        ), result.values()
        contacts = sf.query("select Email from Contact")
        emails = {contacts["Email"] for contacts in contacts["records"]}
        assert "michael.bluth@example.com" in emails, emails
        assert "nichael.bluth@example.com" not in emails, emails
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/upsert/upsert_complex_example.sql",
                "mapping": cumulusci_test_repo_root
                / f"datasets/upsert/upsert_mapping_{api}_complex.yml",
                "set_recently_viewed": False,
            },
        )
        task()
        contacts = sf.query("select Email from Contact")
        emails = {contacts["Email"] for contacts in contacts["records"]}
        assert "michael.bluth@example.com" not in emails
        assert "nichael.bluth@example.com" in emails

    @pytest.mark.vcr()
    def test_upsert_complex_fields__bulk(
        self,
        create_task,
        cumulusci_test_repo_root,
        sf,
        delete_data_from_org,
        run_code_without_recording,
        # mock_bulk_download_for_vcr,
    ):
        run_code_without_recording(
            lambda: delete_data_from_org(
                ["Entitlement", "Opportunity", "Contact", "Account"]
            )
        )
        self._test_two_upserts_and_check_results__complex(
            "bulk", create_task, cumulusci_test_repo_root, sf
        )

    @pytest.mark.vcr()
    def test_upsert_complex_external_id_field__rest(
        self,
        create_task,
        cumulusci_test_repo_root,
        sf,
        run_code_without_recording,
        delete_data_from_org,
    ):
        run_code_without_recording(
            lambda: delete_data_from_org(
                ["Entitlement", "Opportunity", "Contact", "Account"]
            )
        )
        self._test_two_upserts_and_check_results__complex(
            "rest", create_task, cumulusci_test_repo_root, sf
        )

    @pytest.mark.vcr()
    def test_upsert_complex_external_id_field_rest__duplicate_error(
        self,
        create_task,
        cumulusci_test_repo_root,
        sf,
        run_code_without_recording,
        delete_data_from_org,
    ):
        """Test what happens if the upsert key is duplicate and therefore it is unclear
        which record to update."""

        run_code_without_recording(
            lambda: delete_data_from_org(
                ["Entitlement", "Opportunity", "Contact", "Account"]
            )
        )

        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/upsert/upsert_before_data.sql",
                "mapping": cumulusci_test_repo_root
                / "datasets/upsert/upsert_mapping_rest_complex.yml",
                "set_recently_viewed": False,
            },
        )
        task()

        # inject a duplicate to cause an error
        assert sf.query("select Name from Account where AccountNumber='420'")[
            "records"
        ][0]["Name"]
        assert sf.Account.create(
            {"Name": "xyzzy", "AccountNumber": "420"}
        )  # make a dupe

        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/upsert/upsert_complex_example.sql",
                "mapping": cumulusci_test_repo_root
                / "datasets/upsert/upsert_mapping_rest_complex.yml",
                "set_recently_viewed": False,
            },
        )
        with pytest.raises(BulkDataException) as e:
            task()
        assert "Duplicate values for upsert key:" in str(e.value)

    @responses.activate
    def test_simple_upsert__bad_key(
        self, create_task, cumulusci_test_repo_root, org_config
    ):
        domain = org_config.get_domain()
        ver = CURRENT_SF_API_VERSION
        responses.add(
            method="PATCH",
            url=f"https://{domain}/services/data/v{ver}/composite/sobjects/Contact/Email",
            status=200,
            json=[
                {
                    "id": "003P000001Y5exdIAB",
                    "success": True,
                    "errors": [],
                    "created": True,
                },
                {
                    "id": "003P000001Y5exXIAR",
                    "success": True,
                    "errors": [],
                    "created": False,
                },
                {
                    "id": "003P000001Y5exYIAR",
                    "success": True,
                    "errors": [],
                    "created": False,
                },
            ],
        )
        responses.add(
            method="POST",
            url=f"https://{domain}/services/data/v{ver}/composite/sobjects",
            status=200,
            json=[{"id": "001J000002jcjvnIAA", "success": True, "errors": []}],
        )
        mock_describe_calls(domain=domain, version=CURRENT_SF_API_VERSION)
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/upsert/upsert_example_2.sql",
                "mapping": cumulusci_test_repo_root
                / "datasets/upsert/upsert_mapping_simple__bad_key.yml",
                "ignore_row_errors": True,
                "set_recently_viewed": False,
            },
        )
        with pytest.raises(BulkDataException) as e:
            task._update_credentials = mock.Mock()
            task()
        assert "FirstName" in str(e.value)
        assert "update key" in str(e.value)


def look_for_operation_creation_debug_statement(mock_calls):
    relevant_debug_statements = (
        look_for_operation_creation_debug_statement_for_string(call.args[0])
        for call in mock_calls
    )

    return next(stmt for stmt in relevant_debug_statements if stmt)


DEBUG_MATCHER = re.compile("Creating (.*) Operation for (.*) using (.*)")


def look_for_operation_creation_debug_statement_for_string(s):
    match = DEBUG_MATCHER.match(s)
    if match:
        return match[3]
