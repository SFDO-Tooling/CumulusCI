import os
import tempfile
import unittest

from cumulusci.tasks.metadata.package import PackageXmlGenerator

__location__ = os.path.split(os.path.realpath(__file__))[0]

class TestPackageXmlGenerator(unittest.TestCase):

    def test_package_name_urlencoding(self):
        api_version = '36.0'
        package_name = 'Test & Package'
        path = tempfile.mkdtemp()

        expected = '<?xml version="1.0" encoding="UTF-8"?>\n'
        expected += '<Package xmlns="http://soap.sforce.com/2006/04/metadata">\n'
        expected += '    <fullName>Test %26 Package</fullName>\n'
        expected += '    <version>{}</version>\n'.format(api_version)
        expected += '</Package>'
        
        generator = PackageXmlGenerator(path, api_version, package_name)
        package_xml = generator()

        self.assertEquals(package_xml, expected)
        
    
    def test_namespaced_report_folder(self):
        api_version = '36.0'
        package_name = 'Test Package'
        test_dir = 'namespaced_report_folder'

        path = os.path.join(
            __location__,
            'package_metadata',
            test_dir,
        )

        generator = PackageXmlGenerator(path, api_version, package_name)
        with open(os.path.join(path, 'package.xml'), 'r') as f:
            expected_package_xml = f.read().strip()
        package_xml = generator()

        self.assertEquals(package_xml, expected_package_xml)

    def test_delete_namespaced_report_folder(self):
        api_version = '36.0'
        package_name = 'Test Package'
        test_dir = 'namespaced_report_folder'

        path = os.path.join(
            __location__,
            'package_metadata',
            test_dir,
        )

        generator = PackageXmlGenerator(path, api_version, package_name, delete=True)
        with open(os.path.join(path, 'destructiveChanges.xml'), 'r') as f:
            expected_package_xml = f.read().strip()
        package_xml = generator()

        self.assertEquals(package_xml, expected_package_xml)
