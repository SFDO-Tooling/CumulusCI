import random

from cumulusci.tasks.bulkdata.extract_dataset_utils.calculate_dependencies import (
    SObjDependency,
)
from cumulusci.tasks.bulkdata.generate_mapping_utils.dependency_map import DependencyMap
from cumulusci.tasks.bulkdata.generate_mapping_utils.mapping_transforms import (
    merge_matching_steps,
    recategorize_lookups,
    rename_record_type_fields,
    sort_steps,
)
from cumulusci.tasks.bulkdata.mapping_parser import MappingStep


class MappingTransformTesterBase:
    @classmethod
    def setup_class(_):
        mttb = MappingTransformTesterBase
        mttb.std_intertable_dependencies = [
            SObjDependency("Contact", "Account", "AccountId"),
            SObjDependency("Account", "Account", "ParentId"),
            SObjDependency("Opportunity", "Contact", "ContactId"),
            SObjDependency("Opportunity", "Account", "AccountId"),
            SObjDependency("Account", "Custom__c", "Custom__c"),
            SObjDependency("Custom__c", "Opportunity", "Opportunity__c"),
            SObjDependency("Custom_2__c", "Custom__c", "Custom__c"),
            SObjDependency("Custom_2__c", "Custom_3__c", "Custom_3__c"),
            SObjDependency("Custom_3__c", "Custom_2__c", "Custom_2__c"),
        ]
        mttb.std_table_names = [
            dep.table_name_from for dep in mttb.std_intertable_dependencies
        ] + ["Unrelated__c"]

        mttb.std_dep_map = DependencyMap(
            mttb.std_table_names, mttb.std_intertable_dependencies
        )


class TestSortSteps(MappingTransformTesterBase):
    def test_sort_steps(self):
        steps = [
            MappingStep(sf_object="Opportunity"),
            MappingStep(sf_object="Custom__c"),
            MappingStep(sf_object="Custom_2__c"),
            MappingStep(sf_object="Custom_3__c"),
            MappingStep(sf_object="Contact"),
            MappingStep(sf_object="Account"),
        ]

        for i in range(0, 10):
            random.Random(i).shuffle(steps)
            out_steps = sort_steps(steps, self.std_dep_map)
            enumerated = enumerate(step.sf_object for step in out_steps)
            positions = {name: pos for (pos, name) in enumerated}
            assert positions["Account"] < positions["Contact"], positions
            assert positions["Account"] < positions["Opportunity"], positions
            assert positions["Contact"] < positions["Opportunity"], positions
            assert positions["Opportunity"] < positions["Custom__c"], positions
            assert positions["Opportunity"] < positions["Custom__c"], positions
            assert positions["Custom__c"] < positions["Custom_2__c"], positions
            assert positions["Custom__c"] < positions["Custom_3__c"], positions

    def test_sort_steps__with_priorities(self):
        steps = [
            MappingStep(sf_object="Opportunity"),
            MappingStep(sf_object="Custom__c"),
            MappingStep(sf_object="Custom_2__c"),
            MappingStep(sf_object="Custom_3__c"),
            MappingStep(sf_object="Contact"),
            MappingStep(sf_object="Account"),
        ]

        for i in range(0, 10):
            random.Random(i).shuffle(steps)
            # add a high priority requirement that forces Custom_3__c to go before Account
            deps = DependencyMap(
                self.std_table_names,
                self.std_intertable_dependencies
                + [SObjDependency("Account", "Custom_3__c", "Custom_3__c", True)],
            )
            out_steps = sort_steps(steps, deps)
            enumerated = enumerate(step.sf_object for step in out_steps)
            positions = {name: pos for (pos, name) in enumerated}
            assert positions["Custom_3__c"] < positions["Account"], positions
            assert positions["Opportunity"] < positions["Custom__c"], positions
            assert positions["Opportunity"] < positions["Custom__c"], positions
            assert positions["Custom__c"] < positions["Custom_2__c"], positions
            assert positions["Custom__c"] < positions["Custom_3__c"], positions

    def test_sort_steps__with_priorities__2(self):
        steps = [
            MappingStep(sf_object="Opportunity"),
            MappingStep(sf_object="Custom__c"),
            MappingStep(sf_object="Custom_2__c"),
            MappingStep(sf_object="Custom_3__c"),
            MappingStep(sf_object="Contact"),
            MappingStep(sf_object="Account"),
        ]

        for i in range(0, 10):
            random.Random(i).shuffle(steps)
            # add a high priority requirement that forces Custom_2__c to go before Custom_3__c
            deps = DependencyMap(
                self.std_table_names,
                self.std_intertable_dependencies
                + [SObjDependency("Custom_3__c", "Custom_2__c", "Custom_2__c", True)],
            )
            out_steps = sort_steps(steps, deps)
            enumerated = enumerate(step.sf_object for step in out_steps)
            positions = {name: pos for (pos, name) in enumerated}
            assert positions["Custom_2__c"] < positions["Custom_3__c"], positions


