from unittest.mock import Mock

import pytest
from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.preflight.sobjects import (
    CheckSObjectOWDs,
    CheckSObjectPerms,
    CheckSObjectsAvailable,
)
from cumulusci.tasks.salesforce.tests.util import create_task


class TestCheckSObjectsAvailable:
    def test_sobject_preflight(self):
        task = create_task(CheckSObjectsAvailable, {})

        task._init_task = Mock()
        task.sf = Mock()
        task.sf.describe.return_value = {
            "sobjects": [{"name": "Network"}, {"name": "Account"}]
        }

        task()

        assert task.return_values == {"Network", "Account"}


class TestCheckSObjectPerms:
    def test_sobject_perms_preflight(self):
        task = create_task(
            CheckSObjectPerms,
            {
                "permissions": {
                    "Network": {"createable": "false"},
                    "Account": {"createable": True},
                }
            },
        )

        task._init_task = Mock()
        task.sf = Mock()
        task.sf.describe.return_value = {
            "sobjects": [
                {"name": "Network", "createable": False},
                {"name": "Account", "createable": True},
            ]
        }

        task()

        assert task.return_values is True

    def test_sobject_perms_preflight__negative(self):
        task = create_task(
            CheckSObjectPerms,
            {
                "permissions": {
                    "Network": {"createable": "false"},
                    "Account": {"createable": True},
                }
            },
        )

        task._init_task = Mock()
        task.sf = Mock()
        task.sf.describe.return_value = {
            "sobjects": [
                {"name": "Network", "createable": False},
                {"name": "Account", "createable": False},
            ]
        }

        task()

        assert task.return_values is False

    def test_sobject_perms_preflight__missing(self):
        task = create_task(
            CheckSObjectPerms,
            {
                "permissions": {
                    "Network": {"createable": "false"},
                    "Account": {"createable": True},
                }
            },
        )

        task._init_task = Mock()
        task.sf = Mock()
        task.sf.describe.return_value = {"sobjects": [{"name": "Network"}]}

        task()

        assert task.return_values is False

    def test_sobject_perms_preflight__bad_options(self):
        with pytest.raises(TaskOptionsError):
            create_task(CheckSObjectPerms, {"permissions": True})


class TestCheckSObjectOWDs:
    def test_sobject_preflight__positive(self):
        task = create_task(
            CheckSObjectOWDs,
            {
                "org_wide_defaults": [
                    {"api_name": "Account", "internal_sharing_model": "Private"},
                    {"api_name": "Contact", "internal_sharing_model": "ReadWrite"},
                ]
            },
        )
        task._init_task = Mock()
        task.sf = Mock()
        task.sf.query.return_value = {
            "totalSize": 2,
            "records": [
                {"QualifiedApiName": "Account", "InternalSharingModel": "Private"},
                {"QualifiedApiName": "Contact", "InternalSharingModel": "ReadWrite"},
            ],
        }
        task()

        assert task.return_values is True

    def test_sobject_preflight__negative(self):
        task = create_task(
            CheckSObjectOWDs,
            {
                "org_wide_defaults": [
                    {"api_name": "Account", "internal_sharing_model": "Private"}
                ]
            },
        )
        task._init_task = Mock()
        task.sf = Mock()
        task.sf.query.return_value = {
            "totalSize": 1,
            "records": [
                {"QualifiedApiName": "Account", "InternalSharingModel": "ReadWrite"}
            ],
        }
        task()

        assert task.return_values is False

    def test_sobject_preflight__external(self):
        task = create_task(
            CheckSObjectOWDs,
            {
                "org_wide_defaults": [
                    {"api_name": "Account", "external_sharing_model": "Private"}
                ]
            },
        )
        task._init_task = Mock()
        task.sf = Mock()
        task.sf.query.return_value = {
            "totalSize": 1,
            "records": [
                {
                    "QualifiedApiName": "Account",
                    "InternalSharingModel": "Private",
                    "ExternalSharingModel": "Private",
                }
            ],
        }
        task()

        assert task.return_values is True

    def test_sobject_preflight__both(self):
        task = create_task(
            CheckSObjectOWDs,
            {
                "org_wide_defaults": [
                    {
                        "api_name": "Account",
                        "internal_sharing_model": "ReadWrite",
                        "external_sharing_model": "Private",
                    }
                ]
            },
        )
        task._init_task = Mock()
        task.sf = Mock()
        task.sf.query.return_value = {
            "totalSize": 1,
            "records": [
                {
                    "QualifiedApiName": "Account",
                    "InternalSharingModel": "ReadWrite",
                    "ExternalSharingModel": "Private",
                }
            ],
        }
        task()

        assert task.return_values is True

    def test_sobject_preflight__external_not_enabled(self):
        task = create_task(
            CheckSObjectOWDs,
            {
                "org_wide_defaults": [
                    {"api_name": "Account", "external_sharing_model": "Private"}
                ]
            },
        )
        task._init_task = Mock()
        task.sf = Mock()
        task.sf.query.side_effect = SalesforceMalformedRequest(
            "url", 400, "resource_name", "content"
        )
        task()

        assert task.return_values is False

    def test_sobject_preflight__task_options(self):
        with pytest.raises(TaskOptionsError):
            create_task(CheckSObjectOWDs, {})
        with pytest.raises(TaskOptionsError):
            create_task(
                CheckSObjectOWDs,
                {"org_wide_defaults": [{"internal_sharing_model": "Private"}]},
            )
        with pytest.raises(TaskOptionsError):
            create_task(
                CheckSObjectOWDs, {"org_wide_defaults": [{"api_name": "Account"}]}
            )
