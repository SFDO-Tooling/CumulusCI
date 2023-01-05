from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from cumulusci.tasks.bulkdata.convert_dataset_to_recipe import ConvertDatasetToRecipe
from cumulusci.tasks.bulkdata.extract_dataset_utils.tests.test_synthesize_extract_declarations import (
    _fake_get_org_schema,
    describe_for,
)


@contextmanager
def setup_test(org_config):
    object_counts = {"Account": 6, "Contact": 1, "Opportunity": 5}
    obj_describes = (
        describe_for("Account"),
        describe_for("Contact"),
        describe_for("Opportunity"),
    )
    with patch.object(type(org_config), "is_person_accounts_enabled", False), patch(
        "cumulusci.tasks.bulkdata.convert_dataset_to_recipe.get_org_schema",
        lambda _sf, org_config, **kwargs: _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            included_objects=["Account", "Contact", "Opportunity"],
            **kwargs,
        ),
    ):
        yield


class TestConvertDatasetToRecipe:
    def test_convert_simple(self, org_config, create_task):
        with setup_test(org_config):
            with TemporaryDirectory() as t:
                recipe = Path(t) / "recipe.yml"
                task = create_task(
                    ConvertDatasetToRecipe,
                    {"recipe": str(recipe), "sql_path": Path("datasets/sample.sql")},
                )
                task()
                with open(recipe) as f:
                    data = yaml.safe_load(f)
                assert data == [
                    {
                        "object": "Account",
                        "nickname": "Account-Camacho PLC",
                        "fields": {
                            "Name": "Camacho PLC",
                            "Description": "Total logistical task-force",
                            "NumberOfEmployees": "59908",
                            "BillingStreet": "2852 Caleb Village Suite 428",
                            "BillingCity": "Porterside",
                            "BillingState": "Maryland",
                            "BillingPostalCode": "14525",
                            "BillingCountry": "Canada",
                            "ShippingStreet": "6070 Davidson Rapids",
                            "ShippingCity": "Gibsonland",
                            "ShippingState": "North Dakota",
                            "ShippingPostalCode": "62676",
                            "ShippingCountry": "Lithuania",
                            "Phone": "221.285.1033",
                            "Fax": "+1-081-230-6073x31438",
                            "Website": "http://jenkins.info/category/tag/tag/terms/",
                            "AccountNumber": "2679965",
                        },
                    },
                    {
                        "object": "Account",
                        "nickname": "Account-Sample Account for Entitlements",
                        "fields": {"Name": "Sample Account for Entitlements"},
                    },
                    {
                        "object": "Account",
                        "nickname": "Account-The Bluth Company",
                        "fields": {
                            "Name": "The Bluth Company",
                            "Description": "Solid as a rock",
                            "NumberOfEmployees": "6",
                        },
                    },
                    {
                        "object": "Contact",
                        "nickname": "Contact-Bluth",
                        "fields": {
                            "FirstName": "Michael",
                            "LastName": "Bluth",
                            "AccountId": {"reference": "Account-The Bluth Company"},
                        },
                    },
                    {
                        "object": "Contact",
                        "nickname": "Contact-Burnett",
                        "fields": {
                            "FirstName": "Jared",
                            "LastName": "Burnett",
                            "Salutation": "Ms.",
                            "Email": "ja-burnett2011@example.net",
                            "Phone": "372.865.5762x5990",
                            "MobilePhone": "033.134.7156x7943",
                            "Title": "Systems analyst",
                            "Birthdate": "2000-04-18",
                            "AccountId": {"reference": "Account-Camacho PLC"},
                        },
                    },
                ], data
