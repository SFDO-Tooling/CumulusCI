from snowfakery.cci_mapping_files.declaration_parser import SObjectRuleDeclaration

from cumulusci.tasks.bulkdata.extract_dataset_utils.extract_yml import (
    ExtractDeclaration,
)
from cumulusci.tasks.bulkdata.extract_dataset_utils.tests.test_synthesize_extract_declarations import (
    _fake_get_org_schema,
    describe_for,
)
from cumulusci.tasks.bulkdata.generate_mapping_utils.generate_mapping_from_declarations import (
    create_load_mapping_file_from_extract_declarations,
    generate_load_mapping_file,
)
from cumulusci.tasks.bulkdata.mapping_parser import MappingStep
from cumulusci.tasks.bulkdata.step import DataApi, DataOperationType


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
            mf = create_load_mapping_file_from_extract_declarations(
                declarations, schema
            )
            assert mf == {
                "Insert Account": {
                    "sf_object": "Account",
                    "table": "Account",
                    "fields": ["Name", "Description"],
                }
            }

    def test_generate_load_mapping_from_declarations__lookups(self, org_config):
        declarations = [
            ExtractDeclaration(sf_object="Account", fields=["Name", "Description"]),
            ExtractDeclaration(
                sf_object="Contact", fields=["FirstName", "LastName", "AccountId"]
            ),
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
            mf = create_load_mapping_file_from_extract_declarations(
                declarations, schema
            )
            assert mf == {
                "Insert Account": {
                    "sf_object": "Account",
                    "table": "Account",
                    "fields": ["Name", "Description"],
                },
                "Insert Contact": {
                    "sf_object": "Contact",
                    "table": "Contact",
                    "fields": ["FirstName", "LastName"],
                    "lookups": {
                        "AccountId": {"table": "Account", "key_field": "AccountId"}
                    },
                },
            }

    def test_generate_load_mapping_from_declarations__circular_lookups(
        self, org_config
    ):
        declarations = [
            ExtractDeclaration(
                sf_object="Account",
                fields=["Name", "Description", "Primary_Contact__c"],
            ),
            ExtractDeclaration(
                sf_object="Contact", fields=["FirstName", "LastName", "AccountId"]
            ),
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
            mf = create_load_mapping_file_from_extract_declarations(
                declarations, schema
            )
            assert mf == {
                "Insert Account": {
                    "fields": ["Name", "Description"],
                    "lookups": {
                        "Primary_Contact__c": {
                            "after": "Insert Contact",
                            "key_field": "Primary_Contact__c",
                            "table": "Contact",
                        }
                    },
                    "sf_object": "Account",
                    "table": "Account",
                },
                "Insert Contact": {
                    "sf_object": "Contact",
                    "table": "Contact",
                    "fields": ["FirstName", "LastName"],
                    "lookups": {
                        "AccountId": {"table": "Account", "key_field": "AccountId"}
                    },
                },
            }, mf

    def test_generate_load_mapping__with_load_declarations(self, org_config):

        mapping_steps = [
            MappingStep(sf_object="Account"),
            MappingStep(sf_object="Contact"),
        ]
        load_declarations = [
            SObjectRuleDeclaration(sf_object="Account", api="rest"),
            SObjectRuleDeclaration(sf_object="Contact", api="bulk"),
        ]
        mf = generate_load_mapping_file(
            mapping_steps,
            intertable_dependencies=set(),
            load_declarations=load_declarations,
        )
        assert mf == {
            "Insert Account": {
                "sf_object": "Account",
                "api": DataApi.REST,
                "table": "Account",
            },
            "Insert Contact": {
                "sf_object": "Contact",
                "api": DataApi.BULK,
                "table": "Contact",
            },
        }, mf

    def test_generate_load_mapping__with_userts(self, org_config):

        mapping_steps = [
            MappingStep(sf_object="Account"),
            MappingStep(
                sf_object="Account",
                action="UPSERT",
                update_key=["Name"],
                fields=["Name"],
            ),
            MappingStep(
                sf_object="Account",
                action="ETL_UPSERT",
                update_key=["AccountNumber", "Name"],
                fields=["AccountNumber", "Name"],
            ),
            MappingStep(sf_object="Contact"),
        ]

        mf = generate_load_mapping_file(
            mapping_steps,
            intertable_dependencies=set(),
            load_declarations=None,
        )
        assert mf == {
            "Insert Account": {
                "sf_object": "Account",
                "table": "Account",
            },
            "Upsert Account Name": {
                "sf_object": "Account",
                "table": "Account",
                "action": DataOperationType.UPSERT,
                "update_key": ("Name",),
                "fields": ["Name"],
            },
            "Etl_Upsert Account AccountNumber_Name": {
                "sf_object": "Account",
                "table": "Account",
                "action": DataOperationType.ETL_UPSERT,
                "update_key": ("AccountNumber", "Name"),
                "fields": ["AccountNumber", "Name"],
            },
            "Insert Contact": {
                "sf_object": "Contact",
                "table": "Contact",
            },
        }, mf


# TODO: Figure out where clauses
