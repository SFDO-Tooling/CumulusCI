from datetime import datetime
from unittest import mock

from lxml import etree
import pytest

from cumulusci.core.exceptions import TaskOptionsError, CumulusCIException
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.metadata_etl import MD
from cumulusci.tasks.metadata_etl import SetOrgWideDefaults

CUSTOMOBJECT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingModel>Read</sharingModel>
    <externalSharingModel>Read</externalSharingModel>
    <label>Test</label>
    <pluralLabel>Tests</pluralLabel>
    <nameField>
        <label>Test Name</label>
        <trackHistory>false</trackHistory>
        <type>Text</type>
    </nameField>
    <deploymentStatus>Deployed</deploymentStatus>
</CustomObject>"""

CUSTOMOBJECT_XML_MISSING_TAGS = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Test</label>
    <pluralLabel>Tests</pluralLabel>
    <nameField>
        <label>Test Name</label>
        <trackHistory>false</trackHistory>
        <type>Text</type>
    </nameField>
    <deploymentStatus>Deployed</deploymentStatus>
</CustomObject>"""


class TestSetOrgWideDefaults:
    def test_sets_owd(self):
        task = create_task(
            SetOrgWideDefaults,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "org_wide_defaults": [
                    {
                        "api_name": "Account",
                        "internal_sharing_model": "Private",
                        "external_sharing_model": "Private",
                    },
                    {
                        "api_name": "Test__c",
                        "internal_sharing_model": "ReadWrite",
                        "external_sharing_model": "Read",
                    },
                ],
            },
        )

        assert task.api_names == set(["Account", "Test__c"])

        tree = etree.fromstring(CUSTOMOBJECT_XML).getroottree()

        result = task._transform_entity(tree, "Test__c")

        entry = result.findall(f".//{MD}sharingModel")
        assert len(entry) == 1
        assert entry[0].text == "ReadWrite"

        entry = result.findall(f".//{MD}externalSharingModel")
        assert len(entry) == 1
        assert entry[0].text == "Read"

    def test_sets_owd__missing_tags(self):
        task = create_task(
            SetOrgWideDefaults,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "org_wide_defaults": [
                    {
                        "api_name": "Account",
                        "internal_sharing_model": "Private",
                        "external_sharing_model": "Private",
                    },
                    {
                        "api_name": "Test__c",
                        "internal_sharing_model": "ReadWrite",
                        "external_sharing_model": "Read",
                    },
                ],
            },
        )

        assert task.api_names == set(["Account", "Test__c"])

        tree = etree.fromstring(CUSTOMOBJECT_XML_MISSING_TAGS).getroottree()

        result = task._transform_entity(tree, "Test__c")

        entry = result.findall(f".//{MD}sharingModel")
        assert len(entry) == 1
        assert entry[0].text == "ReadWrite"

        entry = result.findall(f".//{MD}externalSharingModel")
        assert len(entry) == 1
        assert entry[0].text == "Read"

    def test_post_deploy_waits_for_enablement(self):
        task = create_task(
            SetOrgWideDefaults,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "org_wide_defaults": [
                    {
                        "api_name": "Account",
                        "internal_sharing_model": "Private",
                        "external_sharing_model": "Private",
                    },
                    {
                        "api_name": "Test__c",
                        "internal_sharing_model": "ReadWrite",
                        "external_sharing_model": "Read",
                    },
                ],
            },
        )
        task.sf = mock.Mock()
        task.sf.query.side_effect = [
            {
                "totalSize": 1,
                "records": [
                    {"ExternalSharingModel": "Read", "InternalSharingModel": "Read"}
                ],
            },
            {
                "totalSize": 1,
                "records": [
                    {
                        "ExternalSharingModel": "Private",
                        "InternalSharingModel": "Private",
                    }
                ],
            },
            {
                "totalSize": 1,
                "records": [
                    {
                        "ExternalSharingModel": "Read",
                        "InternalSharingModel": "ReadWrite",
                    }
                ],
            },
        ]
        task._post_deploy("Success")

        query = (
            "SELECT ExternalSharingModel, InternalSharingModel "
            "FROM EntityDefinition "
            "WHERE QualifiedApiName = '{}'"
        )

        task.sf.query.assert_has_calls(
            [
                mock.call(query.format("Account")),
                mock.call(query.format("Account")),
                mock.call(query.format("Test__c")),
            ]
        )

        assert task.poll_complete

    def test_post_deploy_exception_not_found(self):
        task = create_task(
            SetOrgWideDefaults,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "org_wide_defaults": [
                    {
                        "api_name": "Account",
                        "internal_sharing_model": "Private",
                        "external_sharing_model": "Private",
                    }
                ],
            },
        )
        task.sf = mock.Mock()
        task.sf.query.return_value = {"totalSize": 0, "records": []}
        with pytest.raises(CumulusCIException):
            task._post_deploy("Success")

        query = (
            "SELECT ExternalSharingModel, InternalSharingModel "
            "FROM EntityDefinition "
            "WHERE QualifiedApiName = '{}'"
        )

        task.sf.query.assert_has_calls([mock.call(query.format("Account"))])

    def test_raises_exception_timeout(self):
        task = create_task(
            SetOrgWideDefaults,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "org_wide_defaults": [
                    {
                        "api_name": "Account",
                        "internal_sharing_model": "Private",
                        "external_sharing_model": "Private",
                    }
                ],
            },
        )

        task.time_start = datetime.min
        with pytest.raises(CumulusCIException):
            task._poll_action()

    def test_raises_exception_missing_values(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                SetOrgWideDefaults,
                {
                    "managed": True,
                    "api_version": "47.0",
                    "api_names": "bar,foo",
                    "org_wide_defaults": [
                        {
                            "api_name": "Account",
                            "internal_sharing_model": "Private",
                            "external_sharing_model": "Private",
                        },
                        {"api_name": "Test__c"},
                    ],
                },
            )

    def test_raises_exception_bad_sharing_model(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                SetOrgWideDefaults,
                {
                    "managed": True,
                    "api_version": "47.0",
                    "api_names": "bar,foo",
                    "org_wide_defaults": [
                        {
                            "api_name": "Account",
                            "internal_sharing_model": "Nonsense",
                            "external_sharing_model": "Private",
                        },
                        {"api_name": "Test__c"},
                    ],
                },
            )
