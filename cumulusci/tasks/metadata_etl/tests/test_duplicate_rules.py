from cumulusci.tasks.metadata_etl import SetDuplicateRuleStatus
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.utils.xml import metadata_tree

DUPERULE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<DuplicateRule xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <duplicateRuleFilter xsi:nil="true"/>
    <isActive>true</isActive>
    <sortOrder>1</sortOrder>
</DuplicateRule>
"""


class TestSetDuplicateRuleStatus:
    def test_sets_status(self):
        task = create_task(
            SetDuplicateRuleStatus, {"api_version": "47.0", "active": False}
        )
        tree = metadata_tree.fromstring(DUPERULE_XML)
        assert tree.find("isActive").text == "true"
        result = task._transform_entity(tree, "DupeRule")
        assert result.find("isActive").text == "false"
