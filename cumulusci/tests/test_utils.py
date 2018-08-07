from collections import OrderedDict
import io
import os
import unittest
import zipfile

from xml.etree import ElementTree as ET
import mock
import responses

from cumulusci import utils
from cumulusci.core.config import TaskConfig
from cumulusci.core.tasks import BaseTask

class TestUtils(unittest.TestCase):

    def test_findReplace(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, 'test')
            with open(path, 'w') as f:
                f.write('foo')

            logger = mock.Mock()
            utils.findReplace('foo', 'bar', d, '*', logger)

            logger.info.assert_called_once()
            with open(path, 'r') as f:
                result = f.read()
            self.assertEqual(result, 'bar')

    def test_findReplace_max(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, 'test')
            with open(path, 'w') as f:
                f.write('aa')

            logger = mock.Mock()
            utils.findReplace('a', 'b', d, '*', logger, max=1)

            logger.info.assert_called_once()
            with open(path, 'r') as f:
                result = f.read()
            self.assertEqual(result, 'ba')

    def test_findReplaceRegex(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, 'test')
            with open(path, 'w') as f:
                f.write('aa')

            logger = mock.Mock()
            utils.findReplaceRegex(r'\w', 'x', d, '*', logger)

            logger.info.assert_called_once()
            with open(path, 'r') as f:
                result = f.read()
            self.assertEqual(result, 'xx')

    def test_findRename(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, 'foo')
            with open(path, 'w') as f:
                f.write('aa')

            logger = mock.Mock()
            utils.findRename('foo', 'bar', d, logger)

            logger.info.assert_called_once()
            self.assertEqual(os.listdir(d), ['bar'])

    @mock.patch('xml.etree.ElementTree.parse')
    def test_elementtree_parse_file(self, mock_parse):
        _marker = object()
        mock_parse.return_value = _marker
        self.assertIs(utils.elementtree_parse_file('test_file'), _marker)

    @mock.patch('xml.etree.ElementTree.parse')
    def test_elementtree_parse_file_error(self, mock_parse):
        err = ET.ParseError()
        err.msg = 'it broke'
        err.lineno = 1
        mock_parse.side_effect = err
        try:
            utils.elementtree_parse_file('test_file')
        except ET.ParseError as err:
            self.assertEqual(str(err), 'it broke (test_file, line 1)')
        else:
            self.fail('Expected ParseError')

    def test_removeXmlElement(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, 'test.xml')
            with open(path, 'w') as f:
                f.write(
                    '<?xml version="1.0" ?>'
                    '<root xmlns="http://soap.sforce.com/2006/04/metadata">'
                    '<tag>text</tag></root>'
                )

            utils.removeXmlElement('tag', d, '*')

            with open(path, 'r') as f:
                result = f.read()
            expected = (
                '''<?xml version='1.0' encoding='UTF-8'?>
<root xmlns="http://soap.sforce.com/2006/04/metadata" />'''
            )
            self.assertEqual(expected, result)

    def test_remove_xml_element_not_found(self):
        tree = ET.fromstring('<root />')
        result = utils.remove_xml_element('tag', tree)
        self.assertIs(result, tree)

    @responses.activate
    def test_download_extract_zip(self):
        f = io.BytesIO()
        with zipfile.ZipFile(f, 'w') as zf:
            zf.writestr('top', 'top')
            zf.writestr('folder/test', 'test')
        f.seek(0)
        zipbytes = f.read()
        responses.add(
            method=responses.GET,
            url='http://test',
            body=zipbytes,
            content_type='application/zip',
        )

        zf = utils.download_extract_zip('http://test', subfolder='folder')
        result = zf.read('test')
        self.assertEqual('test', result)

    @responses.activate
    def test_download_extract_zip_to_target(self):
        with utils.temporary_dir() as d:
            f = io.BytesIO()
            with zipfile.ZipFile(f, 'w') as zf:
                zf.writestr('test', 'test')
            f.seek(0)
            zipbytes = f.read()
            responses.add(
                method=responses.GET,
                url='http://test',
                body=zipbytes,
                content_type='application/zip',
            )

            utils.download_extract_zip('http://test', target=d)
            self.assertIn('test', os.listdir(d))

    def test_zip_inject_namespace_managed(self):
        logger = mock.Mock()
        zf = zipfile.ZipFile(io.BytesIO(), 'w')
        zf.writestr(
            '___NAMESPACE___test',
            '%%%NAMESPACE%%%|%%%NAMESPACED_ORG%%%|%%%NAMESPACE_OR_C%%%|%%%NAMESPACED_ORG_OR_C%%%')

        zf = utils.zip_inject_namespace(
            zf, namespace='ns', managed=True, logger=logger)
        result = zf.read('ns__test')
        self.assertEqual('ns__||ns|c', result)

    def test_zip_inject_namespace_unmanaged(self):
        zf = zipfile.ZipFile(io.BytesIO(), 'w')
        zf.writestr(
            '___NAMESPACE___test',
            '%%%NAMESPACE%%%|%%%NAMESPACED_ORG%%%|%%%NAMESPACE_OR_C%%%|%%%NAMESPACED_ORG_OR_C%%%')

        zf = utils.zip_inject_namespace(zf, namespace='ns')
        result = zf.read('test')
        self.assertEqual('||c|c', result)

    def test_zip_inject_namespace_namespaced_org(self):
        zf = zipfile.ZipFile(io.BytesIO(), 'w')
        zf.writestr(
            '___NAMESPACE___test',
            '%%%NAMESPACE%%%|%%%NAMESPACED_ORG%%%|%%%NAMESPACE_OR_C%%%|%%%NAMESPACED_ORG_OR_C%%%')

        zf = utils.zip_inject_namespace(zf, namespace='ns', managed=True, namespaced_org=True)
        result = zf.read('ns__test')
        self.assertEqual('ns__|ns__|ns|ns', result)

    def test_zip_inject_namespace_skips_binary(self):
        contents = b'\xe2\x98\x83%%%NAMESPACE%%%'
        zf = zipfile.ZipFile(io.BytesIO(), 'w')
        zf.writestr('test', contents)

        zf = utils.zip_inject_namespace(zf, namespace='ns', managed=True, namespaced_org=True)
        result = zf.read('test')
        self.assertEqual(contents, result)

    def test_zip_strip_namespace(self):
        zf = zipfile.ZipFile(io.BytesIO(), 'w')
        zf.writestr('ns__test', 'ns__test ns:test')

        zf = utils.zip_strip_namespace(zf, 'ns')
        result = zf.read('test')
        self.assertEqual('test c:test', result)

    def test_zip_strip_namespace_skips_binary(self):
        contents = b'\xe2\x98\x83ns__'
        zf = zipfile.ZipFile(io.BytesIO(), 'w')
        zf.writestr('test', contents)

        zf = utils.zip_strip_namespace(zf, 'ns')
        result = zf.read('test')
        self.assertEqual(contents, result)

    def test_zip_tokenize_namespace(self):
        zf = zipfile.ZipFile(io.BytesIO(), 'w')
        zf.writestr('ns__test', 'ns__test ns:test')

        zf = utils.zip_tokenize_namespace(zf, 'ns')
        result = zf.read('___NAMESPACE___test')
        self.assertEqual('%%%NAMESPACE%%%test %%%NAMESPACE_OR_C%%%test', result)

    def test_zip_tokenize_namespace_skips_binary(self):
        contents = b'\xe2\x98\x83ns__'
        zf = zipfile.ZipFile(io.BytesIO(), 'w')
        zf.writestr('test', contents)

        zf = utils.zip_tokenize_namespace(zf, 'ns')
        result = zf.read('test')
        self.assertEqual(contents, result)

    def test_zip_tokenize_namespace_no_namespace(self):
        zf = zipfile.ZipFile(io.BytesIO(), 'w')
        zf.writestr('test', '')
        result = utils.zip_tokenize_namespace(zf, '')
        self.assertIs(zf, result)

    def test_zip_clean_metaxml(self):
        logger = mock.Mock()
        zf = zipfile.ZipFile(io.BytesIO(), 'w')
        zf.writestr(
            'classes/test-meta.xml',
            '<?xml version="1.0" ?>'
            '<root xmlns="http://soap.sforce.com/2006/04/metadata">'
            '<packageVersions>text</packageVersions></root>'
        )
        zf.writestr('test', '')
        zf.writestr('other/test-meta.xml', '')

        zf = utils.zip_clean_metaxml(zf, logger=logger)
        result = zf.read('classes/test-meta.xml')
        self.assertNotIn('packageVersions', result)

    def test_doc_task(self):
        task_config = TaskConfig({
            'class_path': 'cumulusci.tests.test_utils.TestTask',
            'options': {
                'color': 'black',
            }
        })
        result = utils.doc_task('command', task_config)
        self.assertEqual("""command
==========================================

**Description:** None

**Class::** cumulusci.tests.test_utils.TestTask

Options:
------------------------------------------

* **flavor** *(required)*: What flavor
* **color**: What color **Default: black**""", result)

    def test_package_xml_from_dict(self):
        items = {
            'ApexClass': ['TestClass'],
        }
        result = utils.package_xml_from_dict(
            items, api_version='43.0', package_name='TestPackage')
        self.assertEqual("""<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>TestPackage</fullName>
    <types>
        <members>TestClass</members>
        <name>ApexClass</name>
    </types>
    <version>43.0</version>
</Package>""", result)

class TestTask(BaseTask):
    """For testing doc_task"""
    task_options = OrderedDict((
        ('flavor', {
            'description': 'What flavor',
            'required': True,
        }),
        ('color', {
            'description': 'What color',
        }),
    ))
