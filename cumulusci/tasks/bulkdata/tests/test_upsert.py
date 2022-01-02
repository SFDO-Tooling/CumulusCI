import pytest

from cumulusci.tasks.bulkdata import LoadData
from cumulusci.tasks.bulkdata.step import DataOperationStatus


class TestUpsert:
    # bulk API not supported by VCR yet
    @pytest.mark.needs_org()
    def test_upsert_external_id_field(
        self, create_task, cumulusci_test_repo_root, sf, delete_data_from_org
    ):
        delete_data_from_org(["Entitlement", "Opportunity", "Contact", "Account"])

        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root / "datasets/upsert_example.sql",
                "mapping": cumulusci_test_repo_root / "datasets/upsert_mapping.yml",
                "ignore_row_errors": True,
            },
        )
        task()
        result = task.return_values
        assert result == {
            "step_results": {
                "Insert Accounts": {
                    "sobject": "Account",
                    "record_type": None,
                    "status": DataOperationStatus.SUCCESS,
                    "job_errors": [],
                    "records_processed": 28,
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
        }
        accounts = sf.query("select Name from Account")
        accounts = {account["Name"] for account in accounts["records"]}
        assert "Sitwell-Bluth" in accounts

        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root / "datasets/upsert_example_2.sql",
                "mapping": cumulusci_test_repo_root / "datasets/upsert_mapping.yml",
                "ignore_row_errors": True,
            },
        )
        task()
        result = task.return_values
        accounts = sf.query("select Name from Account")
        accounts = {account["Name"] for account in accounts["records"]}

        assert "Sitwell-Bluth" not in accounts
        assert "Bluth-Sitwell" in accounts
