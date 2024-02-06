from cumulusci.tasks.bulkdata.generate_mapping_utils.mapping_generator_post_processes import (
    add_after_statements,
)
from cumulusci.tasks.bulkdata.mapping_parser import MappingLookup, MappingStep


class TestMappingGeneratorPostProcesses:
    def test_add_after_statements(self):
        "Test that the add_after_statements function will add an `after` statement to the correct mapping step"
        mappings = {
            "Insert Blah": MappingStep(sf_object="Blah"),
            "Insert Accounts": MappingStep(
                sf_object="Account",
                lookups={"PrimaryContact__c": MappingLookup(table="Contact")},
            ),
            "Update Account": MappingStep(
                sf_object="Account",
                action="Update",
            ),
            "Insert Contact": MappingStep(
                sf_object="Contact",
                lookups={"AccountId": MappingLookup(table="Account")},
            ),
        }
        add_after_statements(mappings)
        assert (
            mappings["Insert Accounts"].lookups["PrimaryContact__c"].after
            == "Insert Contact"
        )

    def test_add_after_statements__polymorphic_lookups(self):
        """Test that the add_after_statements function will add an `after` statement to the correct mapping step
        for polymorphic lookups"""
        mappings = {
            "Insert Accounts": MappingStep(
                sf_object="Account",
                lookups={"PrimaryContact__c": MappingLookup(table="Contact")},
            ),
            "Update Account": MappingStep(
                sf_object="Account",
                action="Update",
            ),
            "Insert Contact": MappingStep(
                sf_object="Contact",
                lookups={"AccountId": MappingLookup(table="Account")},
            ),
            "Insert Events": MappingStep(
                sf_object="Event",
                lookups={"WhoId": MappingLookup(table=["Lead", "Contact"])},
            ),
            "Insert Lead": MappingStep(
                sf_object="Lead",
            ),
        }
        add_after_statements(mappings)
        assert (
            mappings["Insert Accounts"].lookups["PrimaryContact__c"].after
            == "Insert Contact"
        )
        assert mappings["Insert Events"].lookups["WhoId"].after == "Insert Lead"
