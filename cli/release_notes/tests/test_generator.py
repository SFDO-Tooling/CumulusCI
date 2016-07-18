import os
import unittest

from release_notes.generator import BaseReleaseNotesGenerator
from release_notes.generator import StaticReleaseNotesGenerator
from release_notes.generator import DirectoryReleaseNotesGenerator
from release_notes.generator import GithubReleaseNotesGenerator
from release_notes.parser import BaseChangeNotesParser

__location__ = os.path.split(os.path.realpath(__file__))[0]


class DummyParser(BaseChangeNotesParser):

    def parse(self, change_note):
        pass

    def _render(self):
        return 'dummy parser output'.format(self.title)


class TestBaseReleaseNotesGenerator(unittest.TestCase):

    def test_render_no_parsers(self):
        release_notes = BaseReleaseNotesGenerator()
        content = release_notes.render()
        self.assertEqual(content, '')

    def test_render_dummy_parsers(self):
        release_notes = BaseReleaseNotesGenerator()
        release_notes.parsers.append(DummyParser('Dummy 1'))
        release_notes.parsers.append(DummyParser('Dummy 2'))
        expected = u'# Dummy 1\r\n\r\ndummy parser output\r\n\r\n' +\
                   u'# Dummy 2\r\n\r\ndummy parser output'
        self.assertEqual(release_notes.render(), expected)


class TestStaticReleaseNotesGenerator(unittest.TestCase):

    def test_init_parser(self):
        release_notes = StaticReleaseNotesGenerator([])
        assert len(release_notes.parsers) == 3


class TestDirectoryReleaseNotesGenerator(unittest.TestCase):

    def test_init_parser(self):
        release_notes = DirectoryReleaseNotesGenerator('change_notes')
        assert len(release_notes.parsers) == 3

    def test_full_content(self):
        change_notes_dir = os.path.join(
            __location__,
            'change_notes',
            'full',
        )
        release_notes = DirectoryReleaseNotesGenerator(
            change_notes_dir,
        )

        content = release_notes()
        expected = "# Critical Changes\r\n\r\n* This will break everything!\r\n\r\n# Changes\r\n\r\nHere's something I did. It was really cool\r\nOh yeah I did something else too!\r\n\r\n# Issues Closed\r\n\r\n#2345\r\n#6236"
        print expected
        print '-------------------------------------'
        print content

        self.assertEquals(content, expected)


class TestGithubReleaseNotesGenerator(unittest.TestCase):

    def setUp(self):
        self.current_tag = 'prod/1.4'
        self.last_tag = 'prod/1.3'
        self.github_info = {
            'github_owner': 'TestOwner',
            'github_repo': 'TestRepo',
            'github_username': 'TestUser',
            'github_password': 'TestPass',
        }

    def test_init_without_last_tag(self):
        github_info = self.github_info.copy()
        generator = GithubReleaseNotesGenerator(github_info, self.current_tag)
        self.assertEquals(generator.github_info, github_info)
        self.assertEquals(generator.current_tag, self.current_tag)
        self.assertEquals(generator.last_tag, None)
        self.assertEquals(generator.change_notes.current_tag, self.current_tag)
        self.assertEquals(generator.change_notes._last_tag, None)

    def test_init_without_last_tag(self):
        github_info = self.github_info.copy()
        generator = GithubReleaseNotesGenerator(
            github_info, self.current_tag, self.last_tag)
        self.assertEquals(generator.github_info, github_info)
        self.assertEquals(generator.current_tag, self.current_tag)
        self.assertEquals(generator.last_tag, self.last_tag)
        self.assertEquals(generator.change_notes.current_tag, self.current_tag)
        self.assertEquals(generator.change_notes._last_tag, self.last_tag)
