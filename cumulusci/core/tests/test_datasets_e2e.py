import time
from shutil import rmtree

import pytest

from cumulusci.core.datasets import Dataset
from cumulusci.salesforce_api.org_schema import Filters, get_org_schema
from cumulusci.tasks.bulkdata.tests.integration_test_utils import ensure_accounts

ensure_accounts = ensure_accounts


class Timer:
    def __init__(self):
        self.old_time = time.time()

    def checkpoint(self, name):
        cur = time.time()
        print(name, cur - self.old_time)
        self.old_time = time.time()


@pytest.mark.needs_org()
class TestDatasetsE2E:
    def test_datasets_e2e(
        self, sf, project_config, org_config, delete_data_from_org, ensure_accounts
    ):
        timer = Timer()
        timer.checkpoint("Started")
        with ensure_accounts(6), Dataset(
            "foo", project_config, org_config, sf
        ) as dataset:
            timer.checkpoint("In Dataset")
            if dataset.path.exists():
                rmtree(dataset.path)

            self.demo_dataset(dataset, timer, sf, delete_data_from_org)

    def demo_dataset(self, dataset, timer, sf, delete_data_from_org):
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

        for objname, fields in objs.items():
            for field in fields:
                # print(objname, field)
                ...

        # Save a similar datastructure back to the file system
        objs = {"Account": objs["Account"]}
        objs["Account"].remove("Description")
        dataset.update_schema_subset(objs)
        timer.checkpoint("Updated Subset")

        # Read full schema in a Datastructure like {"Account": {"Name": True, "Description": False}}
        objs = dataset.read_which_fields_selected()
        assert objs["Account"]["Name"] is True
        assert objs["Account"]["Description"] is False
        timer.checkpoint("Read selected")

        # Run an extract to the filesystem
        dataset.extract()
        timer.checkpoint("Extract")

        delete_data_from_org(
            [
                "Account",
                "Contact",
            ]
        )
        timer.checkpoint("Deleted")

        assert count("Account") == 0
        dataset.load()
        timer.checkpoint("Loaded")

        assert count("Account") == 6
        timer.checkpoint("Verified")

    def test_org_schema(self, sf, org_config):
        with get_org_schema(
            sf,
            org_config,
            include_counts=True,
            filters=[Filters.extractable, Filters.createable],
        ) as schema:
            for obj in schema.sobjects:
                for fieldname, field in obj.fields.items():
                    if field.createable:
                        # print(obj.name, fieldname)
                        ...

    def test_datasets_extract_standard_objects(
        self, sf, project_config, org_config, delete_data_from_org, ensure_accounts
    ):
        timer = Timer()
        timer.checkpoint("Started")
        with Dataset("bar", project_config, org_config, sf) as dataset:
            timer.checkpoint("In Dataset")
            if dataset.path.exists():
                rmtree(dataset.path)

            dataset.create()
            timer.checkpoint("After create")

            # Read selected schema objects and fields into a T.Dict[str, T.List[str]]
            # Datastructure like {"Account": ["Name", "Description"]}
            objs = dataset.read_schema_subset()
            timer.checkpoint("Read Subset")

            for objname, fields in objs.items():
                for field in fields:
                    # print(objname, field)
                    ...

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