class TestMergeMatchingSteps(MappingTransformTesterBase):
    def test_merge_matching_steps(self):
        steps = [
            MappingStep(sf_object="Account", fields={"recordtypeid": "recordtypeid"}),
            MappingStep(sf_object="Account", fields={"Name": "Name"}),
            MappingStep(sf_object="Contact", fields={"recordtype": "recordtype"}),
            MappingStep(sf_object="Contact", fields={"description": "description"}),
        ]
        out_steps = merge_matching_steps(steps, self.std_dep_map)
        by_name = {step.sf_object: step for step in out_steps}
        assert tuple(step.sf_object for step in out_steps) == ("Account", "Contact")
        assert tuple(by_name["Account"].fields) == ("recordtypeid", "Name")
        assert tuple(by_name["Contact"].fields) == ("recordtype", "description")


class TestRenameRecordTypeFields(MappingTransformTesterBase):
    def test_rename_record_type_fields(self):
        steps = [
            MappingStep(
                sf_object="Account", fields={"record_type_id": "record_type_id"}
            ),
            MappingStep(sf_object="Custom__c", fields={"recordtypeid": "recordtypeid"}),
            MappingStep(sf_object="Custom_2__c", fields={"recordtype": "recordtype"}),
            MappingStep(sf_object="Custom_3__c"),
        ]
        out_steps = rename_record_type_fields(steps, self.std_dep_map)

        by_name = {step.sf_object: step for step in out_steps}
        assert tuple(by_name.keys()) == (
            "Account",
            "Custom__c",
            "Custom_2__c",
            "Custom_3__c",
        )

        assert "RecordTypeId" in by_name["Account"].fields
        assert "RecordTypeId" in by_name["Custom__c"].fields
        assert "RecordTypeId" in by_name["Custom_2__c"].fields
        assert "RecordTypeId" not in by_name["Custom_3__c"].fields


class TestRecategorizeLookups(MappingTransformTesterBase):
    def test_recategorize_lookups(self):
        steps = [
            MappingStep(
                sf_object="Account",
                fields={
                    "ParentId": "ParentId",
                    "Name": "Name",
                    "Custom__c": "Custom__c",
                },
            ),
            MappingStep(
                sf_object="Contact",
                fields={"AccountId": "AccountId", "Firstname": "Firstname"},
            ),
            MappingStep(
                sf_object="Custom_2__c",
                fields={"Custom__c": "Custom__c", "Name": "Name"},
            ),
            MappingStep(
                sf_object="Custom_3__c",
                fields={"Name": "Name"},
            ),
        ]
        out_steps = recategorize_lookups(steps, self.std_dep_map)

        by_name = {step.sf_object: step for step in out_steps}
        assert tuple(by_name["Account"].fields) == ("Name",)
        assert tuple(by_name["Account"].lookups) == ("ParentId", "Custom__c")
        assert tuple(by_name["Contact"].fields) == ("Firstname",)
        assert tuple(by_name["Contact"].lookups) == ("AccountId",)
        assert tuple(by_name["Custom_2__c"].fields) == ("Name",)
        assert tuple(by_name["Custom_2__c"].lookups) == ("Custom__c",)
