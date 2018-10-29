# -*- coding: utf-8 -*-

from collections import OrderedDict
import io
import os
import unittest
import zipfile
from datetime import datetime, timedelta

from xml.etree import ElementTree as ET
import mock
import responses

from cumulusci import utils
from cumulusci.core.config import TaskConfig
from cumulusci.core.tasks import BaseTask


class TestUtils(unittest.TestCase):
    def test_findReplace(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, "test")
            with open(path, "w") as f:
                f.write("foo")

            logger = mock.Mock()
            utils.findReplace("foo", "bar", d, "*", logger)

            logger.info.assert_called_once()
            with open(path, "r") as f:
                result = f.read()
            self.assertEqual(result, "bar")

    def test_findReplace_max(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, "test")
            with open(path, "w") as f:
                f.write("aa")

            logger = mock.Mock()
            utils.findReplace("a", "b", d, "*", logger, max=1)

            logger.info.assert_called_once()
            with open(path, "r") as f:
                result = f.read()
            self.assertEqual(result, "ba")

    def test_findReplaceRegex(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, "test")
            with open(path, "w") as f:
                f.write("aa")

            logger = mock.Mock()
            utils.findReplaceRegex(r"\w", "x", d, "*", logger)

            logger.info.assert_called_once()
            with open(path, "r") as f:
                result = f.read()
            self.assertEqual(result, "xx")

    def test_findRename(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, "foo")
            with open(path, "w") as f:
                f.write("aa")

            logger = mock.Mock()
            utils.findRename("foo", "bar", d, logger)

            logger.info.assert_called_once()
            self.assertEqual(os.listdir(d), ["bar"])

    @mock.patch("xml.etree.ElementTree.parse")
    def test_elementtree_parse_file(self, mock_parse):
        _marker = object()
        mock_parse.return_value = _marker
        self.assertIs(utils.elementtree_parse_file("test_file"), _marker)

    @mock.patch("xml.etree.ElementTree.parse")
    def test_elementtree_parse_file_error(self, mock_parse):
        err = ET.ParseError()
        err.msg = "it broke"
        err.lineno = 1
        mock_parse.side_effect = err
        try:
            utils.elementtree_parse_file("test_file")
        except ET.ParseError as err:
            self.assertEqual(str(err), "it broke (test_file, line 1)")
        else:
            self.fail("Expected ParseError")

    def test_removeXmlElement(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, "test.xml")
            with open(path, "w") as f:
                f.write(
                    '<?xml version="1.0" ?>'
                    '<root xmlns="http://soap.sforce.com/2006/04/metadata">'
                    "<tag>text</tag></root>"
                )

            utils.removeXmlElement("tag", d, "*")

            with open(path, "r") as f:
                result = f.read()
            expected = """<?xml version='1.0' encoding='UTF-8'?>
<root xmlns="http://soap.sforce.com/2006/04/metadata" />"""
            self.assertEqual(expected, result)

    @mock.patch("xml.etree.ElementTree.parse")
    def test_remove_xml_element_parse_error(self, mock_parse):
        err = ET.ParseError()
        err.msg = "it broke"
        err.lineno = 1
        mock_parse.side_effect = err
        with utils.temporary_dir() as d:
            path = os.path.join(d, "test.xml")
            with open(path, "w") as f:
                f.write(
                    '<?xml version="1.0" ?>'
                    '<root xmlns="http://soap.sforce.com/2006/04/metadata">'
                    "<tag>text</tag></root>"
                )
            try:
                utils.removeXmlElement("tag", d, "*")
            except ET.ParseError as err:
                self.assertEqual(str(err), "it broke (test.xml, line 1)")
            else:
                self.fail("Expected ParseError")

    def test_remove_xml_element_not_found(self):
        tree = ET.fromstring("<root />")
        result = utils.remove_xml_element("tag", tree)
        self.assertIs(result, tree)

    @responses.activate
    def test_download_extract_zip(self):
        f = io.BytesIO()
        with zipfile.ZipFile(f, "w") as zf:
            zf.writestr("top", "top")
            zf.writestr("folder/test", "test")
        f.seek(0)
        zipbytes = f.read()
        responses.add(
            method=responses.GET,
            url="http://test",
            body=zipbytes,
            content_type="application/zip",
        )

        zf = utils.download_extract_zip("http://test", subfolder="folder")
        result = zf.read("test")
        self.assertEqual(b"test", result)

    @responses.activate
    def test_download_extract_zip_to_target(self):
        with utils.temporary_dir() as d:
            f = io.BytesIO()
            with zipfile.ZipFile(f, "w") as zf:
                zf.writestr("test", "test")
            f.seek(0)
            zipbytes = f.read()
            responses.add(
                method=responses.GET,
                url="http://test",
                body=zipbytes,
                content_type="application/zip",
            )

            utils.download_extract_zip("http://test", target=d)
            self.assertIn("test", os.listdir(d))

    def test_download_extract_github(self):
        f = io.BytesIO()
        with zipfile.ZipFile(f, "w") as zf:
            zf.writestr("top/", "top")
            zf.writestr("top/src/", "top_src")
            zf.writestr("top/src/test", "test")
        f.seek(0)
        zipbytes = f.read()
        mock_repo = mock.Mock(default_branch="master")

        def assign_bytes(archive_type, zip_content, ref=None):
            zip_content.write(zipbytes)

        mock_archive = mock.Mock(return_value=True, side_effect=assign_bytes)
        mock_repo.archive = mock_archive
        zf = utils.download_extract_github(mock_repo, "src")
        result = zf.read("test")
        self.assertEqual(b"test", result)

    def test_zip_inject_namespace_managed(self):
        logger = mock.Mock()
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr(
            "___NAMESPACE___test",
            "%%%NAMESPACE%%%|%%%NAMESPACED_ORG%%%|%%%NAMESPACE_OR_C%%%|%%%NAMESPACED_ORG_OR_C%%%",
        )

        zf = utils.zip_inject_namespace(zf, namespace="ns", managed=True, logger=logger)
        result = zf.read("ns__test")
        self.assertEqual(b"ns__||ns|c", result)

    def test_zip_inject_namespace_unmanaged(self):
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr(
            "___NAMESPACE___test",
            "%%%NAMESPACE%%%|%%%NAMESPACED_ORG%%%|%%%NAMESPACE_OR_C%%%|%%%NAMESPACED_ORG_OR_C%%%",
        )

        zf = utils.zip_inject_namespace(zf, namespace="ns")
        result = zf.read("test")
        self.assertEqual(b"||c|c", result)

    def test_zip_inject_namespace_namespaced_org(self):
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr(
            "___NAMESPACE___test",
            "%%%NAMESPACE%%%|%%%NAMESPACED_ORG%%%|%%%NAMESPACE_OR_C%%%|%%%NAMESPACED_ORG_OR_C%%%",
        )

        zf = utils.zip_inject_namespace(
            zf, namespace="ns", managed=True, namespaced_org=True
        )
        result = zf.read("ns__test")
        self.assertEqual(b"ns__|ns__|ns|ns", result)

    def test_zip_inject_namespace__skips_binary(self):
        contents = b"\x9c%%%NAMESPACE%%%"
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("test", contents)

        zf = utils.zip_inject_namespace(
            zf, namespace="ns", managed=True, namespaced_org=True
        )
        result = zf.read("test")
        self.assertEqual(contents, result)

    def test_zip_strip_namespace(self):
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("ns__test", "ns__test ns:test")

        zf = utils.zip_strip_namespace(zf, "ns")
        result = zf.read("test")
        self.assertEqual(b"test c:test", result)

    def test_zip_strip_namespace__skips_binary(self):
        contents = b"\x9cns__"
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("test", contents)

        zf = utils.zip_strip_namespace(zf, "ns")
        result = zf.read("test")
        self.assertEqual(contents, result)

    def test_zip_strip_namespace_logs(self):
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("ns__test", "ns__test ns:test")

        logger = mock.Mock()
        zf = utils.zip_strip_namespace(zf, "ns", logger=logger)
        logger.info.assert_called_once()

    def test_zip_tokenize_namespace(self):
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("ns__test", "ns__test ns:test")

        zf = utils.zip_tokenize_namespace(zf, "ns")
        result = zf.read("___NAMESPACE___test")
        self.assertEqual(b"%%%NAMESPACE%%%test %%%NAMESPACE_OR_C%%%test", result)

    def test_zip_tokenize_namespace__skips_binary(self):
        contents = b"\x9cns__"
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("test", contents)

        zf = utils.zip_tokenize_namespace(zf, "ns")
        result = zf.read("test")
        self.assertEqual(contents, result)

    def test_zip_tokenize_namespace_no_namespace(self):
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("test", "")
        result = utils.zip_tokenize_namespace(zf, "")
        self.assertIs(zf, result)

    def test_zip_clean_metaxml(self):
        logger = mock.Mock()
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr(
            "classes/test-meta.xml",
            '<?xml version="1.0" ?>'
            '<root xmlns="http://soap.sforce.com/2006/04/metadata">'
            "<packageVersions>text</packageVersions></root>",
        )
        zf.writestr("test", "")
        zf.writestr("other/test-meta.xml", "")

        zf = utils.zip_clean_metaxml(zf, logger=logger)
        result = zf.read("classes/test-meta.xml")
        self.assertNotIn(b"packageVersions", result)
        self.assertIn("other/test-meta.xml", zf.namelist())

    def test_zip_clean_metaxml__skips_binary(self):
        logger = mock.Mock()
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("classes/test-meta.xml", b"\x9c")
        zf.writestr("test", "")
        zf.writestr("other/test-meta.xml", "")

        zf = utils.zip_clean_metaxml(zf, logger=logger)
        self.assertIn("classes/test-meta.xml", zf.namelist())

    def test_zip_clean_metaxml__handles_nonascii(self):
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("classes/test-meta.xml", b"<root>\xc3\xb1</root>")

        zf = utils.zip_clean_metaxml(zf)
        self.assertIn(b"<root>\xc3\xb1</root>", zf.read("classes/test-meta.xml"))

    def test_doc_task(self):
        task_config = TaskConfig(
            {
                "class_path": "cumulusci.tests.test_utils.FunTestTask",
                "options": {"color": "black"},
            }
        )
        result = utils.doc_task("command", task_config)
        self.assertEqual(
            """command
==========================================

**Description:** None

**Class::** cumulusci.tests.test_utils.FunTestTask

extra docs

Options:
------------------------------------------

* **flavor** *(required)*: What flavor
* **color**: What color **Default: black**""",
            result,
        )

    def test_package_xml_from_dict(self):
        items = {"ApexClass": ["TestClass"]}
        result = utils.package_xml_from_dict(
            items, api_version="43.0", package_name="TestPackage"
        )
        self.assertEqual(
            """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>TestPackage</fullName>
    <types>
        <members>TestClass</members>
        <name>ApexClass</name>
    </types>
    <version>43.0</version>
</Package>""",
            result,
        )

    def test_cd__no_path(self):
        cwd = os.getcwd()
        with utils.cd(None):
            self.assertEqual(cwd, os.getcwd())

    def test_in_directory(self):
        cwd = os.getcwd()
        self.assertTrue(utils.in_directory(".", cwd))
        self.assertFalse(utils.in_directory("..", cwd))

    def test_parse_api_datetime__good(self):
        good_str = "2018-08-07T16:00:56.000+0000"
        dt = utils.parse_api_datetime(good_str)
        self.assertAlmostEqual(
            dt, datetime(2018, 8, 7, 16, 0, 56), delta=timedelta(seconds=1)
        )

    def test_parse_api_datetime__bad(self):
        bad_str = "2018-08-07T16:00:56.000-20000"
        with self.assertRaises(AssertionError):
            dt = utils.parse_api_datetime(bad_str)

    def test_log_progress(self):
        logger = mock.Mock()
        for x in utils.log_progress(range(3), logger, batch_size=1):
            pass
        self.assertEqual(4, logger.info.call_count)


class FunTestTask(BaseTask):
    """For testing doc_task"""

    task_options = OrderedDict(
        (
            ("flavor", {"description": "What flavor", "required": True}),
            ("color", {"description": "What color"}),
        )
    )
    task_docs = "extra docs"
