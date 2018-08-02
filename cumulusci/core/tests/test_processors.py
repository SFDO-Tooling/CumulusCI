from __future__ import absolute_import

import io
import os
import base64
import zipfile
import unittest

import nose
from cumulusci.core import __location__
from ..processors import CallablePackageZipBuilder, FilePackageZipBuilder


class FakeZipBuilder(CallablePackageZipBuilder):
    def _populate_zip(self):
        self._write_file('test.txt', 'this is a test file')


class TestPackageZipBuilders(unittest.TestCase):
    @nose.tools.raises(NotImplementedError)
    def test_raises_error(self):
        builder = CallablePackageZipBuilder()
        builder()

    def test_returns_b64encoded_zip(self):
        builder = FakeZipBuilder()
        decodedzip = base64.b64decode(builder())
        zipf = zipfile.ZipFile(io.BytesIO(decodedzip), 'r')
        self.assertIsNone(zipf.testzip())  # testzip returns None


class TestFilePackageZipBuilder(unittest.TestCase):
    src_dir = os.path.join(__location__, 'tests/mdapisrc/ccitest')
    with open(os.path.join(src_dir, 'tabs/SampleObject__c.tab'), 'r') as f:
        tab_contents = f.read()

    def test_builds_package(self):
        builder = FilePackageZipBuilder(self.src_dir)
        decodedzip = base64.b64decode(builder.encode_zip())
        zipf = zipfile.ZipFile(io.BytesIO(decodedzip), 'r')
        self.assertIsNone(zipf.testzip())  # testzip returns None

    def test_package_has_members(self):
        builder = FilePackageZipBuilder(self.src_dir)
        builder.encode_zip()
        zipf = builder.zip
        self.assertIn('tabs/SampleObject__c.tab', zipf.namelist())

    def test_package_members_are_equal(self):
        builder = FilePackageZipBuilder(self.src_dir)
        decodedzip = base64.b64decode(builder.encode_zip())
        zipf = zipfile.ZipFile(io.BytesIO(decodedzip), 'r')
        self.assertEqual(zipf.read('tabs/SampleObject__c.tab'), self.tab_contents)
