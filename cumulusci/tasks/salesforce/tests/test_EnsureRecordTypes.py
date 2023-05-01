import os
from unittest import mock

import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce import EnsureRecordTypes
from cumulusci.utils import temporary_dir

from .util import create_task

OPPORTUNITY_METADATA = """<?xml version="1.0" encoding="utf-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <businessProcesses>
        <fullName>NPSP_Default</fullName>
        <isActive>true</isActive>
        <values>
            <fullName>Test</fullName>
            <default>false</default>
        </values>
    </businessProcesses>
    <recordTypes>
        <fullName>NPSP_Default</fullName>
        <active>true</active>
        <businessProcess>NPSP_Default</businessProcess>
        <label>NPSP Default</label>
        <description></description>
    </recordTypes>
</CustomObject>
"""

CASE_METADATA = """<?xml version="1.0" encoding="utf-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <businessProcesses>
        <fullName>NPSP_Default</fullName>
        <isActive>true</isActive>
        <values>
            <fullName>Test</fullName>
            <default>true</default>
        </values>
    </businessProcesses>
    <recordTypes>
        <fullName>NPSP_Default</fullName>
        <active>true</active>
        <businessProcess>NPSP_Default</businessProcess>
        <label>NPSP Default</label>
        <description>The first 255 characters of record_type_descirption option-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------</description>
    </recordTypes>
</CustomObject>
"""

ACCOUNT_METADATA = """<?xml version="1.0" encoding="utf-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    
    <recordTypes>
        <fullName>NPSP_Default</fullName>
        <active>true</active>
        
        <label>NPSP Default</label>
        <description>Default Account Record Type created by NPSP.</description>
    </recordTypes>
</CustomObject>
"""  # noqa: W293

PACKAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>*</members>
        <name>CustomObject</name>
    </types>
    <version>45.0</version>
