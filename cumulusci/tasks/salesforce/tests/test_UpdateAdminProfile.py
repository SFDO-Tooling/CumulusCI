from pathlib import Path
from unittest import mock

import pytest
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce import UpdateAdminProfile

from .util import create_task

ADMIN_PROFILE_BEFORE = """<?xml version='1.0' encoding='utf-8'?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
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


def test_run_task():
    task = create_task(
        UpdateAdminProfile,
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

    def _retrieve_unpackaged():
        profiles_path = Path(task.retrieve_dir, "profiles")
        admin_profile_path = Path(profiles_path, "Admin.profile")
        profiles_path.mkdir()
        admin_profile_path.write_text(ADMIN_PROFILE_BEFORE)

    def _check_result():
        result_path = Path(task.retrieve_dir, "profiles", "Admin.profile")
        result = result_path.read_text()
        assert ADMIN_PROFILE_EXPECTED == result

    task._retrieve_unpackaged = _retrieve_unpackaged
    task._deploy_metadata = _check_result
    task()


def test_run_task__record_type_not_found():
    task = create_task(
        UpdateAdminProfile,
        {"record_types": [{"record_type": "DOESNT_EXIST"}], "namespaced_org": True},
    )

    def _retrieve_unpackaged():
        profiles_path = Path(task.retrieve_dir, "profiles")
        admin_profile_path = Path(profiles_path, "Admin.profile")
        profiles_path.mkdir()
        admin_profile_path.write_text(ADMIN_PROFILE_BEFORE)

    task._retrieve_unpackaged = _retrieve_unpackaged
    with pytest.raises(TaskOptionsError):
        task()


@mock.patch("cumulusci.salesforce_api.metadata.ApiRetrieveUnpackaged.__call__")
def test_retrieve_unpackaged(ApiRetrieveUnpackaged):
    task = create_task(UpdateAdminProfile)
    task.retrieve_dir = "/tmp"
    task._retrieve_unpackaged()
    ApiRetrieveUnpackaged.assert_called_once()


def test_deploy_metadata(tmpdir):
    task = create_task(UpdateAdminProfile)
    task.retrieve_dir = Path(tmpdir, "retrieve", "profiles")
    task.deploy_dir = Path(tmpdir, "deploy")
    task.retrieve_dir.mkdir(parents=True)
    task.deploy_dir.mkdir(parents=True)
    task.retrieve_dir = task.retrieve_dir.parent
    task.deploy_dir = task.deploy_dir.parent

    task._get_api = mock.Mock()
    task._deploy_metadata()
    task._get_api.assert_called_once()
