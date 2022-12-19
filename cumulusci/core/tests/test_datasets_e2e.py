import time
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
import yaml

from cumulusci.core.datasets import Dataset
from cumulusci.core.exceptions import BulkDataException
from cumulusci.salesforce_api.org_schema import Filters
from cumulusci.tasks.bulkdata.extract_dataset_utils.tests.test_synthesize_extract_declarations import (
    _fake_get_org_schema,
    describe_for,
)
from cumulusci.tasks.bulkdata.tests.integration_test_utils import (
    ensure_accounts,
    ensure_records,
)

ensure_accounts = ensure_accounts
ensure_records = ensure_records


@contextmanager
def setup_test(org_config):
    object_counts = {"Account": 6, "Contact": 1, "Opportunity": 5}
    obj_describes = (
        describe_for("Account"),
        describe_for("Contact"),
        describe_for("Opportunity"),
    )
    with patch.object(type(org_config), "is_person_accounts_enabled", False), patch(
        "cumulusci.core.datasets.get_org_schema",
        lambda _sf, org_config, **kwargs: _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            included_objects=["Account", "Contact", "Opportunity"],
            **kwargs,
        ),
    ):
        yield


class Timer:
    def __init__(self):
        self.old_time = time.time()

    def checkpoint(self, name):
        cur = time.time()
        print(name, cur - self.old_time)
        self.old_time = time.time()


