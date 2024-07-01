from unittest import mock

import pytest

from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.mapping_parser import MappingStep
from cumulusci.tasks.bulkdata.step import DataApi, DataOperationType
from cumulusci.tasks.preflight.dataset_load import LoadDataSetCheck
from cumulusci.tasks.salesforce.tests.util import create_task


class TestLoadDataSetCheck:
    @mock.patch(
        "cumulusci.tasks.preflight.dataset_load.validate_and_inject_mapping",
        return_value=True,
    )
    def test_run_task(self, validate_and_inject_mapping):
        task = create_task(LoadDataSetCheck, {})
        assert task()
        assert task.options["dataset"] == "default"
        assert task.mapping == {
            "Account": MappingStep(
                sf_object="Account",
                table="Account",
                fields={
                    "Name": "Name",
                    "Description": "Description",
                    "ShippingStreet": "ShippingStreet",
                    "ShippingCity": "ShippingCity",
                    "ShippingState": "ShippingState",
                    "ShippingPostalCode": "ShippingPostalCode",
                    "ShippingCountry": "ShippingCountry",
                    "Phone": "Phone",
                    "AccountNumber": "AccountNumber",
                },
                lookups={},
                static={},
                filters=[],
                action=DataOperationType.INSERT,
                api=DataApi.BULK,
                batch_size=1,
                oid_as_pk=False,
                record_type=None,
                bulk_mode=None,
                anchor_date=None,
                soql_filter=None,
                update_key=(),
            ),
            "Contact": MappingStep(
                sf_object="Contact",
                table="Contact",
                fields={"FirstName": "FirstName"},
                lookups={},
                static={},
                filters=[],
                action=DataOperationType.INSERT,
                api=DataApi.BULK,
                batch_size=1,
                oid_as_pk=False,
                record_type=None,
                bulk_mode=None,
                anchor_date=None,
                soql_filter=None,
                update_key=(),
            ),
        }

    def test_mapping_file_not_found(self):
        task = create_task(LoadDataSetCheck, {"dataset": "alpha"})
        with pytest.raises(Exception) as e:
            task()
        assert "No such file or directory" in str(e.value)
        assert task.options["dataset"] == "alpha"

    @mock.patch(
        "cumulusci.tasks.preflight.dataset_load.validate_and_inject_mapping",
        side_effect=BulkDataException("An error occurred during validation"),
    )
    def test_run_fail(self, validate_and_inject_mapping):
        task = create_task(LoadDataSetCheck, {})
        task.logger = mock.Mock()
        assert not task()
        assert task.logger.error.asset_called_once_with(
            "An error occurred during validation"
        )
