import base64
import io
import zipfile

from cumulusci.core.config import BaseProjectConfig, UniversalConfig
from cumulusci.tasks.salesforce import CreatePackage

from .util import create_task


class TestCreatePackage:
    def test_get_package_zip(self):
        project_config = BaseProjectConfig(
            UniversalConfig(),
            {"project": {"package": {"name": "TestPackage", "api_version": "43.0"}}},
        )
        task = create_task(CreatePackage, project_config=project_config)
        package_zip = task._get_package_zip()
        zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(package_zip)), "r")
        package_xml = zf.read("package.xml")
        assert b"<fullName>TestPackage</fullName>" in package_xml
