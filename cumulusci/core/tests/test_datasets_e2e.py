import time
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory
from typing import Any
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
        # Need record types for the RecordTypeId field to be in the org
        create_record_type_for_account(sf, run_code_without_recording)

        def count(sobject):
            return sf.query(f"select count(Id) from {sobject}")["records"][0]["expr0"]

        assert count("Account") == 6
        timer.checkpoint("Before create")
        # Create a dataset directory and associated files
        dataset.create()
        load_rules = [{"sf_object": "Account", "api": "rest"}]
        dataset.load_rules_file.write_text(yaml.safe_dump(load_rules))

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
        objs["Account"].remove("ns__LinkedAccount__c")
        objs["Account"].remove("Primary_Contact__c")
        dataset.update_schema_subset(objs)
        timer.checkpoint("Updated Subset")

        # Read full schema in a Datastructure like
        # {"Account": {"Name": True, "Description": False}}
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
        # Need record types for the RecordTypeId field to be in the org
        create_record_type_for_account(sf, run_code_without_recording)

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
        object_counts = {
            "Account": 6,
            "Contact": 1,
            "Opportunity": 5,
            "Lead": 1,
            "Event": 2,
        }
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Opportunity"),
            describe_for("Lead"),
            describe_for("Event"),
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

                def write_yaml(filename: str, json: Any):
                    full_path = Path(t) / filename
                    with open(full_path, "w") as f:
                        yaml.safe_dump(json, f)
                    return full_path

                extract_def = write_yaml(
                    "test_extract_definition",
                    {
                        "extract": {
                            "Account": {"fields": ["Name"]},
                            "Contact": {
                                "fields": ["FirstName", "LastName", "AccountId"]
                            },
                            "Event": {"fields": ["Subject", "WhoId"]},
                        }
                    },
                )
                loading_rules = write_yaml(
                    "loading_rules.load.yml",
                    [
                        {"sf_object": "Account", "load_after": "Contact"},
                        {"sf_object": "Lead", "load_after": "Event"},
                    ],
                )

                # Don't actually extract data.
                with patch("cumulusci.tasks.bulkdata.ExtractData._run_task"):
                    dataset.extract(
                        extraction_definition=extract_def,
                        loading_rules_file=loading_rules,
                    )
            with open(dataset.mapping_file) as p:
                actual = yaml.safe_load(p)
                expected = {
                    "Insert Contact": {
                        "sf_object": "Contact",
                        "table": "Contact",
                        "fields": ["FirstName", "LastName"],
                        "lookups": {
                            "AccountId": {
                                "table": ["Account"],
                                "key_field": "AccountId",
                                "after": "Insert Account",
                            }
                        },
                        "select_options": {},
                    },
                    "Insert Event": {
                        "sf_object": "Event",
                        "table": "Event",
                        "fields": ["Subject"],
                        "lookups": {
                            "WhoId": {
                                "table": ["Contact", "Lead"],
                                "key_field": "WhoId",
                                "after": "Insert Lead",
                            }
                        },
                        "select_options": {},
                    },
                    "Insert Account": {
                        "sf_object": "Account",
                        "table": "Account",
                        "fields": ["Name"],
                        "select_options": {},
                    },
                    "Insert Lead": {
                        "sf_object": "Lead",
                        "table": "Lead",
                        "fields": ["Company", "LastName"],
                        "select_options": {},
                    },
                }
                assert tuple(actual.items()) == tuple(expected.items()), actual.items()

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


# Need record types for the RecordTypeId field to be in the org
def create_record_type_for_account(sf, run_code_without_recording):
    def create_record_type_for_account_real():
        account_record_types = sf.query(
            "select Count(Id) from RecordType where SObjectType='Account'"
        )
        if account_record_types["records"][0]["expr0"] == 0:
            sf.RecordType.create(
                {
                    "DeveloperName": "PytestAccountRecordType",
                    "Name": "PytestAccountRecordType",
                    "SObjectType": "Account",
                }
            )

    run_code_without_recording(create_record_type_for_account_real)
