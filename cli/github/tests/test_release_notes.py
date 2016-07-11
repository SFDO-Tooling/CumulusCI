import unittest

class TestBaseReleaseNotesGenerator(unittest.TestCase):

    def test_add_content(self):
        from release_notes import ReleaseNotesGenerator

class TestReleaseNotesGenerator(unittest.TestCase):

    def test_init_parser(self):
        from release_notes import ReleaseNotesGenerator
        release_notes = ReleaseNotesGenerator()
        assert len(release_notes.parsers) == 3

if __name__ == '__main__':
    unittest.main()
