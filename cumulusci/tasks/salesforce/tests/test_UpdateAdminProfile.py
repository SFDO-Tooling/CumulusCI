import mock
import os
import unittest

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
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


class TestUpdateAdminProfile(unittest.TestCase):
    maxDiff = None

    def test_run_task(self):
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
            profiles_path = os.path.join(task.tempdir, "profiles")
            admin_profile_path = os.path.join(profiles_path, "Admin.profile")
            os.mkdir(profiles_path)
            with open(admin_profile_path, "w") as f:
                f.write(ADMIN_PROFILE_BEFORE)

        def _check_result():
            with open(
                os.path.join(task.tempdir, "profiles", "Admin.profile"), "r"
            ) as f:
                result = f.read()
            self.assertMultiLineEqual(ADMIN_PROFILE_EXPECTED, result)

        task._retrieve_unpackaged = _retrieve_unpackaged
        task._deploy_metadata = _check_result
        task()

    def test_run_task__record_type_not_found(self):
        task = create_task(
            UpdateAdminProfile,
            {"record_types": [{"record_type": "DOESNT_EXIST"}], "namespaced_org": True},
        )

        def _retrieve_unpackaged():
            profiles_path = os.path.join(task.tempdir, "profiles")
            admin_profile_path = os.path.join(profiles_path, "Admin.profile")
            os.mkdir(profiles_path)
            with open(admin_profile_path, "w") as f:
                f.write(ADMIN_PROFILE_BEFORE)

        task._retrieve_unpackaged = _retrieve_unpackaged
        with self.assertRaises(TaskOptionsError):
            task()

    @mock.patch("cumulusci.salesforce_api.metadata.ApiRetrieveUnpackaged.__call__")
    def test_retrieve_unpackaged(self, ApiRetrieveUnpackaged):
        task = create_task(UpdateAdminProfile)
        task.tempdir = "/tmp"
        task._retrieve_unpackaged()
        ApiRetrieveUnpackaged.assert_called_once()

    def test_deploy_metadata(self):
        task = create_task(UpdateAdminProfile)
        task.tempdir = "/tmp"
        task._get_api = mock.Mock()
        task._deploy_metadata()
        task._get_api.assert_called_once()
