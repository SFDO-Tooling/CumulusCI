import os
import shutil
import tempfile
import unittest
from github.release_notes import BaseReleaseNotesGenerator
from github.release_notes import StaticReleaseNotesGenerator
from github.release_notes import DirectoryReleaseNotesGenerator

from github.release_notes import BaseChangeNotesParser
from github.release_notes import ChangeNotesLinesParser

from github.release_notes import BaseChangeNotesProvider
from github.release_notes import StaticChangeNotesProvider
from github.release_notes import DirectoryChangeNotesProvider
from github.release_notes import GithubChangeNotesProvider

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

class DummyParser(BaseChangeNotesParser):

    def parse(self, change_note):
        pass

    def _render(self):
        return 'dummy parser output\r\n'


class TestBaseReleaseNotesGenerator(unittest.TestCase):

    def test_render_no_parsers(self):
        release_notes = BaseReleaseNotesGenerator()
        content = release_notes.render()
        self.assertEqual(content, '')

    def test_render_dummy_parsers(self):
        release_notes = BaseReleaseNotesGenerator()
        release_notes.parsers.append(DummyParser('Dummy 1'))
        release_notes.parsers.append(DummyParser('Dummy 2'))
        self.assertEqual(release_notes.render(), (
                         u'# Dummy 1\r\ndummy parser output\r\n\r\n' +
                         u'# Dummy 2\r\ndummy parser output\r\n'))


class TestStaticReleaseNotesGenerator(unittest.TestCase):

    def test_init_parser(self):
        release_notes = StaticReleaseNotesGenerator([])
        assert len(release_notes.parsers) == 3

class TestDirectoryReleaseNotesGenerator(unittest.TestCase):

    def test_init_parser(self):
        release_notes = DirectoryReleaseNotesGenerator('change_notes')
        assert len(release_notes.parsers) == 3

class TestBaseChangeNotesParser(unittest.TestCase):
    pass

class TestChangeNotesLinesParser(unittest.TestCase):

    def test_init_empty_start_line(self):
        self.assertRaises(ValueError, ChangeNotesLinesParser, None, None, '')

    def test_parse_no_start_line(self):
        start_line = '# Start Line'
        change_note = 'foo\r\nbar\r\n'
        parser = ChangeNotesLinesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, [])

    def test_parse_start_line_no_content(self):
        start_line = '# Start Line'
        change_note = '{}\r\n\r\n'.format(start_line)
        parser = ChangeNotesLinesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, [])

    def test_parse_start_line_no_end_line(self):
        start_line = '# Start Line'
        change_note = '{}\r\nfoo\r\nbar'.format(start_line)
        parser = ChangeNotesLinesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, ['foo', 'bar'])

    def test_parse_start_line_no_content_no_end_line(self):
        start_line = '# Start Line'
        change_note = start_line
        parser = ChangeNotesLinesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, [])

    def test_parse_multiple_start_lines_without_end_lines(self):
        start_line = '# Start Line'
        change_note = '{0}\r\nfoo\r\n{0}\r\nbar\r\n'.format(start_line)
        parser = ChangeNotesLinesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, ['foo', 'bar'])

    def test_parse_multiple_start_lines_with_end_lines(self):
        start_line = '# Start Line'
        change_note = '{0}\r\nfoo\r\n\r\n{0}\r\nbar\r\n\r\n'.format(start_line)
        parser = ChangeNotesLinesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, ['foo', 'bar'])

    def test_render_no_content(self):
        start_line = '# Start Line'
        parser = ChangeNotesLinesParser(None, None, start_line)
        self.assertEqual(parser.render(), None)

    def test_render_one_content(self):
        title = 'Title'
        start_line = '# Start Line'
        parser = ChangeNotesLinesParser(None, title, start_line)
        content = ['foo']
        parser.content = content
        self.assertEqual(parser.render(),
                         '# {}\r\n{}'.format(title, content[0]))

    def test_render_multiple_content(self):
        title = 'Title'
        start_line = '# Start Line'
        parser = ChangeNotesLinesParser(None, title, start_line)
        content = ['foo', 'bar']
        parser.content = content
        self.assertEqual(parser.render(),
                         '# {}\r\n{}'.format(title, '\r\n'.join(content)))


class TestGithubIssuesParser(unittest.TestCase):
    pass

class TestBaseChangeNotesProvider(unittest.TestCase):

    def test_init(self):
        provider = BaseChangeNotesProvider('test')
        assert provider.release_notes_generator == 'test'

    def test_call_raises_notimplemented(self):
        provider = BaseChangeNotesProvider('test')
        self.assertRaises(NotImplementedError, provider.__call__)
       
class TestStaticChangeNotesProvider(unittest.TestCase):
    
    def test_empty_list(self): 
        provider = StaticChangeNotesProvider('test', [])
        assert list(provider()) == []

    def test_single_item_list(self): 
        provider = StaticChangeNotesProvider('test', ['abc'])
        assert list(provider()) == ['abc']

    def test_multi_item_list(self): 
        provider = StaticChangeNotesProvider('test', ['abc','d','e'])
        assert list(provider()) == ['abc','d','e']

class TestDirectoryChangeNotesProvider(unittest.TestCase):

    def get_empty_dir(self):
        tempdir = tempfile.mkdtemp()
        return os.path.join(tempdir)

    def get_dir_content(self, path):
        dir_content = [] 
        for item in os.listdir(path):
            item_path = '{}/{}'.format(path, item)
            dir_content.append(open(item_path, 'r').read())
        return dir_content

    def test_empty_directory(self): 
        directory = self.get_empty_dir()
        provider = DirectoryChangeNotesProvider('test', directory)
        dir_content = self.get_dir_content(directory)
        assert list(provider()) == dir_content    
        shutil.rmtree(directory)
        

    def test_single_item_directory(self): 
        directory = '{}/change_notes/single/'.format(__location__)
        provider = DirectoryChangeNotesProvider('test', directory)
        dir_content = self.get_dir_content(directory)
        assert list(provider()) == dir_content

    def test_multi_item_directory(self): 
        directory = '{}/change_notes/multi/'.format(__location__)
        provider = DirectoryChangeNotesProvider('test', directory)
        dir_content = self.get_dir_content(directory)
        assert list(provider()) == dir_content
