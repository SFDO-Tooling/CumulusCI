import base64
import io
import os
import zipfile

import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.flowrunner import StepSpec
from cumulusci.core.source_transforms.transforms import CleanMetaXMLTransform
from cumulusci.tasks.salesforce import Deploy
from cumulusci.utils import temporary_dir, touch

from .util import create_task

# from unittest import mock


class TestDeploy:
    def test_get_api(self):
        with temporary_dir() as path:
            touch("package.xml")
            task = create_task(
                Deploy,
                {
                    "path": path,
                    "namespace_tokenize": "ns",
                    "namespace_inject": "ns",
                    "namespace_strip": "ns",
                    "unmanaged": True,
                },
            )

            api = task._get_api()
            zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
            assert "package.xml" in zf.namelist()
            zf.close()

    #     @mock.patch("cumulusci.tasks.salesforce.Deploy.parseString")
    #     def test_collision_check(self,parseString):
    #         parseString=mock.Mock(return_value=mock.Mock(getElementsByTagName=mock.Mock(
    #             return_value=[
    #             {
    #                 "firstChild":{
    #                     "nextSibling":{
    #                         "firstChild":{
    #                             "nodeValue":"Entity of type 'CustomField' named 'Delivery__c.Supplier__c' cannot be found"
    #                         }
    #                     }

    #                 }
    #             }
    #         ]
    #         )
    #         )
    #         )

    #         with temporary_dir() as path:
    #             touch("package.xml")
    #             with open("package.xml", "w") as f:
    #                 f.write(
    #                 """<?xml version="1.0" encoding="UTF-8"?>
    # <Package xmlns="http://soap.sforce.com/2006/04/metadata">
    #     <types>
    #         <members>Delivery__c.Supplier__c</members>
    #         <name>CustomField</name>
    #     </types>
    #     <version>58.0</version>
    # </Package>""")
    #             task = create_task(
    #                 Deploy,
    #                 {
    #                     "path": path,
    #                     "namespace_tokenize": "ns",
    #                     "namespace_inject": "ns",
    #                     "namespace_strip": "ns",
    #                     "unmanaged": True,
    #                     "collision_check": True
    #                 },
    #             )
    #             task.api_retrieve_unpackaged=mock.Mock(
    #                 _get_response=mock.Mock(
    #                          return_value=

    #                 {
    #                     "content": b'<?xml version="1.0" encoding="UTF-8"?> <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns="http://soap.sforce.com/2006/04/metadata"><soapenv:Body><checkRetrieveStatusResponse><result><done>true</done><fileProperties><createdById>0051m0000069dpxAAA</createdById><createdByName>User User</createdByName><createdDate>2023-10-09T08:47:44.875Z</createdDate><fileName>unpackaged/package.xml</fileName><fullName>unpackaged/package.xml</fullName><id></id><lastModifiedById>0051m0000069dpxAAA</lastModifiedById><lastModifiedByName>User User</lastModifiedByName><lastModifiedDate>2023-10-09T08:47:44.875Z</lastModifiedDate><manageableState>unmanaged</manageableState><type>Package</type></fileProperties><id>09S1m000001EKBkEAO</id><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;CustomField&apos; named &apos;Delivery_Item__c.Food_Expiration_Date__c&apos; cannot be found</problem></messages><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;CustomField&apos; named &apos;Delivery__c.Status__c&apos; cannot be found</problem></messages><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;CustomField&apos; named &apos;Delivery_Item__c.Food_Storage__c&apos; cannot be found</problem></messages><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;CustomField&apos; named &apos;Delivery_Item__c.Delivery__c&apos; cannot be found</problem></messages><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;CustomField&apos; named &apos;Delivery__c.Scheduled_Date__c&apos; cannot be found</problem></messages><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;CustomField&apos; named &apos;Delivery__c.Supplier__c&apos; cannot be found</problem></messages><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;CustomObject&apos; named &apos;Delivery__c&apos; cannot be found</problem></messages><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;CustomObject&apos; named &apos;Delivery_Item__c&apos; cannot be found</problem></messages><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;CustomTab&apos; named &apos;Delivery__c&apos; cannot be found</problem></messages><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;Layout&apos; named &apos;Delivery_Item__c-Delivery Item Layout&apos; cannot be found</problem></messages><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;Layout&apos; named &apos;Delivery__c-Delivery Layout&apos; cannot be found</problem></messages><messages><fileName>unpackaged/package.xml</fileName><problem>Entity of type &apos;ListView&apos; named &apos;Delivery__c.All&apos; cannot be found</problem></messages><status>Succeeded</status><success>true</success><zipFile>UEsDBBQACAgIAPZFSVcAAAAAAAAAAAAAAAAWAAAAdW5wYWNrYWdlZC9wYWNrYWdlLnhtbKVTTU/DMAy991dUva8pCNCE0kyIUQkJCaQNrlGami2QNFXjwvrvyT7KuFTraE7Ji5/fsy3T2cbo8Atqp2yZRhdxEoVQSluocpVGr8tsMo1mLKAvQn6KFYQ+unRptEasbglxVlSxe7e1hFhaQy6T5IYkV8QAikKgiFgQ+kOxrcDt77u3AZN7STYHrbx2yx8RDOcy/gW4pKSLGsDLrC34w6ZStUBfCJ8LhH/lWKCtfZ1DuZ62kGsoGg3FWaJbIgps3DmEpqq0grqHUgoD7L5xaE2mQBeU7JD9BMifEQwex0BjJ8w85x8gcYSbkwpLkY8vdtIB4RYIn0RrGxzYgSO3n7bz132P6EV8p3V/fuXwTcF3v8Jh1dn1NE4o6V4BJYcNZ8EPUEsHCGtr2HwiAQAAEwQAAFBLAQIUABQACAgIAPZFSVdra9h8IgEAABMEAAAWAAAAAAAAAAAAAAAAAAAAAAB1bnBhY2thZ2VkL3BhY2thZ2UueG1sUEsFBgAAAAABAAEARAAAAGYBAAAAAA==</zipFile></result></checkRetrieveStatusResponse></soapenv:Body></soapenv:Envelope>'
    #                 }
    #                 )

    #             )

    #             is_collision,xml_map=task._collision_check(path)

    #             assert is_collision==False

    def test_get_api__managed(self):
        with temporary_dir() as path:
            touch("package.xml")
            task = create_task(
                Deploy, {"path": path, "namespace_inject": "ns", "unmanaged": False}
            )

            api = task._get_api()
            zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
            assert "package.xml" in zf.namelist()
            zf.close()

    def test_get_api__additional_options(self):
        with temporary_dir() as path:
            touch("package.xml")
            task = create_task(
                Deploy,
                {
                    "path": path,
                    "test_level": "RunSpecifiedTests",
                    "specified_tests": "TestA,TestB",
                    "unmanaged": False,
                },
            )

            api = task._get_api()
            assert api.run_tests == ["TestA", "TestB"]
            assert api.test_level == "RunSpecifiedTests"

    def test_get_api__skip_clean_meta_xml(self):
        with temporary_dir() as path:
            touch("package.xml")
            task = create_task(
                Deploy,
                {
                    "path": path,
                    "clean_meta_xml": False,
                    "unmanaged": True,
                },
            )

            api = task._get_api()
            zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
            assert "package.xml" in zf.namelist()
            zf.close()

    def test_get_api__static_resources(self):
        with temporary_dir() as path:
            with open("package.xml", "w") as f:
                f.write(
                    """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <name>OtherType</name>
    </types>
</Package>"""
                )
                touch("otherfile")

            with temporary_dir() as static_resource_path:
                os.mkdir("TestBundle")
                touch("TestBundle/test.txt")
                touch("TestBundle.resource-meta.xml")

                task = create_task(
                    Deploy,
                    {
                        "path": path,
                        "static_resource_path": static_resource_path,
                        "namespace_tokenize": "ns",
                        "namespace_inject": "ns",
                        "namespace_strip": "ns",
                        "unmanaged": True,
                    },
                )

                api = task._get_api()
                zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
                namelist = zf.namelist()
                assert "staticresources/TestBundle.resource" in namelist
                assert "staticresources/TestBundle.resource-meta.xml" in namelist
                package_xml = zf.read("package.xml").decode()
                assert "<name>StaticResource</name>" in package_xml
                assert "<members>TestBundle</members>" in package_xml
                zf.close()

    def test_get_api__missing_path(self):
        task = create_task(
            Deploy,
            {
                "path": "BOGUS",
                "unmanaged": True,
            },
        )

        api = task._get_api()
        assert api is None

    def test_get_api__empty_package_zip(self):
        with temporary_dir() as path:
            task = create_task(
                Deploy,
                {
                    "path": path,
                    "unmanaged": True,
                },
            )

            api = task._get_api()
            assert api is None

    def test_init_options(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                Deploy,
                {
                    "path": "empty",
                    "test_level": "RunSpecifiedTests",
                    "unmanaged": False,
                },
            )

        with pytest.raises(TaskOptionsError):
            create_task(
                Deploy, {"path": "empty", "test_level": "Test", "unmanaged": False}
            )

        with pytest.raises(TaskOptionsError):
            create_task(
                Deploy,
                {
                    "path": "empty",
                    "test_level": "RunLocalTests",
                    "specified_tests": ["TestA"],
                    "unmanaged": False,
                },
            )

    def test_init_options__transforms(self):
        d = create_task(
            Deploy,
            {
                "path": "src",
                "transforms": ["clean_meta_xml"],
            },
        )

        assert len(d.transforms) == 1
        assert isinstance(d.transforms[0], CleanMetaXMLTransform)

    def test_init_options__bad_transforms(self):
        with pytest.raises(TaskOptionsError) as e:
            create_task(
                Deploy,
                {
                    "path": "src",
                    "transforms": [{}],
                },
            )

            assert "transform spec is not valid" in str(e)

    def test_freeze_sets_kind(self):
        task = create_task(
            Deploy,
            {
                "path": "path",
                "namespace_tokenize": "ns",
                "namespace_inject": "ns",
                "namespace_strip": "ns",
            },
        )
        step = StepSpec(
            step_num=1,
            task_name="deploy",
            task_config=task.task_config,
            task_class=None,
            project_config=task.project_config,
        )

        assert all(s["kind"] == "metadata" for s in task.freeze(step))
