from cumulusci.core.exceptions import TaskOptionsError
from unittest.mock import Mock
import unittest

from cumulusci.tasks.salesforce.sobject_preflights import CheckSobjectOWDs
from .util import create_task

from simple_salesforce.exceptions import SalesforceMalformedRequest


class TestLicensePreflights(unittest.TestCase):
    def test_sobject_preflight__positive(self):
        task = create_task(
            CheckSobjectOWDs,
            {
                "org_wide_defaults": [
                    {"api_name": "Account", "internal_sharing_model": "Private"}
                ]
            },
        )
        task._init_api = Mock()
        task._init_api.return_value.query.return_value = {
            "totalSize": 1,
            "records": [{"InternalSharingModel": "Private"}],
        }
        task()

        assert task.return_values is True

    def test_sobject_preflight__negative(self):
        task = create_task(
            CheckSobjectOWDs,
            {
                "org_wide_defaults": [
                    {"api_name": "Account", "internal_sharing_model": "Private"}
                ]
            },
        )
        task._init_api = Mock()
        task._init_api.return_value.query.return_value = {
            "totalSize": 1,
            "records": [{"InternalSharingModel": "ReadWrite"}],
        }
        task()

        assert task.return_values is False

    def test_sobject_preflight__external(self):
        task = create_task(
            CheckSobjectOWDs,
            {
                "org_wide_defaults": [
                    {"api_name": "Account", "external_sharing_model": "Private"}
                ]
            },
        )
        task._init_api = Mock()
        task._init_api.return_value.query.return_value = {
            "totalSize": 1,
            "records": [
                {"InternalSharingModel": "Private", "ExternalSharingModel": "Private"}
            ],
        }
        task()

        assert task.return_values is True

    def test_sobject_preflight__both(self):
        task = create_task(
            CheckSobjectOWDs,
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
        task._init_api = Mock()
        task._init_api.return_value.query.return_value = {
            "totalSize": 1,
            "records": [
                {"InternalSharingModel": "ReadWrite", "ExternalSharingModel": "Private"}
            ],
        }
        task()

        assert task.return_values is True

    def test_sobject_preflight__external_not_enabled(self):
        task = create_task(
            CheckSobjectOWDs,
            {
                "org_wide_defaults": [
                    {"api_name": "Account", "external_sharing_model": "Private"}
                ]
            },
        )
        task._init_api = Mock()
        task._init_api.return_value.query.side_effect = SalesforceMalformedRequest(
            "url", 400, "resource_name", "content"
        )
        task()

        assert task.return_values is False

    def test_sobject_preflight__task_options(self):
        with self.assertRaises(TaskOptionsError):
            create_task(CheckSobjectOWDs, {})
        with self.assertRaises(TaskOptionsError):
            create_task(
                CheckSobjectOWDs,
                {"org_wide_defaults": [{"internal_sharing_model": "Private"}]},
            )
        with self.assertRaises(TaskOptionsError):
            create_task(
                CheckSobjectOWDs, {"org_wide_defaults": [{"api_name": "Account"}]}
            )
