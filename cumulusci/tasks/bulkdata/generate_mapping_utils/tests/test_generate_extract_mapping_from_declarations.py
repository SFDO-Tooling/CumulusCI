from cumulusci.tasks.bulkdata.extract_dataset_utils.extract_yml import (
    ExtractDeclaration,
)
from cumulusci.tasks.bulkdata.extract_dataset_utils.tests.test_synthesize_extract_declarations import (
    _fake_get_org_schema,
    describe_for,
)
from cumulusci.tasks.bulkdata.generate_mapping_utils.extract_mapping_file_generator import (
    create_extract_mapping_file_from_declarations,
)


class TestGenerateLoadMappingFromDeclarations:
    def test_simple_generate_mapping_from_declarations(self, org_config):
        declarations = [
            ExtractDeclaration(sf_object="Account", fields=["Name", "Description"])
        ]
        object_counts = {"Account": 10, "Contact": 0, "Case": 5}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Case"),
        )
        with _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            filters=[],
            include_counts=True,
        ) as schema:
            mf = create_extract_mapping_file_from_declarations(declarations, schema, ())
            assert mf == {
                "Extract Account": {
                    "api": "smart",
                    "sf_object": "Account",
                    "fields": ["Name", "Description"],
                    "soql_filter": "Name != 'Sample Account for " "Entitlements'",
                }
            }

    def test_generate_mapping_from_declarations__lookups(self, org_config):
        declarations = [
            ExtractDeclaration(sf_object="Account", fields=["Name", "Description"]),
            ExtractDeclaration(sf_object="Contact", fields=["LastName", "AccountId"]),
        ]
        object_counts = {"Account": 10, "Contact": 5, "Case": 5}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Case"),
        )
        with _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            filters=[],
            include_counts=True,
        ) as schema:
            mf = create_extract_mapping_file_from_declarations(declarations, schema, ())
            print(mf)
            assert mf == {
                "Extract Account": {
                    "api": "smart",
                    "sf_object": "Account",
                    "soql_filter": "Name != 'Sample Account for Entitlements'",
                    "fields": ["Name", "Description"],
                },
                "Extract Contact": {
                    "api": "smart",
                    "sf_object": "Contact",
                    "fields": ["LastName"],
                    "lookups": {"AccountId": {"table": ("Account",)}},
                },
            }

    def test_generate_mapping_from_declarations__polymorphic_lookups(self, org_config):
        """Generate correct mapping file for sobjects with polymorphic lookup fields"""
        declarations = [
            ExtractDeclaration(sf_object="Account", fields=["Name", "Description"]),
            ExtractDeclaration(sf_object="Contact", fields=["LastName", "AccountId"]),
            ExtractDeclaration(sf_object="Event", fields=["Subject", "WhoId"]),
            ExtractDeclaration(sf_object="Lead", fields=["LastName", "Company"]),
        ]
        object_counts = {"Account": 10, "Contact": 5, "Case": 5, "Event": 1, "Lead": 2}
        obj_describes = (
            describe_for("Account"),
            describe_for("Contact"),
            describe_for("Case"),
            describe_for("Lead"),
            describe_for("Event"),
        )
        with _fake_get_org_schema(
            org_config,
            obj_describes,
            object_counts,
            filters=[],
            include_counts=True,
        ) as schema:
            mf = create_extract_mapping_file_from_declarations(declarations, schema, ())
            print(mf)
            assert mf == {
                "Extract Account": {
                    "api": "smart",
                    "sf_object": "Account",
                    "soql_filter": "Name != 'Sample Account for Entitlements'",
                    "fields": ["Name", "Description"],
                },
                "Extract Contact": {
                    "api": "smart",
                    "sf_object": "Contact",
                    "fields": ["LastName"],
                    "lookups": {"AccountId": {"table": ("Account",)}},
                },
                "Extract Lead": {
                    "api": "smart",
                    "sf_object": "Lead",
                    "fields": ["LastName", "Company"],
                },
                "Extract Event": {
                    "api": "smart",
                    "sf_object": "Event",
                    "fields": ["Subject"],
                    "lookups": {
                        "WhoId": {
                            "table": (
                                "Contact",
                                "Lead",
                            )
                        }
                    },
                },
            }


# TODO: Figure out where clauses
