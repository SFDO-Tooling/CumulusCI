import os
import pathlib
import tempfile
from unittest import mock

import pytest

from cumulusci.core.exceptions import TaskOptionsError, CumulusCIException
from cumulusci.tasks.metadata_etl import MetadataOperation
from cumulusci.tasks.salesforce import ProfileGrantAllAccess
from cumulusci.utils import CUMULUSCI_PATH
from cumulusci.utils.xml import metadata_tree
from cumulusci.tests.util import create_project_config

from .util import create_task

ADMIN_PROFILE_BEFORE = b"""<?xml version='1.0' encoding='utf-8'?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <applicationVisibilities>
        <application>npsp__Nonprofit_CRM</application>
        <default>true</default>
        <visible>false</visible>
    </applicationVisibilities>
    <classAccesses>
        <apexClass>TestClass</apexClass>
        <enabled>false</enabled>
    </classAccesses>
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

ADMIN_PROFILE_EXPECTED = """<?xml version="1.0" encoding="UTF-8"?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <applicationVisibilities>
        <application>npsp__Nonprofit_CRM</application>
        <default>true</default>
        <visible>true</visible>
    </applicationVisibilities>
    <classAccesses>
        <apexClass>TestClass</apexClass>
        <enabled>true</enabled>
    </classAccesses>
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
</Profile>
"""

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

ADMIN_PROFILE_BEFORE__MULTI_OBJECT_RT = b"""<?xml version='1.0' encoding='utf-8'?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <recordTypeVisibilities>
        <recordType>Account.Business_Account</recordType>
        <default>false</default>
        <personAccountDefault>true</personAccountDefault>
        <visible>true</visible>
    </recordTypeVisibilities>
    <recordTypeVisibilities>
        <recordType>Opportunity.Donation</recordType>
        <default>true</default>
        <personAccountDefault>false</personAccountDefault>
        <visible>false</visible>
    </recordTypeVisibilities>
</Profile>"""

ADMIN_PROFILE_EXPECTED__MULTI_OBJECT_RT = """<?xml version="1.0" encoding="UTF-8"?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <recordTypeVisibilities>
        <recordType>Account.Business_Account</recordType>
        <default>true</default>
        <personAccountDefault>true</personAccountDefault>
        <visible>true</visible>
    </recordTypeVisibilities>
    <recordTypeVisibilities>
        <recordType>Opportunity.Donation</recordType>
        <default>true</default>
        <personAccountDefault>false</personAccountDefault>
        <visible>false</visible>
    </recordTypeVisibilities>
