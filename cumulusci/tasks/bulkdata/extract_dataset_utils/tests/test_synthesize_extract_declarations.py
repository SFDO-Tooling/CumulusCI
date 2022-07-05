import json
from contextlib import contextmanager
from functools import cache
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest
from sqlalchemy import create_engine

from cumulusci.core.config import OrgConfig
from cumulusci.salesforce_api.org_schema import get_org_schema
from cumulusci.tasks.bulkdata.extract_dataset_utils.extract_yml import ExtractRulesFile
from cumulusci.tasks.bulkdata.extract_dataset_utils.synthesize_extract_declarations import (
    flatten_declarations,
)
from cumulusci.tasks.bulkdata.step import DataApi
from cumulusci.tests.util import read_mock
from cumulusci.utils.tests.test_org_schema import FakeSF


class TestSynthesizeExtractDeclarations:
    def test_synthesize_extract_declarations(self, org_config):
        declarations = """
            extract:
                    OBJECTS(POPULATED):
                        fields:
                            FIELDS(ALL)
        """
        object_counts = {"Account": 10, "Contact": 0, "Case": 5}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Case"),
        )
        declarations = ExtractRulesFile.parse_extract(StringIO(declarations))
        with _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            filters=[],
            include_counts=True,
        ) as schema:
            decls = flatten_declarations(declarations.values(), schema)

            assert tuple(decl.dict() for decl in decls) == tuple(
                (
                    {
                        "where": "Name != 'Sample Account for Entitlements'",
                        "fields_": mock.ANY,
                        "api": DataApi.SMART,
                        "sf_object": "Account",
                    },
                    {
                        "where": None,
                        "fields_": mock.ANY,
                        "api": DataApi.SMART,
                        "sf_object": "Case",
                    },
                )
            )

    def test_synthesize_extract_declarations__custom(self, org_config):
        declarations = """
            extract:
                    OBJECTS(CUSTOM):
                        fields:
                            FIELDS(ALL)
        """
        object_counts = {"Account": 0, "Contact": 2, "Custom__c": 5}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Custom__c"),
        )
        declarations = ExtractRulesFile.parse_extract(StringIO(declarations))
        with _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            include_counts=True,
        ) as schema:
            decls = flatten_declarations(declarations.values(), schema)

            assert tuple(decl.dict() for decl in decls) == tuple(
                (
                    {
                        "where": None,
                        "fields_": mock.ANY,
                        "api": DataApi.SMART,
                        "sf_object": "Custom__c",
                    },
                )
            )

    @pytest.mark.skip("FIXME")
    def test_required_lookups__not_fulfilled(
        self, cumulusci_test_repo_root, org_config
    ):
        ...

    def test_parse_real_file(self, cumulusci_test_repo_root, org_config):
        declarations = ExtractRulesFile.parse_extract(
            cumulusci_test_repo_root / "datasets/test.extract.yml"
        )
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Opportunity"),
            describe_for("Custom__c"),
        )
        object_counts = {
            "Account": 100,
            "Opportunity": 10,
            "Custom__c": 5,
            "Contact": 0,
        }
        with _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            include_counts=True,
        ) as schema:
            decls = flatten_declarations(declarations.values(), schema)
            decls = {decl.sf_object: decl for decl in decls}
            assert decls["Opportunity"].fields == [
                "Name",
                "ContactId",
                "AccountId",
                "CloseDate",  # pull these in because they required
                "IsPrivate",
                "OwnerId",  # ??? maybe should not include this?
                "StageName",
            ]
            assert "Account" in decls
            assert "Contact" in decls  # pulled in because of ContactId
            assert "Custom__c" in decls
            print(schema["Custom__c"].fields.keys())
            assert set(decls["Custom__c"].fields) == set(
                schema["Custom__c"].fields.keys()
            ) - set(["Id"])


@cache
def describe_for(sobject: str):
    return json.loads(read_mock(sobject))


@contextmanager
def _fake_get_org_schema(
    org_config: OrgConfig,
    org_describes: list[dict],
    object_counts: dict[str, int],
    **kwargs,
):
    with mock.patch(
        "cumulusci.salesforce_api.org_schema.count_sobjects",
        lambda *args: (
            object_counts,
            [],
            [],
        ),
    ), mock.patch(
        "cumulusci.salesforce_api.org_schema.ZippableTempDb", FakeZippableTempDb
    ), mock.patch(
        "cumulusci.salesforce_api.org_schema.deep_describe",
        return_value=((desc, "Sat, 1 Jan 2000 00:00:01 GMT") for desc in org_describes),
    ), get_org_schema(
        FakeSF(), org_config, **kwargs
    ) as schema:
        yield schema


class FakeZippableTempDb:
    "Fast no-IO database for testing"

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        return ""

    def zip_database(self, target_path: Path):
        pass

    def unzip_database(self, zipped_db: Path):
        pass

    def clear(self):
        pass

    def create_engine(self):
        self.engine = create_engine("sqlite:///")
        return self.engine


@contextmanager
def faketempdb():
    yield Path("")
