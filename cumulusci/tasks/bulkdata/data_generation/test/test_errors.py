from io import StringIO
import unittest

from cumulusci.tasks.bulkdata.data_generation.generate_from_yaml import _generate
from cumulusci.tasks.bulkdata.data_generation.data_generator import (
    DataGenSyntaxError,
    DataGenNameError,
)

yaml1 = """                             #1
- object: A                             #2
  count: <<abcd()>>                     #3
  fields:                               #4
    A: What a wonderful life            #5
    X: Y                                #6
    """

yaml2 = """- object: B                  #1
  count: <<expr)>                       #2
  fields:                               #3
    A: What a wonderful life            #4
    X: Y                                #5
"""


class TestLineNumbers(unittest.TestCase):
    def test_name_error(self):
        with self.assertRaises(DataGenNameError) as e:
            _generate(StringIO(yaml1), 1, {}, None, None)
        print(e.exception)
        assert str(e.exception)[-2:] == ":3"

    def test_syntax_error(self):
        with self.assertRaises(DataGenSyntaxError) as e:
            _generate(StringIO(yaml2), 1, {}, None, None)
        assert str(e.exception)[-2:] == ":2"
