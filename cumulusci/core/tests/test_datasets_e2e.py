from shutil import rmtree

import pytest

from cumulusci.core.datasets import Dataset
from cumulusci.salesforce_api.org_schema import Filters, get_org_schema


@pytest.mark.needs_org()
class TestDatasetsE2E:
    def test_datasets_e2e(self, sf, project_config, org_config):
        sf.Account.create({"Name": "AAA", "Description": "BBBBB"})
        with Dataset("foo", project_config, org_config, sf) as dataset:
            if dataset.path.exists():
                rmtree(dataset.path)

            self.demo_dataset(dataset)

    def demo_dataset(self, dataset):
        # Create a dataset directory and associated files
        dataset.create()

        # Read schema objects and fields into a T.Dict[str, T.List[str]]
        # Datastructure like {"Account": ["Name", "Description"]}
        objs = dataset.read_schema_subset()
        for objname, fields in objs.items():
            for field in fields:
                print(objname, field)

        # Save a similar datastructure back to the file system
        objs["Account"].remove("Description")
        dataset.update_schema_subset(objs)

        # Run an extract to the filesystem
        dataset.extract()

        # Run a load (will probably fail for duplicate values etc.)
        # dataset.load()

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
                        print(obj.name, fieldname)