</Package>"""

OPPORTUNITY_DESCRIBE_NO_RTS = {
    "recordTypeInfos": [{"master": True}],
    "fields": [
        {"name": "Id"},
        {
            "name": "StageName",
            "picklistValues": [
                {"value": "Bad", "active": False},
                {"value": "Test", "active": True},
            ],
        },
    ],
}

CASE_DESCRIBE_NO_RTS = {
    "recordTypeInfos": [{"master": True}],
    "fields": [
        {"name": "Id"},
        {
            "name": "Status",
            "picklistValues": [
                {"value": "Bad", "active": False},
                {"value": "Test", "active": True},
            ],
        },
    ],
}

OPPORTUNITY_DESCRIBE_WITH_RTS = {
    "recordTypeInfos": [{"master": False}, {"master": True}],
    "fields": [
        {"name": "Id"},
        {
            "name": "StageName",
            "picklistValues": [
                {"value": "Bad", "active": False},
                {"value": "Test", "active": True},
            ],
        },
    ],
}


class TestEnsureRecordTypes:
    def test_infers_correct_business_process(self):
        task = create_task(
            EnsureRecordTypes,
            {
                "record_type_developer_name": "NPSP_Default",
                "record_type_label": "NPSP Default",
                "sobject": "Opportunity",
            },
        )
        task.sf = mock.Mock()
        task.sf.Opportunity = mock.Mock()
        task.sf.Opportunity.describe = mock.Mock(
            return_value=OPPORTUNITY_DESCRIBE_NO_RTS
        )

        task._infer_requirements()

        assert task.options["generate_business_process"]
        assert task.options["generate_record_type"]
        assert task.options["stage_name"] == "Test"

    def test_no_business_process_where_unneeded(self):
        task = create_task(
            EnsureRecordTypes,
            {
                "record_type_developer_name": "NPSP_Default",
                "record_type_label": "NPSP Default",
                "sobject": "Account",
            },
        )
        task.sf = mock.Mock()
        task.sf.Account = mock.Mock()
        task.sf.Account.describe = mock.Mock(return_value=OPPORTUNITY_DESCRIBE_NO_RTS)

        task._infer_requirements()

        assert not task.options["generate_business_process"]
        assert task.options["generate_record_type"]
        assert "stage_name" not in task.options

    def test_generates_record_type_and_business_process(self):
        # Asserts Record Type Description is optional.
        task = create_task(
            EnsureRecordTypes,
            {
                "record_type_developer_name": "NPSP_Default",
                "record_type_label": "NPSP Default",
                "sobject": "Opportunity",
            },
        )

        task.sf = mock.Mock()
        task.sf.Opportunity = mock.Mock()
        task.sf.Opportunity.describe = mock.Mock(
            return_value=OPPORTUNITY_DESCRIBE_NO_RTS
        )
        task._infer_requirements()

        with temporary_dir():
            task._build_package()
            with open(os.path.join("objects", "Opportunity.object"), "r") as f:
                opp_contents = f.read()
                assert OPPORTUNITY_METADATA == opp_contents
                assert OPPORTUNITY_METADATA == opp_contents
            with open(os.path.join("package.xml"), "r") as f:
                pkg_contents = f.read()
                assert PACKAGE_XML == pkg_contents

    def test_generates_record_type_and_business_process__case(self):
        # Asserts Record Type Description is added and truncated to 255 characters.
        task = create_task(
            EnsureRecordTypes,
            {
                "record_type_developer_name": "NPSP_Default",
                "record_type_label": "NPSP Default",
                "record_type_description": "The first 255 characters of record_type_descirption option-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Everything past here is more than 255 characters",
                "sobject": "Case",
            },
        )

        task.sf = mock.Mock()
        task.sf.Case = mock.Mock()
        task.sf.Case.describe = mock.Mock(return_value=CASE_DESCRIBE_NO_RTS)
        task._infer_requirements()

        with temporary_dir():
            task._build_package()
            with open(os.path.join("objects", "Case.object"), "r") as f:
                opp_contents = f.read()
                assert CASE_METADATA == opp_contents
            with open(os.path.join("package.xml"), "r") as f:
                pkg_contents = f.read()
                assert PACKAGE_XML == pkg_contents

    def test_generates_record_type_only(self):
        # Asserts Record Type Description is added when the Description is less than 255 characters.
        task = create_task(
            EnsureRecordTypes,
            {
                "record_type_developer_name": "NPSP_Default",
                "record_type_label": "NPSP Default",
                "record_type_description": "Default Account Record Type created by NPSP.",
                "sobject": "Account",
            },
        )

        task.sf = mock.Mock()
        task.sf.Account = mock.Mock()
        task.sf.Account.describe = mock.Mock(return_value=OPPORTUNITY_DESCRIBE_NO_RTS)
        task._infer_requirements()

        with temporary_dir():
            task._build_package()
            with open(os.path.join("objects", "Account.object"), "r") as f:
                opp_contents = f.read()
                assert ACCOUNT_METADATA == opp_contents
            with open(os.path.join("package.xml"), "r") as f:
                pkg_contents = f.read()
                assert PACKAGE_XML == pkg_contents

    def test_no_action_if_existing_record_types(self):
        task = create_task(
            EnsureRecordTypes,
            {
                "record_type_developer_name": "NPSP_Default",
                "record_type_label": "NPSP Default",
                "sobject": "Opportunity",
            },
        )
        task.sf = mock.Mock()
        task.sf.Opportunity = mock.Mock()
        task.sf.Opportunity.describe = mock.Mock(
            return_value=OPPORTUNITY_DESCRIBE_WITH_RTS
        )

        task._infer_requirements()

        assert not task.options["generate_business_process"]
        assert not task.options["generate_record_type"]

    def test_second_rt_if_force_create(self):
        # Asserts a second Record Type is added even when RTs already exist when force_create is True
        task = create_task(
            EnsureRecordTypes,
            {
                "record_type_developer_name": "NPSP_Default",
                "record_type_label": "NPSP Default",
                "record_type_description": "Default Account Record Type created by NPSP.",
                "sobject": "Account",
                "force_create": True,
            },
        )

        task.sf = mock.Mock()
        task.sf.Account = mock.Mock()
        # no impact from using opp describe; it's simply representing Record Types as present
        task.sf.Account.describe = mock.Mock(return_value=OPPORTUNITY_DESCRIBE_WITH_RTS)
        task._infer_requirements()

        with temporary_dir():
            task._build_package()
            with open(os.path.join("objects", "Account.object"), "r") as f:
                obj_contents = f.read()
                assert ACCOUNT_METADATA == obj_contents
            with open(os.path.join("package.xml"), "r") as f:
                pkg_contents = f.read()
                assert PACKAGE_XML == pkg_contents

    def test_executes_deployment(self):
        task = create_task(
            EnsureRecordTypes,
            {
                "record_type_developer_name": "NPSP_Default",
                "record_type_label": "NPSP Default",
                "sobject": "Opportunity",
            },
        )

        task.sf = mock.Mock()
        task.sf.Opportunity = mock.Mock()
        task.sf.Opportunity.describe = mock.Mock(
            return_value=OPPORTUNITY_DESCRIBE_NO_RTS
        )
        task._deploy = mock.Mock()
        task._run_task()

        task._deploy.assert_called_once()
        task._deploy.return_value.assert_called_once()

    def test_no_deployment_if_unneeded(self):
        task = create_task(
            EnsureRecordTypes,
            {
                "record_type_developer_name": "NPSP_Default",
                "record_type_label": "NPSP Default",
                "sobject": "Opportunity",
            },
        )

        task.sf = mock.Mock()
        task.sf.Opportunity = mock.Mock()
        task.sf.Opportunity.describe = mock.Mock(
            return_value=OPPORTUNITY_DESCRIBE_WITH_RTS
        )
        task._deploy = mock.Mock()
        task._run_task()

        task._deploy.assert_not_called()

    def test_init_options(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                EnsureRecordTypes,
                {
                    "record_type_developer_name": "%#$(*%(%))",
                    "record_type_label": "NPSP Default",
                    "sobject": "Opportunity",
                },
            )

        with pytest.raises(TaskOptionsError):
            create_task(
                EnsureRecordTypes,
                {
                    "record_type_developer_name": "NPSP_Default",
                    "record_type_label": "NPSP Default",
                    "sobject": "Test__c",
                },
            )
