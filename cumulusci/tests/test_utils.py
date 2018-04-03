import unittest

from cumulusci.tests.util import create_source_files
from cumulusci.tests.util import create_zip_file
from cumulusci.utils import zip_clean_metaxml


class TestZipCleanMetaXml(unittest.TestCase):

    def setUp(self):
        self.path = create_source_files()
        self.zip = create_zip_file(self.path)

    def tearDown(self):
        self.zip.close()

    def test_zip_clean_metaxml_1(self):
        zip_cleaned = zip_clean_metaxml(self.zip)
