from contextlib import contextmanager
from unittest import mock

from cumulusci.tasks.bulkdata.extract_dataset_utils.tests.test_synthesize_extract_declarations import (
    _fake_get_org_schema,
    describe_for,
)
from cumulusci.tasks.sample_data.capture_sample_data import CaptureSampleData


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
    ):
        yield


class TestCaptureDatasetss:
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
            # default dataset should created
            Dataset.assert_any_call("default", mock.ANY, mock.ANY, org_config, mock.ANY)
            # and extracted
            Dataset().__enter__().extract.assert_called_with()

    @mock.patch("cumulusci.tasks.sample_data.capture_sample_data.Dataset")
    def test_named_extract(
        self,
        Dataset,
        create_task,
        org_config,
    ):
        with setup_test(org_config):
            Dataset().__enter__().path.exists.return_value = False
            task = create_task(CaptureSampleData, {"dataset": "mydataset"})
            task()
            # named dataset should create
            Dataset.assert_any_call(
                "mydataset", mock.ANY, mock.ANY, org_config, mock.ANY
            )
            Dataset().__enter__().create.assert_called_with()
            # and extracted
            Dataset().__enter__().extract.assert_called_with()
