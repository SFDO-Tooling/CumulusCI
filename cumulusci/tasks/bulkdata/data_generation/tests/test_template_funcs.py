from io import StringIO
import unittest
from unittest import mock

from cumulusci.tasks.bulkdata.data_generation.data_generator import generate

write_row_path = "cumulusci.tasks.bulkdata.data_generation.output_streams.DebugOutputStream.write_row"


def row_values(write_row_mock, index, value):
    return write_row_mock.mock_calls[index][1][1][value]


class TestTemplateFuncs(unittest.TestCase):
    @mock.patch(write_row_path)
    def test_inline_reference(self, write_row_mock):
        yaml = """
        - object: Person
          nickname: daddy
          count: 1
        - object: Person
          count: 1
          fields:
            parent: <<reference(daddy).id>>
            parent2: <<reference(daddy)>>
        """
        generate(StringIO(yaml), 1, {}, None)
        assert write_row_mock.mock_calls == [
            mock.call("Person", {"id": 1}),
            mock.call("Person", {"id": 2, "parent": 1, "parent2": mock.ANY}),
        ]

    @mock.patch(write_row_path)
    def test_unweighted_random_choice_object(self, write_row):
        yaml = """
        - object : A
          fields:
            b:
                random_choice:
                  - object: C
                  - object: D
                  - object: E
        """
        generate(StringIO(yaml), 1, {}, None)
        assert len(write_row.mock_calls) == 2, write_row.mock_calls
        # TODO CHECK MORE

    @mock.patch(write_row_path)
    def test_weighted_random_choice(self, write_row):
        yaml = """
        - object : A
          fields:
            b:
                random_choice:
                    - choice:
                        probability: 50%
                        pick:
                        - object: C
                    - choice:
                        probability: 40%
                        pick:
                        - object: D
                    - choice:
                        probability: 10%
                        pick:
                        - object: E
        """
        generate(StringIO(yaml), 1, {}, None)
        assert len(write_row.mock_calls) == 2, write_row.mock_calls
        # TODO CHECK MORE

    @mock.patch(write_row_path)
    def test_conditional(self, write_row):
        yaml = """
        - object : A
          fields:
            a: False
            b: True
            c: True
            d:
                if:
                    - choice:
                        when: <<a>>
                        pick: AAA
                    - choice:
                        when: <<b>>
                        pick: BBB
                    - choice:
                        when: <<c>>
                        pick: CCC
        """
        generate(StringIO(yaml), 1, {}, None)
        assert write_row.mock_calls == [
            mock.call("A", {"id": 1, "a": False, "b": True, "c": True, "d": "BBB"})
        ]

    # @mock.patch(write_row_path)
    # def test_weighted_random_choice_objects(self, write_row):
    #     yaml = """
    #     - object : A
    #       fields:
    #         b:
    #             random_choice:
    #                 -
    #                   - 50%
    #                   - object: C
    #                 -
    #                   - 40%:
    #                   - object: D
    #                 -
    #                   - 30%:
    #                   - object: E
    #     """
    #     generate(StringIO(yaml), 1, {}, None)
    #     assert len(write_row.mock_calls) == 2, write_row.mock_calls
    #     # TODO CHECK MORE


#
#     @mock.patch(write_row_path)
#     def test_counter(self, write_row_mock):
#         yaml = """
#         - object: Person
#           count: 3
#           fields:
#             unique_number:
#                 counter: Person
#         - object: Person
#           count: 2
#           fields:
#             unique_number:
#                 counter: Person
#         """
#         generate(StringIO(yaml), 1, {}, None)
#         unique_numbers = [
#             call[1]["unique_number"] for call in write_row_mock.mock_calls
#         ]
#         assert unique_numbers == (1, 2, 3, 4, 5)
