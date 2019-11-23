from io import StringIO
import unittest
from unittest import mock


from cumulusci.tasks.bulkdata.data_generation.generate_from_yaml import generate

structured_values_with_templates = """  #1
- object: A                             #2
  fields:                               #4
    A: 5                                 #5
    B:                                  #5
     random_number:                      #6
       min: <<this.A - 3>>                      #7
       max: <<this.A + 3>>                      #7
"""


write_row_path = "cumulusci.tasks.bulkdata.data_generation.output_streams.DebugOutputStream.write_row"


class TestStructuredValues(unittest.TestCase):
    @mock.patch(write_row_path)
    def test_structured_values(self, write_row):
        generate(StringIO(structured_values_with_templates), 1, {}, None)
        assert isinstance(write_row.mock_calls[0][1][1]["B"], int)
        assert 2 <= write_row.mock_calls[0][1][1]["B"] <= 8