</Profile>
"""


def test_run_task():
    with tempfile.TemporaryDirectory() as tempdir:
        with open(
            os.path.join(CUMULUSCI_PATH, "cumulusci", "files", "admin_profile.xml"), "w"
        ) as f:
            f.write(PACKAGE_XML_BEFORE)

        retrieve_dir = pathlib.Path(tempdir, "retrieve")
        retrieve_dir.mkdir()
        target_dir = retrieve_dir / "profiles"
        target_dir.mkdir()

        with open(target_dir / "Admin.profile", "wb") as f:
            f.write(ADMIN_PROFILE_BEFORE)

        task = create_task(
            ProfileGrantAllAccess,
            {
                "record_types": [
                    {
                        "record_type": "Account.HH_Account",
                        "default": True,
                        "person_account_default": True,
                    }
                ],
                "namespaced_org": True,
                "include_packaged_objects": False,
            },
        )

        task._retrieve = mock.Mock()
        task._deploy = mock.Mock()
        task._create_directories = mock.Mock()
        task.retrieve_dir = retrieve_dir
        task.deploy_dir = pathlib.Path(tempdir, "deploy")
        task.deploy_dir.mkdir()

        task()

        dest_path = task.deploy_dir / "profiles" / "Admin.profile"
        assert dest_path.exists()

        assert dest_path.read_text() == ADMIN_PROFILE_EXPECTED


def test_transforms_profile():
    task = create_task(
        ProfileGrantAllAccess,
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

    inbound = metadata_tree.fromstring(ADMIN_PROFILE_BEFORE)
    outbound = task._transform_entity(inbound, "Admin")

    xml_output = outbound.tostring(xml_declaration=True)

    assert xml_output == ADMIN_PROFILE_EXPECTED


def test_transforms_profile__multi_object_rt():
    task = create_task(
        ProfileGrantAllAccess,
        {
            "record_types": [
                {
                    "record_type": "Account.Business_Account",
                    "default": True,
                    "person_account_default": True,
                }
            ],
            "namespaced_org": True,
        },
    )

    inbound = metadata_tree.fromstring(ADMIN_PROFILE_BEFORE__MULTI_OBJECT_RT)
    outbound = task._transform_entity(inbound, "Admin")

    xml_output = outbound.tostring(xml_declaration=True)

    assert xml_output == ADMIN_PROFILE_EXPECTED__MULTI_OBJECT_RT


def test_throws_exception_record_type_not_found():
    task = create_task(
        ProfileGrantAllAccess,
        {"record_types": [{"record_type": "DOESNT_EXIST"}], "namespaced_org": True},
    )

    with pytest.raises(TaskOptionsError):
        task._transform_entity(metadata_tree.fromstring(ADMIN_PROFILE_BEFORE), "Admin")


def test_expand_package_xml():
    task = create_task(ProfileGrantAllAccess, {"api_names": ["Admin"]})
    task.tooling = mock.Mock()
    task.tooling.query_all.return_value = {
        "totalSize": 2,
        "records": [
            {"DeveloperName": "Test", "NamespacePrefix": "ns"},
            {"DeveloperName": "Foo_Bar", "NamespacePrefix": "fb"},
        ],
    }

    package_xml = metadata_tree.fromstring(PACKAGE_XML_BEFORE)
    task._expand_package_xml(package_xml)
    types = package_xml.find("types", name="CustomObject")
    assert "ns__Test__c" in {elem.text for elem in types.findall("members")}
    assert "fb__Foo_Bar__c" in {elem.text for elem in types.findall("members")}


def test_expand_package_xml__broken_package():
    task = create_task(ProfileGrantAllAccess, {"api_names": ["Admin"]})
    task.tooling = mock.Mock()
    task.tooling.query_all.return_value = {
        "totalSize": 2,
        "records": [
            {"DeveloperName": "Test", "NamespacePrefix": "ns"},
            {"DeveloperName": "Foo_Bar", "NamespacePrefix": "fb"},
        ],
    }

    package_xml = metadata_tree.fromstring(PACKAGE_XML_BEFORE)
    types = package_xml.find("types", name="CustomObject")
    types.find("name").text = "NotCustomObject"
    with pytest.raises(CumulusCIException):
        task._expand_package_xml(package_xml)


def test_expand_profile_members():
    task = create_task(
        ProfileGrantAllAccess,
        {
            "api_names": ["Admin", "%%%NAMESPACE%%%Continuous Integration"],
            "namespace_inject": "ns",
            "managed": True,
        },
    )
    package_xml = metadata_tree.fromstring(PACKAGE_XML_BEFORE)

    task._expand_profile_members(package_xml)

    types = package_xml.find("types", name="Profile")
    assert {elem.text for elem in types.findall("members")} == {
        "Admin",
        "ns__Continuous Integration",
    }


def test_expand_profile_members__namespaced_org():
    task = create_task(
        ProfileGrantAllAccess,
        {
            "api_names": ["Admin", "%%%NAMESPACE%%%Continuous Integration"],
            "namespace_inject": "ns",
            "namespaced_org": True,
        },
    )
    package_xml = metadata_tree.fromstring(PACKAGE_XML_BEFORE)

    task._expand_profile_members(package_xml)

    types = package_xml.find("types", name="Profile")
    assert {elem.text for elem in types.findall("members")} == {
        "Admin",
        "Continuous Integration",
    }


def test_expand_profile_members__broken_package():
    task = create_task(ProfileGrantAllAccess, {"api_names": ["Admin"]})
    task.tooling = mock.Mock()
    task.tooling.query.return_value = {
        "totalSize": 2,
        "records": [
            {"DeveloperName": "Test", "NamespacePrefix": "ns"},
            {"DeveloperName": "Foo_Bar", "NamespacePrefix": "fb"},
        ],
    }

    package_xml = metadata_tree.fromstring(PACKAGE_XML_BEFORE)
    types = package_xml.find("types", name="Profile")
    types.find("name").text = "NotProfile"

    with pytest.raises(CumulusCIException):
        task._expand_profile_members(package_xml)


def test_init_options__general():
    pc = create_project_config()
    pc.project__package__namespace = "ns"
    task = create_task(ProfileGrantAllAccess, {"managed": "true"}, project_config=pc)
    assert task.options["managed"]
    assert not task.options["namespaced_org"]
    assert task.options["namespace_inject"] == "ns"
    assert task.namespace_prefixes == {"managed": "ns__", "namespaced_org": ""}

    task = create_task(
        ProfileGrantAllAccess, {"namespaced_org": "true"}, project_config=pc
    )
    assert task.options["managed"]
    assert task.options["namespaced_org"]
    assert task.options["namespace_inject"] == "ns"
    assert task.namespace_prefixes == {"managed": "ns__", "namespaced_org": "ns__"}

    task = create_task(ProfileGrantAllAccess, {}, project_config=pc)
    assert not task.options["managed"]
    assert not task.options["namespaced_org"]
    assert task.options["namespace_inject"] == "ns"
    assert task.namespace_prefixes == {"managed": "", "namespaced_org": ""}


def test_init_options__api_names():
    task = create_task(
        ProfileGrantAllAccess,
        {
            "api_names": ["Admin", "%%%NAMESPACE%%%Continuous Integration"],
            "namespace_inject": "ns",
            "managed": True,
        },
    )
    assert task.api_names == {"Admin", "ns__Continuous Integration"}

    task = create_task(
        ProfileGrantAllAccess,
        {
            "api_names": ["Admin", "%%%NAMESPACE%%%Continuous Integration"],
            "namespace_inject": "ns",
            "managed": False,
        },
    )
    assert task.api_names == {"Admin", "Continuous Integration"}

    task = create_task(
        ProfileGrantAllAccess, {"profile_name": "Continuous Integration"}
    )
    assert task.api_names == {"Continuous Integration"}

    task = create_task(ProfileGrantAllAccess, {})
    assert task.api_names == {"Admin"}

    task = create_task(ProfileGrantAllAccess, {"package_xml": "lib/admin_profile.xml"})
    assert task.api_names == {"*"}


def test_init_options__include_packaged_objects():
    pc = create_project_config()
    pc.minimum_cumulusci_version = "4.0.0"
    task = create_task(
        ProfileGrantAllAccess,
        {"package_xml": "lib/admin_profile.xml"},
        project_config=pc,
    )
    assert task.package_xml_path == "lib/admin_profile.xml"
    assert not task.options["include_packaged_objects"]

    task = create_task(ProfileGrantAllAccess, {}, project_config=pc)
    assert task.options["include_packaged_objects"]
    assert task.package_xml_path == os.path.join(
        CUMULUSCI_PATH, "cumulusci", "files", "admin_profile.xml"
    )

    pc.minimum_cumulusci_version = "2.0.0"
    task = create_task(ProfileGrantAllAccess, {}, project_config=pc)
    assert not task.options["include_packaged_objects"]

    task = create_task(
        ProfileGrantAllAccess, {"include_packaged_objects": True}, project_config=pc
    )
    assert task.options["include_packaged_objects"]


def test_generate_package_xml__retrieve():
    with tempfile.TemporaryDirectory() as tmp_dir:
        admin_profile = os.path.join(tmp_dir, "admin_profile.xml")
        with open(admin_profile, "w") as f:
            f.write(PACKAGE_XML_BEFORE)
        with open(
            os.path.join(CUMULUSCI_PATH, "cumulusci", "files", "admin_profile.xml"), "w"
        ) as f:
            f.write(PACKAGE_XML_BEFORE)

        task = create_task(
            ProfileGrantAllAccess,
            {"package_xml": admin_profile, "include_packaged_objects": False},
        )

        task._expand_profile_members = mock.Mock()
        task._expand_package_xml = mock.Mock()
        task._generate_package_xml(MetadataOperation.RETRIEVE)
        task._expand_profile_members.assert_not_called()
        task._expand_package_xml.assert_not_called()

        task = create_task(
            ProfileGrantAllAccess,
            {"package_xml": admin_profile, "include_packaged_objects": True},
        )

        task._expand_profile_members = mock.Mock()
        task._expand_package_xml = mock.Mock()
        task._generate_package_xml(MetadataOperation.RETRIEVE)
        task._expand_profile_members.assert_not_called()
        task._expand_package_xml.assert_called_once()

        task = create_task(ProfileGrantAllAccess, {"include_packaged_objects": True})

        task._expand_profile_members = mock.Mock()
        task._expand_package_xml = mock.Mock()
        task._generate_package_xml(MetadataOperation.RETRIEVE)
        task._expand_profile_members.assert_called_once()
        task._expand_package_xml.assert_called_once()

        task = create_task(ProfileGrantAllAccess, {"include_packaged_objects": False})

        task._expand_profile_members = mock.Mock()
        task._expand_package_xml = mock.Mock()
        task._generate_package_xml(MetadataOperation.RETRIEVE)
        task._expand_profile_members.assert_called_once()
        task._expand_package_xml.assert_not_called()


def test_init_options_raises_combined_options():
    with pytest.raises(TaskOptionsError):
        create_task(
            ProfileGrantAllAccess,
            {"package_xml": "admin_profile.xml", "profile_name": "test"},
        )
