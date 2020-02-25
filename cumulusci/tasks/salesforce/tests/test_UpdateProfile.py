import os
from unittest import mock

from lxml import etree
import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl import MD
from cumulusci.tasks.salesforce import UpdateProfile
from cumulusci.utils import CUMULUSCI_PATH
from cumulusci.tests.util import create_project_config

from .util import create_task

ADMIN_PROFILE_BEFORE = """<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <applicationVisibilities>
        <application>npsp__Nonprofit_CRM</application>
        <default>true</default>
        <visible>false</visible>
    </applicationVisibilities>
    <classAccess>
        <apexClass>TestClass</apexClass>
        <enabled>false</enabled>
    </classAccess>
    <fieldPermissions>
        <field>Account.TestField__c</field>
        <editable>false</editable>
        <readable>false</readable>
    </fieldPermissions>
    <pageAccesses>
        <apexPage>TestPage</apexPage>
        <enabled>false</enabled>
    </pageAccesses>
    <recordTypeVisibilities>
        <recordType>Account.Business_Account</recordType>
        <default>true</default>
        <personAccountDefault>true</personAccountDefault>
        <visible>true</visible>
    </recordTypeVisibilities>
    <recordTypeVisibilities>
        <recordType>Account.HH_Account</recordType>
        <default>false</default>
        <personAccountDefault>false</personAccountDefault>
        <visible>false</visible>
    </recordTypeVisibilities>
    <tabVisibilities>
        <tab>NPSP_Settings</tab>
        <visibility>Hidden</visibility>
    </tabVisibilities>
</Profile>"""

ADMIN_PROFILE_EXPECTED = """<?xml version='1.0' encoding='utf-8'?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <applicationVisibilities>
        <application>npsp__Nonprofit_CRM</application>
        <default>true</default>
        <visible>true</visible>
    </applicationVisibilities>
    <classAccess>
        <apexClass>TestClass</apexClass>
        <enabled>true</enabled>
    </classAccess>
    <fieldPermissions>
        <field>Account.TestField__c</field>
        <editable>true</editable>
        <readable>true</readable>
    </fieldPermissions>
    <pageAccesses>
        <apexPage>TestPage</apexPage>
        <enabled>true</enabled>
    </pageAccesses>
    <recordTypeVisibilities>
        <recordType>Account.Business_Account</recordType>
        <default>false</default>
        <personAccountDefault>false</personAccountDefault>
        <visible>true</visible>
    </recordTypeVisibilities>
    <recordTypeVisibilities>
        <recordType>Account.HH_Account</recordType>
        <default>true</default>
        <personAccountDefault>true</personAccountDefault>
        <visible>true</visible>
    </recordTypeVisibilities>
    <tabVisibilities>
        <tab>NPSP_Settings</tab>
        <visibility>DefaultOn</visibility>
    </tabVisibilities>
</Profile>"""

PACKAGE_XML_BEFORE = """<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>*</members>
        <members>Account</members>
        <members>Campaign</members>
        <members>CampaignMember</members>
        <members>Contact</members>
        <members>Lead</members>
        <members>Opportunity</members>
        <name>CustomObject</name>
    </types>
    <types>
        <name>Profile</name>
    </types>
    <version>39.0</version>
</Package>"""


def test_transforms_profile():
    task = create_task(
        UpdateProfile,
        {
            "record_types": [
                {
                    "record_type": "Account.HH_Account",
                    "default": True,
                    "person_account_default": True,
                }
            ],
            "namespaced_org": True,
        },
    )

    result = etree.tostring(
        task._transform_entity(etree.fromstring(ADMIN_PROFILE_BEFORE), "Admin"),
        encoding="utf-8",
        xml_declaration=True,
    ).decode("utf-8")
    print(result)
    assert result == ADMIN_PROFILE_EXPECTED


def test_throws_exception_record_type_not_found():
    task = create_task(
        UpdateProfile,
        {"record_types": [{"record_type": "DOESNT_EXIST"}], "namespaced_org": True},
    )

    with pytest.raises(TaskOptionsError):
        task._transform_entity(etree.fromstring(ADMIN_PROFILE_BEFORE), "Admin")


