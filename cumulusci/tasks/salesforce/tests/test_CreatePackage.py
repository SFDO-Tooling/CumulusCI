from unittest import mock
import unittest

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.tasks.salesforce import CreatePackage
from .util import create_task


class TestCreatePackage(unittest.TestCase):
    @mock.patch("cumulusci.salesforce_api.package_zip.CreatePackageZipBuilder.__call__")
    def test_get_package_zip(self, CreatePackageZipBuilder):
        project_config = BaseProjectConfig(
            BaseGlobalConfig(),
            {"project": {"package": {"name": "TestPackage", "api_version": "43.0"}}},
        )
        task = create_task(CreatePackage, project_config=project_config)
        task._get_package_zip()
        CreatePackageZipBuilder.assert_called_once()
