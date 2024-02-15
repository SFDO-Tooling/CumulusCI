import json
import typing as T
from contextlib import contextmanager
from functools import lru_cache
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest
from sqlalchemy import create_engine

from cumulusci.core.config import OrgConfig
from cumulusci.salesforce_api.org_schema import Filters, get_org_schema
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
                    OBJECTS(ALL):
                        fields:
                            FIELDS(REQUIRED)
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
            decls = flatten_declarations(declarations.values(), schema, ())

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

    def test_find_custom_objects(self, org_config):
        declarations = """
            extract:
                    OBJECTS(CUSTOM):
                        fields:
                            FIELDS(ALL)
        """
        object_counts = {"Account": 10, "Contact": 0, "Case": 5, "Custom__c": 10}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Case"),
            describe_for("Custom__c"),
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
                        "where": None,
                        "fields_": mock.ANY,
                        "api": DataApi.SMART,
                        "sf_object": "Custom__c",
                    },
                )
            )

    def test_find_standard_objects(self, org_config):
        declarations = """
            extract:
                    OBJECTS(STANDARD):
                        fields:
                            FIELDS(REQUIRED)
        """
        object_counts = {"Account": 10, "Contact": 0, "Case": 5, "Custom__c": 10}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Case"),
            describe_for("Custom__c"),
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

    def test_filter_objects(self, org_config):
        declarations = """
            extract:
                    OBJECTS(STANDARD):
                        fields:
                            FIELDS(REQUIRED)
        """
        object_counts = {"Account": 10, "Contact": 0, "Case": 5, "Custom__c": 10}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Case"),
            describe_for("Custom__c"),
        )
        declarations = ExtractRulesFile.parse_extract(StringIO(declarations))
        with _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            filters=[],
            include_counts=True,
        ) as schema:
            decls = flatten_declarations(declarations.values(), schema, ("Account"))

            assert tuple(decl.dict() for decl in decls) == tuple(
                (  # No Account
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

    def test_synthesize_extract_declarations__custom_fields(self, org_config):
        declarations = """
            extract:
                    OBJECTS(CUSTOM):
                        fields:
                            FIELDS(custom)
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
                        "fields_": ["CustomField__c"],
                        "api": DataApi.SMART,
                        "sf_object": "Custom__c",
                    },
                )
            )

    def test_synthesize_extract_declarations__standard_fields(self, org_config):
        declarations = """
            extract:
                    OBJECTS(CUSTOM):
                        fields:
                            FIELDS(standard)
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
                        "fields_": ["Name"],
                        "api": DataApi.SMART,
                        "sf_object": "Custom__c",
                    },
                )
            )

    def test_required_lookups__pulled_in(self, org_config):
        """Bringing in the AccountId should force Account to come in.

        Including all Account/Contact required fields."""
        declarations = """
            extract:
                Contact:
                    fields:
                        AccountId
        """
        object_counts = {"Account": 3, "Contact": 2, "Custom__c": 5}
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
                        "where": mock.ANY,
                        "fields_": ["AccountId", "LastName"],
                        "api": DataApi.SMART,
                        "sf_object": "Contact",
                    },
                    {
                        "where": mock.ANY,
                        "fields_": [
                            "Name",
                        ],
                        "api": DataApi.SMART,
                        "sf_object": "Account",
                    },
                )
            )

    def test_required_lookups__pulled_in__polymorphic_lookups(self, org_config):
        """Bringing in the WhoId for sobject Event should force Contact
        and Lead to come in.

        Including all Lead/Contact/Event required fields."""
        declarations = """
            extract:
                Event:
                    fields:
                        WhoId
        """
        object_counts = {
            "Account": 3,
            "Contact": 2,
            "Custom__c": 5,
            "Lead": 2,
            "Event": 1,
        }
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Custom__c"),
            describe_for("Event"),
            describe_for("Lead"),
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
                        "where": mock.ANY,
                        "fields_": ["WhoId"],
                        "api": DataApi.SMART,
                        "sf_object": "Event",
                    },
                    {
                        "where": mock.ANY,
                        "fields_": ["LastName"],
                        "api": DataApi.SMART,
                        "sf_object": "Contact",
                    },
                    {
                        "where": mock.ANY,
                        "fields_": ["Company", "LastName"],
                        "api": DataApi.SMART,
                        "sf_object": "Lead",
                    },
                )
            )

    def test_parse_real_file(self, cumulusci_test_repo_root, org_config):
        declarations = ExtractRulesFile.parse_extract(
            cumulusci_test_repo_root / "datasets/test_minimal.extract.yml"
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
                "StageName",
            ]
            assert "Account" in decls
            assert "Contact" in decls  # pulled in because of ContactId
            assert "Custom__c" in decls
            assert set(decls["Custom__c"].fields) == set(
                schema["Custom__c"].fields.keys()
            ) - set(["Id"])

    def test_synthesize_extract_declarations__where_clause(self, org_config):
        declarations = """
            extract:
                Contact:
                    fields:
                        FIELDS(REQUIRED)
                Account:
                    where: Name Like '%Foo%'
                    fields:
                        - Description

        """
        declarations = ExtractRulesFile.parse_extract(StringIO(declarations))
        object_counts = {"Account": 2, "Contact": 2, "Custom__c": 5}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Custom__c"),
        )
        with _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            include_counts=True,
        ) as schema:
            decls = flatten_declarations(declarations.values(), schema)
            decls = {decl.sf_object: decl for decl in decls}
            assert "Account" in decls
            assert "Contact" in decls
            assert "Custom__c" not in decls

            assert set(decls["Account"].fields) == set(["Name", "Description"])
            assert decls["Contact"].fields == ["LastName"], decls["Contact"].fields

    def test_synthesize_fields(self, sf, org_config):
        declarations = """
            extract:
                Opportunity:
                    fields:
                        - FIELDS(STANDARD)
                Account:
                    fields:
                        - FIELDS(CUSTOM)
                Contact:
                    fields:
                        - FIELDS(ALL)
                Custom__c:
                    fields:
                        - FIELDS(CUSTOM)
        """
        declarations = ExtractRulesFile.parse_extract(StringIO(declarations))
        object_counts = {"Account": 2, "Contact": 2, "Custom__c": 5}
        object_describes = [describe_for(obj) for obj in object_counts.keys()]
        with _fake_get_org_schema(
            org_config,
            object_describes,
            object_counts,
            include_counts=True,
        ) as schema:
            decls = flatten_declarations(declarations.values(), schema)
            decls = {decl.sf_object: decl for decl in decls}
            assert "Account" in decls
            assert "Contact" in decls
            assert "Entitlement" not in decls
            assert "Opportunity" not in decls  # not populated
            assert "Name" not in decls["Custom__c"].fields
            assert "Id" not in decls["Custom__c"].fields
            assert "Name" in decls["Account"].fields  # because required
            assert "BillingCountry" not in decls["Account"].fields  # not required
            assert "CustomField__c" in decls["Custom__c"].fields

    @pytest.mark.needs_org()
    @pytest.mark.slow()
    def test_find_standard_objects__integration_tests(self, sf, org_config):
        declarations = """
            extract:
                    OBJECTS(STANDARD):
                        fields:
                            FIELDS(REQUIRED)
        """
        with get_org_schema(
            sf,
            org_config,
            include_counts=True,
            filters=[Filters.createable, Filters.extractable, Filters.populated],
        ) as schema:
            declarations = ExtractRulesFile.parse_extract(StringIO(declarations))
            decls = flatten_declarations(declarations.values(), schema)
            decls = {decl.sf_object: decl for decl in decls}
            assert "WorkBadgeDefinition" in decls
            # HEY NOW!
            assert "You\\'re a RockStar!" in str(decls["WorkBadgeDefinition"].where)
            if "Opportunity" in decls:
                assert "IsPrivate" not in decls["Opportunity"].fields, decls.keys()


@lru_cache(maxsize=None)
def describe_for(sobject: str):
    return json.loads(read_mock(sobject))


@contextmanager
def _fake_get_org_schema(
    org_config: OrgConfig,
    org_describes: T.Sequence[dict],
    object_counts: T.Dict[str, int],
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

    def zip_database(self, target_path):
        pass

    def unzip_database(self, zipped_db):
        pass

    def clear(self):
        pass

    def create_engine(self):
        self.engine = create_engine("sqlite:///")
        return self.engine


@contextmanager
def faketempdb():
    yield Path("")


# TODO: Decide upon what happens in this cases:
#       OBJECTS(STANDARD)
#          fields:
#           - X
#       Account:
#          fields:
#           - Y
#    Do you get X and Y? (Union semantics?) Or just Y (override semantics)
# Consider all kinds of conflicting/complementary declarations.
