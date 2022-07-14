from cumulusci.tasks.bulkdata.extract_dataset_utils.extract_yml import (
    ExtractDeclaration,
)
from cumulusci.tasks.bulkdata.extract_dataset_utils.tests.test_synthesize_extract_declarations import (
    _fake_get_org_schema,
    describe_for,
)
from cumulusci.tasks.bulkdata.generate_mapping_utils.generate_mapping_from_declarations import (
    create_load_mapping_file_from_extract_declarations,
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
            mf = create_load_mapping_file_from_extract_declarations(
                declarations, schema
            )
            print(mf)
            assert mf == {
                "Insert Account": {
                    "sf_object": "Account",
                    "table": "Account",
                    "fields": ["Name", "Description"],
                }
            }

    def test_generate_mapping_from_declarations__lookups(self, org_config):
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
            print(mf)
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


# TODO: Figure out where clauses
