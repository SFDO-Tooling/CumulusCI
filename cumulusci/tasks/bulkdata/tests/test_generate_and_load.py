import os.path
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata import GenerateAndLoadData

from .utils import _make_task


class TestGenerateAndLoadData:
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

        with pytest.raises(TaskOptionsError):
            _make_task(GenerateAndLoadData, options)

    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._dataload")
    def test_no_datageneration_task_specified(self, _dataload):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        options = {"options": {"num_records": 20, "mapping": mapping_file}}

        with pytest.raises(TaskOptionsError) as e:
            _make_task(GenerateAndLoadData, options)

        assert "No data generation task" in str(e.value)

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

    def test_bad_mapping_file_path(self):
        with pytest.raises(TaskOptionsError):
            _make_task(
                GenerateAndLoadData,
                {
                    "options": {
                        "num_records": 12,
                        "mapping": "does_not_exist",
                        "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                        "batch_size": 12,
                    }
                },
            )

    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._dataload")
    def test_missing_mapping_file_when_needed(self, _dataload):
        with pytest.raises(TaskOptionsError):
            task = _make_task(
                GenerateAndLoadData,
                {
                    "options": {
                        "num_records": 12,
                        "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                        "batch_size": 12,
                    }
                },
            )
            task()

    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._dataload")
    def test_missing_mapping_file_path(self, _dataload):
        task = _make_task(
            GenerateAndLoadData,
            {
                "options": {
                    "num_records": 12,
                    "data_generation_task": "cumulusci.tasks.bulkdata.tests.mock_data_factory_without_mapping.GenerateDummyData",
                    "batch_size": 12,
                }
            },
        )
        task()
        calls = _dataload.mock_calls
        assert calls[0][1][0]["generate_mapping_file"]

    def test_bad_options(self):
        with pytest.raises(TaskOptionsError):
            _make_task(
                GenerateAndLoadData,
                {
                    "options": {
                        "num_records": 12,
                        "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                        "database_url": "not_a_real_url:///non-url",
                        "batch_size": -1,
                    }
                },
            )

    def test_loader_subtask(self):
        class MockLoadData:
            def __init__(self, *args, **kwargs):
                options = kwargs["task_config"].options
                assert options["num_records"] == 12
                assert options["database_url"].startswith("sqlite")
                assert options["bulk_mode"] == "Serial"
                assert "mapping_vanilla_sf" in options["mapping"]

            def __call__(self):
                self.return_values = {}

        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        with mock.patch(
            "cumulusci.tasks.bulkdata.generate_and_load_data.LoadData", MockLoadData
        ):
            task = _make_task(
                GenerateAndLoadData,
                {
                    "options": {
                        "num_records": 12,
                        "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                        "mapping": mapping_file,
                        "bulk_mode": "Serial",
                    }
                },
            )
            task()

    def test_error_on_tables_exist(self):
        class FakeEngine:
            pass

        class FakeMetadata:
            tables = {"foo": mock.MagicMock}

        def _setup_engine(*args, **kwargs):
            return FakeEngine(), FakeMetadata()

        with mock.patch(
            "cumulusci.tasks.bulkdata.generate_and_load_data.GenerateAndLoadData._setup_engine",
            _setup_engine,
        ):
            with pytest.raises(TaskOptionsError):
                task = _make_task(
                    GenerateAndLoadData,
                    {
                        "options": {
                            "num_records": 12,
                            "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                            "batch_size": 12,
                            "database_url": "not_a_real:///",
                        }
                    },
                )

                task()

    def test_working_directory(self):
        class MockLoadData:
            def __init__(self, *args, **kwargs):
                options = kwargs["task_config"].options
                assert Path(options["working_directory"]).exists()

            def __call__(self):
                self.return_values = {}

        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        with TemporaryDirectory() as t:
            with mock.patch(
                "cumulusci.tasks.bulkdata.generate_and_load_data.LoadData", MockLoadData
            ):
                assert not list(Path(t).glob("*"))
                task = _make_task(
                    GenerateAndLoadData,
                    {
                        "options": {
                            "num_records": 12,
                            "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                            "working_directory": t,
                            "mapping": mapping_file,
                        }
                    },
                )
                task()
                assert list(Path(t).glob("*"))

    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._dataload")
    @mock.patch(
        "cumulusci.tasks.bulkdata.generate_and_load_data.validate_and_inject_mapping"
    )
    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._datagen")
    def test_validate_only_mode(self, mock_datagen, mock_validate, _dataload):
        """Test that validate_only mode validates without loading data"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        # Mock ValidationResult
        validation_result = ValidationResult()
        mock_validate.return_value = validation_result

        task = _make_task(
            GenerateAndLoadData,
            {
                "options": {
                    "num_records": 12,
                    "mapping": mapping_file,
                    "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                    "validate_only": True,
                }
            },
        )

        task()

        # Verify data generation was called (to create mapping)
        mock_datagen.assert_called_once()

        # Verify validation was called
        mock_validate.assert_called_once()

        # Verify load was NOT called
        _dataload.assert_not_called()

        # Verify return values contain validation_result
        assert "validation_result" in task.return_values
        assert task.return_values["validation_result"] == validation_result

    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._dataload")
    @mock.patch(
        "cumulusci.tasks.bulkdata.generate_and_load_data.validate_and_inject_mapping"
    )
    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._datagen")
    def test_validate_only_with_errors(self, mock_datagen, mock_validate, _dataload):
        """Test that validate_only mode returns errors without raising exception"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        # Mock ValidationResult with errors
        validation_result = ValidationResult()
        validation_result.add_error("Test error: Field does not exist")
        validation_result.add_warning("Test warning: Field has no permissions")
        mock_validate.return_value = validation_result

        task = _make_task(
            GenerateAndLoadData,
            {
                "options": {
                    "num_records": 12,
                    "mapping": mapping_file,
                    "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                    "validate_only": True,
                }
            },
        )

        # Should not raise exception even with errors
        task()

        # Verify data generation was called
        mock_datagen.assert_called_once()

        # Verify validation was called
        mock_validate.assert_called_once()

        # Verify load was NOT called
        _dataload.assert_not_called()

        # Verify return values contain validation_result with errors
        assert "validation_result" in task.return_values
        assert task.return_values["validation_result"].has_errors()
        assert len(task.return_values["validation_result"].errors) == 1
        assert len(task.return_values["validation_result"].warnings) == 1

    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._dataload")
    def test_validate_only_false_loads_data(self, _dataload):
        """Test that validate_only=False performs normal data loading"""
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        task = _make_task(
            GenerateAndLoadData,
            {
                "options": {
                    "num_records": 12,
                    "mapping": mapping_file,
                    "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                    "validate_only": False,
                }
            },
        )

        task()

        # Verify load WAS called
        _dataload.assert_called_once()

        # Verify return values contain load_results, not validation_result
        assert "load_results" in task.return_values
        assert "validation_result" not in task.return_values

    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._dataload")
    @mock.patch(
        "cumulusci.tasks.bulkdata.generate_and_load_data.validate_and_inject_mapping"
    )
    @mock.patch("cumulusci.tasks.bulkdata.GenerateAndLoadData._datagen")
    def test_validate_only_with_working_directory(
        self, mock_datagen, mock_validate, _dataload
    ):
        """Test that validate_only respects working_directory option"""
        from cumulusci.tasks.bulkdata.mapping_parser import ValidationResult

        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        validation_result = ValidationResult()
        mock_validate.return_value = validation_result

        with TemporaryDirectory() as t:
            task = _make_task(
                GenerateAndLoadData,
                {
                    "options": {
                        "num_records": 12,
                        "mapping": mapping_file,
                        "data_generation_task": "cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData",
                        "validate_only": True,
                        "working_directory": t,
                    }
                },
            )

            task()

            # Verify data generation was called
            mock_datagen.assert_called_once()

            # Verify validation was called
            mock_validate.assert_called_once()

            # Verify load was NOT called
            _dataload.assert_not_called()

            # Verify working directory was used (should have generated files)
            assert list(Path(t).glob("*"))
