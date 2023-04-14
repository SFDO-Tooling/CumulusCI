from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.extract_dataset_utils.tests.test_synthesize_extract_declarations import (
    _fake_get_org_schema,
    describe_for,
)
from cumulusci.tasks.sample_data.capture_sample_data import CaptureSampleData
from cumulusci.tests.util import CURRENT_SF_API_VERSION


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
        "cumulusci.tasks.sample_data.capture_sample_data.get_org_schema",
        lambda _sf, org_config, **kwargs: _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            included_objects=["Account", "Contact", "Opportunity"],
            **kwargs,
        ),
    ), responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            f"{org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects",
            json={"sobjects": [{"name": "WebLink"}]},
            status=200,
        )
        yield


class TestCaptureDatasets:
    @mock.patch("cumulusci.tasks.sample_data.capture_sample_data.Dataset")
    def test_simple_extract(
        self,
        Dataset,
        create_task,
        org_config,
    ):
        with setup_test(org_config):
            task = create_task(CaptureSampleData, {})
            task()
            print("Dataset.mock_calls", Dataset.mock_calls)
            # default dataset should created
            Dataset.assert_any_call("default", mock.ANY, mock.ANY, org_config, mock.ANY)
            # and extracted
            Dataset().__enter__().extract.assert_called_with(
                {}, task.logger, None, mock.ANY, None
            )

    @mock.patch("cumulusci.tasks.sample_data.capture_sample_data.Dataset")
    def test_named_extract(
        self,
        Dataset,
        create_task,
        org_config,
    ):
        with setup_test(org_config), TemporaryDirectory() as t:
            extraction_definition = Path(t) / "test_extract_definition"
            with open(extraction_definition, "w") as f:
                f.write("")  # Doesn't matter. We won't parse it

            loading_rules = Path(t) / "test_load_definition"
            with open(loading_rules, "w") as f:
                f.write("[]")  # Doesn't matter. We won't parse it

            Dataset().__enter__().path.exists.return_value = False
            task = create_task(
                CaptureSampleData,
                {
                    "dataset": "mydataset",
                    "extraction_definition": extraction_definition,
                    "loading_rules": loading_rules,
                },
            )
            task()
            # named dataset should create
            Dataset.assert_any_call(
                "mydataset", mock.ANY, mock.ANY, org_config, mock.ANY
            )
            Dataset().__enter__().create.assert_called_with()
            # and extracted
            Dataset().__enter__().extract.assert_called_with(
                {}, task.logger, extraction_definition, mock.ANY, loading_rules
            )

    @mock.patch("cumulusci.tasks.sample_data.capture_sample_data.Dataset")
    def test_option_error(
        self,
        Dataset,
        create_task,
        org_config,
    ):
        task = create_task(
            CaptureSampleData,
            {
                "dataset": "mydataset",
                "extraction_definition": Path("xyzzy.bbb.yml"),
            },
        )
        with pytest.raises(TaskOptionsError, match="xyzzy.bbb.yml"):
            task()
