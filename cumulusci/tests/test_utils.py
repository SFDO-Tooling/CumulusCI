import unittest
import zipfile

from cumulusci.tests.util import create_source_files
from cumulusci.tests.util import create_zip_file
from cumulusci.utils import zip_clean_metaxml


class TestZipCleanMetaXml(unittest.TestCase):

    def setUp(self):
        self.path = create_source_files()
        self.f_zip = create_zip_file(self.path)

    def tearDown(self):
        self.f_zip.close()

    def test_zip_clean_metaxml_1(self):
        zip = zipfile.ZipFile(self.f_zip)
        zip_cleaned = zip_clean_metaxml(zip)
        zip.close()
