from unittest import mock

import pytest
import responses

from cumulusci.tasks.bulkdata import LoadData
from cumulusci.tasks.bulkdata.step import DataApi, DataOperationStatus
from cumulusci.tests.util import mock_describe_calls

current_sf_version = "52.0"


class TestUpsert:
    # bulk API not supported by VCR yet
    @pytest.mark.needs_org()
    def test_upsert_external_id_field(
        self, create_task, cumulusci_test_repo_root, sf, delete_data_from_org
    ):
        delete_data_from_org(["Entitlement", "Opportunity", "Contact", "Account"])
        self._common_integration_testing_code(
            "bulk", create_task, cumulusci_test_repo_root, sf
        )

    def _common_integration_testing_code(
        self, api, create_task, cumulusci_test_repo_root, sf
    ):
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
        with mock.patch.object(task.logger, "info"):
            task()
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
                    "Insert Contacts": {
                        "sobject": "Contact",
                        "record_type": None,
                        "status": DataOperationStatus.SUCCESS,
                        "job_errors": [],
                        "records_processed": 16,
                        "total_row_errors": 0,
                    },
                }
            }, result
            accounts = sf.query("select Name from Account")
            accounts = {account["Name"] for account in accounts["records"]}
            assert "Sitwell-Bluth" in accounts
            contacts = sf.query("select FirstName from Contact")
            contacts = {contact["FirstName"] for contact in contacts["records"]}
            assert "Annyong" not in contacts
            assert "JaJavier" not in contacts
            assert "UPSERT" in str(task.logger.info.mock_calls)

        with mock.patch.object(task.logger, "info"):
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
            result = task.return_values
            contacts = sf.query("select FirstName from Contact")
            contacts = {contact["FirstName"] for contact in contacts["records"]}

            assert "Annyong" in contacts
            assert "JaJavier" in contacts
            assert "UPSERT" in str(task.logger.mock_calls)

    @pytest.mark.needs_org()
    def test_upsert__rest(
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
        self._common_integration_testing_code(
            "rest",
            create_task,
            cumulusci_test_repo_root,
            sf,
        )

    @responses.activate
    def test_upsert_rest__faked(
        self,
        create_task,
        cumulusci_test_repo_root,
        run_code_without_recording,
        delete_data_from_org,
    ):
        ver = current_sf_version
        responses.add(
            method="PATCH",
            url=f"https://orgname.my.salesforce.com/services/data/v{ver}/composite/sobjects/Contact/Email",
            status=200,
            json=[  # TODO: Compress this
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
        mock_describe_calls(domain="orgname.my.salesforce.com", version="52.0")
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/upsert/upsert_example_2.sql",
                "mapping": cumulusci_test_repo_root
                / "datasets/upsert/upsert_mapping_rest__external_id.yml",
                "ignore_row_errors": True,
                "set_recently_viewed": False,
            },
        )
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
                    "Insert Contacts": {
                        "sobject": "Contact",
                        "record_type": None,
                        "status": DataOperationStatus.SUCCESS,
                        "job_errors": [],
                        "records_processed": 3,
                        "total_row_errors": 0,
                    },
                }
            }, rc
            relevant_debug_call = [
                call
                for call in task.logger.debug.mock_calls
                if call.args[0] == "Creating %s Operation for %s using %s"
            ][0]
            assert relevant_debug_call.args[-1] == DataApi.REST

    @responses.activate
    def test_upsert__fake_bulk(self, create_task, cumulusci_test_repo_root):
        mock_describe_calls(domain="orgname.my.salesforce.com", version="52.0")
        responses.add(
            method="POST",
            url=f"https://orgname.my.salesforce.com/services/async/{current_sf_version}/job",
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
        <apiVersion>v{current_sf_version}</apiVersion>
        <numberRecordsFailed>0</numberRecordsFailed>

        <totalProcessingTime>0</totalProcessingTime>
        <apiActiveProcessingTime>0</apiActiveProcessingTime>

        <apexProcessingTime>0</apexProcessingTime>
        </jobInfo>""",
        )
        responses.add(
            method="POST",
            url=f"https://orgname.my.salesforce.com/services/async/{current_sf_version}/job/750P0000005mX3LIAU",
            status=200,
            body=""""<?xml version="1.0" encoding="UTF-8"?>
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
            <apiVersion>v52.0</apiVersion>
            <numberRecordsFailed>0</numberRecordsFailed>
            <totalProcessingTime>0</totalProcessingTime>
            <apiActiveProcessingTime>0</apiActiveProcessingTime>
            <apexProcessingTime>0</apexProcessingTime>
            </jobInfo>""",
        )

        responses.add(
            method="GET",
            url=f"https://orgname.my.salesforce.com/services/async/{current_sf_version}/job/750P0000005mX3LIAU",
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
        <numberRecordsProcessed>0</numberRecordsProcessed>

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
            url=f"https://orgname.my.salesforce.com/services/async/{current_sf_version}/job/750P0000005mX3LIAU/batch",
            status=200,
            body="""<?xml version="1.0" encoding="UTF-8"?>
            <batchInfoList xmlns="http://www.force.com/2009/06/asyncapi/dataload"/>""",
        )

        responses.add(
            method="POST",
            url=f"https://orgname.my.salesforce.com/services/async/{current_sf_version}/job/750P0000005mX3LIAU/batch",
            status=200,
            body="""<?xml version="1.0" encoding="UTF-8"?>
            <batchInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">

        <id>751P0000006fIUAIA2</id>
        <jobId>750P0000005mX2wIAE</jobId>
        <state>Queued</state>

        <createdDate>2022-03-02T04:14:44.000Z</createdDate>
        <systemModstamp>2022-03-02T04:14:44.000Z</systemModstamp>

        <numberRecordsProcessed>0</numberRecordsProcessed>
        <numberRecordsFailed>0</numberRecordsFailed>

        <totalProcessingTime>0</totalProcessingTime>
        <apiActiveProcessingTime>0</apiActiveProcessingTime>

        <apexProcessingTime>0</apexProcessingTime>
        </batchInfo>""",
        )

        responses.add(
            method="GET",
            url=f"https://orgname.my.salesforce.com/services/async/{current_sf_version}/job/750P0000005mX3LIAU/batch/751P0000006fIUAIA2/result",
            status=200,
            body="""""Id","Success","Created","Error"
        "003P000001Y5yvdIAB","true","false",""
        "003P000001Y5ywMIAR","true","false",""
        "003P000001Y5ywNIAR","true","false",""
        "003P000001Y5ywOIAR","true","false","" """,
        )

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
                    "Insert Contacts": {
                        "sobject": "Contact",
                        "record_type": None,
                        "status": DataOperationStatus.SUCCESS,
                        "job_errors": [],
                        "records_processed": 0,
                        "total_row_errors": 0,
                    },
                }
            }, ret
            relevant_debug_call = [
                call
                for call in task.logger.debug.mock_calls
                if call.args[0] == "Creating %s Operation for %s using %s"
            ][0]
            assert relevant_debug_call.args[-1] == DataApi.BULK