def test_expand_package_xml():
    task = create_task(UpdateProfile, {"api_names": ["Admin"]})
    task.tooling = mock.Mock()
    task.tooling.query.return_value = {
        "totalSize": 2,
        "records": [
            {"DeveloperName": "Test", "NamespacePrefix": "ns"},
            {"DeveloperName": "Foo_Bar", "NamespacePrefix": "fb"},
        ],
    }

    package_xml = etree.fromstring(PACKAGE_XML_BEFORE)
    task._expand_package_xml(package_xml)
    types = package_xml.findall(f".//{MD}types[{MD}name='CustomObject']")[0]
    assert "ns__Test__c" in {elem.text for elem in types.findall(f".//{MD}members")}
    assert "fb__Foo_Bar__c" in {elem.text for elem in types.findall(f".//{MD}members")}


def test_expand_profile_members():
    task = create_task(
        UpdateProfile,
        {
            "api_names": ["Admin", "%%%NAMESPACE%%%Continuous Integration"],
            "namespace_inject": "ns",
            "managed": True,
        },
    )
    package_xml = etree.fromstring(PACKAGE_XML_BEFORE)

    task._expand_profile_members(package_xml)

    types = package_xml.findall(f".//{MD}types[{MD}name='Profile']")[0]
    assert {elem.text for elem in types.findall(f".//{MD}members")} == {
        "Admin",
        "ns__Continuous Integration",
    }


def test_init_options__general():
    pc = create_project_config()
    pc.project__package__namespace = "ns"
    task = create_task(UpdateProfile, {"managed": "true"}, project_config=pc)
    assert task.options["managed"]
    assert not task.options["namespaced_org"]
    assert task.options["namespace_inject"] == "ns"
    assert task.namespace_prefixes == {"managed": "ns__", "namespaced_org": ""}

    task = create_task(UpdateProfile, {"namespaced_org": "true"}, project_config=pc)
    assert task.options["managed"]
    assert task.options["namespaced_org"]
    assert task.options["namespace_inject"] == "ns"
    assert task.namespace_prefixes == {"managed": "ns__", "namespaced_org": "ns__"}

    task = create_task(UpdateProfile, {}, project_config=pc)
    assert not task.options["managed"]
    assert not task.options["namespaced_org"]
    assert task.options["namespace_inject"] == "ns"
    assert task.namespace_prefixes == {"managed": "", "namespaced_org": ""}


def test_init_options__api_names():
    task = create_task(
        UpdateProfile,
        {
            "api_names": ["Admin", "%%%NAMESPACE%%%Continuous Integration"],
            "namespace_inject": "ns",
            "managed": True,
        },
    )
    assert task.api_names == {"Admin", "ns__Continuous Integration"}

    task = create_task(
        UpdateProfile,
        {
            "api_names": ["Admin", "%%%NAMESPACE%%%Continuous Integration"],
            "namespace_inject": "ns",
            "managed": False,
        },
    )
    assert task.api_names == {"Admin", "Continuous Integration"}

    task = create_task(UpdateProfile, {"profile_name": "Continuous Integration"})
    assert task.api_names == {"Continuous Integration"}

    task = create_task(UpdateProfile, {})
    assert task.api_names == {"Admin"}

    task = create_task(UpdateProfile, {"package_xml": "lib/admin_profile.xml"})
    assert task.api_names == {"*"}


def test_init_options__include_packaged_objects():
    pc = create_project_config()
    pc.minimum_cumulusci_version = "4.0.0"
    task = create_task(
        UpdateProfile, {"package_xml": "lib/admin_profile.xml"}, project_config=pc
    )
    assert task.package_xml_path == "lib/admin_profile.xml"
    assert not task.options["include_packaged_objects"]

    task = create_task(UpdateProfile, {}, project_config=pc)
    assert task.options["include_packaged_objects"]
    assert task.package_xml_path == os.path.join(
        CUMULUSCI_PATH, "cumulusci", "files", "admin_profile.xml"
    )

    pc.minimum_cumulusci_version = "2.0.0"
    task = create_task(UpdateProfile, {}, project_config=pc)
    assert not task.options["include_packaged_objects"]

    task = create_task(
        UpdateProfile, {"include_packaged_objects": True}, project_config=pc
    )
    assert task.options["include_packaged_objects"]


def test_generate_package_xml():
    raise NotImplementedError
