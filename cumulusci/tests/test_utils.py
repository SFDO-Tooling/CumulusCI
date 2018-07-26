import unittest

import mock

class TestMetadataXmlElementParser(unittest.TestCase):

    @mock.patch('xml.etree.ElementTree.parse')
    def test_elementtree_parse_file(self, mock_parse):
        from xml.etree.ElementTree import ParseError
        from cumulusci.tasks.metadata.package import elementtree_parse_file

        err = ParseError()
        err.msg = 'it broke'
        err.lineno = 1
        mock_parse.side_effect = err
        try:
            elementtree_parse_file('test_file')
        except ParseError as err:
            self.assertEqual(str(err), 'it broke (test_file, line 1)')
        else:
            self.fail('Expected ParseError')
