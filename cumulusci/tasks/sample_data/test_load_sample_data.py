import logging
from contextlib import contextmanager
from unittest import mock

import pytest

from cumulusci.core.datasets import Dataset as RealDataset
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.extract_dataset_utils.tests.test_synthesize_extract_declarations import (
    _fake_get_org_schema,
    describe_for,
)
from cumulusci.tasks.sample_data.load_sample_data import LoadSampleData


@contextmanager
def setup_test(org_config):
    object_counts = {"Account": 6, "Contact": 1, "Opportunity": 5}
    obj_describes = (
        describe_for("Account"),
        describe_for("Contact"),
        describe_for("Opportunity"),
    )
    with mock.patch.object(
        type(org_config), "is_person_accounts_enabled", False
    ), mock.patch(
        "cumulusci.tasks.sample_data.load_sample_data.get_org_schema",
        lambda _sf, org_config, **kwargs: _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            included_objects=["Account", "Contact", "Opportunity"],
            **kwargs,
        ),
    ):
        yield


class TestLoadDatasets:
    @mock.patch("cumulusci.tasks.sample_data.load_sample_data.Dataset")
    def test_simple_extract(
        self,
        Dataset,
        create_task,
        org_config,
    ):
        with setup_test(org_config):
            org_config.config["config_name"] = "dev"
            task = create_task(LoadSampleData, {"ignore_row_errors": True})
            task()
            # default dataset should be opened
            Dataset.assert_any_call(
                org_config.config_name, mock.ANY, mock.ANY, org_config, mock.ANY
            )
            # and loaded
            Dataset().__enter__().load.assert_called_with(
                {"ignore_row_errors": True}, task.logger
            )

    @mock.patch("cumulusci.tasks.sample_data.load_sample_data.Dataset")
    def test_simple_extract__name(
        self,
        Dataset,
        create_task,
        org_config,
    ):
        with setup_test(org_config):
            task = create_task(LoadSampleData, {"dataset": "mydataset"})
            task()
            # default dataset should opened
            Dataset.assert_any_call(
                "mydataset", mock.ANY, mock.ANY, org_config, mock.ANY
            )
            # and loaded
            Dataset().__enter__().load.assert_called_with(
                {"dataset": "mydataset"}, task.logger
            )

    @mock.patch("cumulusci.tasks.sample_data.load_sample_data.Dataset")
    def test_simple_extract__scratch_config(
        self, Dataset, sf, create_task, org_config, project_config
    ):
        ds = RealDataset(
            "qwerty",
            project_config,
            sf,
            org_config,
        )
        with setup_test(org_config):
            org_config.config["config_name"] = "qwerty"
            ds.path.mkdir()
            try:
                task = create_task(LoadSampleData, {})
                task()
                # default dataset should opened
                Dataset.assert_any_call(
                    "qwerty", mock.ANY, mock.ANY, org_config, mock.ANY
                )
                # and loaded
                Dataset().__enter__().load.assert_called_with({}, task.logger)
            finally:
                ds.delete()

    def test_no_match_to_name(self, create_task):
        task = create_task(LoadSampleData, {"dataset": "f.z.f.efa.f"})
        with pytest.raises(TaskOptionsError, match="Could not find.*f.z.f.efa.f"):
            task()

    @mock.patch(
        "cumulusci.tasks.sample_data.load_sample_data.Dataset", spec=RealDataset
    )
    def test_no_dataset_available(self, Dataset, caplog, create_task, org_config):
        caplog.set_level(logging.INFO)
        with setup_test(org_config):
            org_config.config["config_name"] = "qa"
            task = create_task(LoadSampleData, {})
            Dataset().exists.return_value = False
            assert not Dataset().exists()
            task()
            Dataset().__enter__.assert_not_called()
            assert "No contextual sample data found" in caplog.text