@pytest.mark.vcr()
class TestDatasetsE2E:
    def test_datasets_e2e(
        self,
        sf,
        project_config,
        org_config,
        delete_data_from_org,
        ensure_accounts,
        run_code_without_recording,
    ):
        timer = Timer()
        timer.checkpoint("Started")
        object_counts = {"Account": 6, "Contact": 1, "Opportunity": 5}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Opportunity"),
        )

        with patch.object(
            type(org_config), "is_person_accounts_enabled", False
        ), _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            include_counts=True,
            filters=[Filters.extractable, Filters.createable],
            included_objects=["Account", "Contact", "Opportunity"],
        ) as schema, ensure_accounts(
            6
        ), Dataset(
            "foo", project_config, sf, org_config, schema=schema
        ) as dataset:
            timer.checkpoint("In Dataset")
            if dataset.path.exists():
                rmtree(dataset.path)

            self.demo_dataset(
                dataset, timer, sf, delete_data_from_org, run_code_without_recording
            )

            if dataset.path.exists():
                rmtree(dataset.path)

    def demo_dataset(
        self, dataset, timer, sf, delete_data_from_org, run_code_without_recording
    ):
        def count(sobject):
            return sf.query(f"select count(Id) from {sobject}")["records"][0]["expr0"]

        assert count("Account") == 6
        timer.checkpoint("Before create")
        # Create a dataset directory and associated files
        dataset.create()
        timer.checkpoint("After create")

        # Read selected schema objects and fields into a T.Dict[str, T.List[str]]
        # Datastructure like {"Account": ["Name", "Description"]}
        objs = dataset.read_schema_subset()
        timer.checkpoint("Read Subset")

        # Save a similar datastructure back to the file system
        objs = {"Account": objs["Account"]}
        objs["Account"].remove("Description")
        objs["Account"].remove("History__c")
        objs["Account"].remove("ns__Description__c")
        objs["Account"].remove("Primary_Contact__c")
        dataset.update_schema_subset(objs)
        timer.checkpoint("Updated Subset")

        # Read full schema in a Datastructure like {"Account": {"Name": True, "Description": False}}
        objs = dataset.read_which_fields_selected()
        assert objs["Account"]["Name"] is True
        assert objs["Account"]["Description"] is False
        timer.checkpoint("Read selected")

        # Run an extract to the filesystem
        with patch("cumulusci.tasks.bulkdata.extract.validate_and_inject_mapping"):
            dataset.extract()
        timer.checkpoint("Extract")

        run_code_without_recording(
            lambda: delete_data_from_org(
                [
                    "Account",
                    "Contact",
                ]
            )
        )
        timer.checkpoint("Deleted")

        assert count("Account") == 0
        dataset.load()
        timer.checkpoint("Loaded")

        assert count("Account") == 6
        timer.checkpoint("Verified")

    def test_datasets_extract_standard_objects(
        self, sf, project_config, org_config, delete_data_from_org, ensure_accounts
    ):
        timer = Timer()
        timer.checkpoint("Started")
        object_counts = {"Account": 6, "Contact": 1, "Opportunity": 5}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Opportunity"),
        )
        with patch.object(type(org_config), "is_person_accounts_enabled", False), patch(
            "cumulusci.core.datasets.get_org_schema",
            lambda _sf, org_config, **kwargs: _fake_get_org_schema(
                org_config,
                obj_describes,
                object_counts,
                included_objects=["Account", "Contact", "Opportunity"],
                **kwargs,
            ),
        ), ensure_accounts(6), Dataset(
            "bar", project_config, sf, org_config
        ) as dataset:
            timer.checkpoint("In Dataset")
            if dataset.path.exists():
                rmtree(dataset.path)

            dataset.create()
            timer.checkpoint("After create")

            # Read selected schema objects and fields into a T.Dict[str, T.List[str]]
            # Datastructure like {"Account": ["Name", "Description"]}
            objs = dataset.read_schema_subset()
            timer.checkpoint("Read Subset")

            # Save a similar datastructure back to the file system
            objs = {
                objname: [f for f in fields if "__" not in f]
                for objname, fields in objs.items()
                if objname not in ["EdgeMartDataFile"] and "__" not in objname
            }
            dataset.update_schema_subset(objs)
            timer.checkpoint("Updated Subset")

            # Run an extract to the filesystem
            dataset.extract()
            timer.checkpoint("Extract")

            if dataset.path.exists():
                rmtree(dataset.path)

    def test_datasets_read_explicit_extract_declaration(
        self, sf, project_config, org_config, delete_data_from_org, ensure_accounts
    ):
        object_counts = {"Account": 6, "Contact": 1, "Opportunity": 5}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Opportunity"),
        )
        with patch.object(type(org_config), "is_person_accounts_enabled", False), patch(
            "cumulusci.core.datasets.get_org_schema",
            lambda _sf, org_config, **kwargs: _fake_get_org_schema(
                org_config,
                obj_describes,
                object_counts,
                included_objects=["Account", "Contact", "Opportunity"],
                **kwargs,
            ),
        ), ensure_accounts(6), Dataset(
            "bar", project_config, sf, org_config
        ) as dataset:
            if dataset.path.exists():
                rmtree(dataset.path)

            dataset.create()
            with TemporaryDirectory() as t:
                def_file = Path(t) / "test_extract_definition"
                with open(def_file, "w") as f:
                    yaml.safe_dump({"extract": {"Account": {"fields": "Name"}}}, f)

                # Don't actually extract data.
                with patch("cumulusci.tasks.bulkdata.ExtractData._run_task"):
                    dataset.extract(extraction_definition=def_file)
            with open(dataset.mapping_file) as p:
                actual = yaml.safe_load(p)
                expected = {
                    "Insert Account": {
                        "sf_object": "Account",
                        "table": "Account",
                        "fields": ["Name"],
                    }
                }
                assert actual == expected, actual

            if dataset.path.exists():
                rmtree(dataset.path)


class TestLoadDatasets:
    def test_dataset_with_snowfakery(self, sf, project_config, org_config):
        def fake_path_exists(self):
            return str(self).endswith("recipe.yml")

        called = False

        def fake_run_snowfakery(self):
            nonlocal called
            assert "foo.recipe.yml" in self.options["recipe"]
            called = True

        with setup_test(org_config), Dataset(
            "foo", project_config, sf, org_config, schema=None
        ) as dataset, patch(
            "cumulusci.core.datasets.Path.exists", fake_path_exists
        ), patch(
            "cumulusci.tasks.bulkdata.snowfakery.Snowfakery._run_task",
            fake_run_snowfakery,
        ):
            dataset.load()
        assert called

    def test_dataset_with_no_data_or_recipe(self, sf, project_config, org_config):

        with setup_test(org_config), Dataset(
            "fxoyoxz", project_config, sf, org_config, schema=None
        ) as dataset, pytest.raises(BulkDataException, match="fxoyoxz"):
            dataset.load()
