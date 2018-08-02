from __future__ import absolute_import

import io
import base64
import zipfile
import unittest

import nose

from ..processors import MetadataProcessor
from ..processors import CallablePackageZipBuilder

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
        zipf = zipfile.ZipFile(io.BytesIO(decodedzip),'r')
        self.assertIsNone(zipf.testzip()) # testzip returns None



class TestMetadataProcessor(unittest.TestCase):
    def test_bytefile(self):
        processor = MetadataProcessor('mdapisrc')
        #self.assertEqual(processor.path, 'mdapisc')
    