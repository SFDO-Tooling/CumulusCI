import unittest
from io import StringIO
from tempfile import NamedTemporaryFile

from cumulusci.tasks.bulkdata.data_generation.output_streams import SqlOutputStream


from cumulusci.tasks.bulkdata.data_generation.data_generator import generate


class TestParseGenerator(unittest.TestCase):
    def test_extra_options_warning(self):
        yaml = """
        - object: foo
          count: 15
          fields:
            a: b
            c: 3
        """
        flush_count = 0
        real_flush = None

        def mock_flush():
            nonlocal flush_count
            flush_count += 1
            real_flush()

        with NamedTemporaryFile() as f:
            output_stream = SqlOutputStream.from_url(f"sqlite:///{f.name}", None)
            output_stream.flush_limit = 3
            real_flush = output_stream.flush
            output_stream.flush = mock_flush
            generate(StringIO(yaml), 1, {}, output_stream, None)
            assert flush_count == 3
            output_stream.close()
