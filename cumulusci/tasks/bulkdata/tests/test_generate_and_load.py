import os.path

import unittest
from unittest import mock

from cumulusci.tasks.bulkdata import GenerateAndLoadData
from cumulusci.core.exceptions import TaskOptionsError

from .test_bulkdata import _make_task


class TestGenerateAndLoadData(unittest.TestCase):
    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._dataload")
    def test_generate_and_load_data(self, _dataload):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        task = _make_task(
            GenerateAndLoadData,
            {
                "options": {
                    "num_records": 12,
                    "mapping": mapping_file,
                    "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                }
            },
        )

        task()
        _dataload.assert_called_once()

    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._dataload")
    def test_generate_and_load_data_batched(self, _dataload):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        task = _make_task(
            GenerateAndLoadData,
            {
                "options": {
                    "num_records": 20,
                    "mapping": mapping_file,
                    "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                    "batch_size": 8,
                }
            },
        )

        task()
        calls = _dataload.mock_calls
        assert len(calls) == 3
        task_options = [call[1][0] for call in calls]  # get at the args
        for i in range(0, 3):
            assert task_options[i]["current_batch_number"] == i
            assert task_options[i]["batch_size"] == 8
            assert task_options[i]["mapping"] == mapping_file
        assert task_options[0]["num_records"] == task_options[1]["num_records"] == 8
        assert task_options[2]["num_records"] == 4

    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._dataload")
    def test_batchsize_zero(self, _dataload):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        options = {
            "options": {
                "num_records": 20,
                "mapping": mapping_file,
                "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                "batch_size": 0,
            }
        }

        with self.assertRaises(TaskOptionsError):
            _make_task(GenerateAndLoadData, options)

    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._dataload")
    def test_batchsize_matches_numrecords(self, _dataload):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        task = _make_task(
            GenerateAndLoadData,
            {
                "options": {
                    "num_records": 12,
                    "mapping": mapping_file,
                    "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                    "batch_size": 12,
                }
            },
        )

        task()
        _dataload.assert_called_once()
