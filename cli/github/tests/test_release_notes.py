import httplib
import os
import shutil
import tempfile
import unittest

import requests
import responses

from github.release_notes import BaseReleaseNotesGenerator
from github.release_notes import StaticReleaseNotesGenerator
from github.release_notes import DirectoryReleaseNotesGenerator
from github.release_notes import BaseChangeNotesParser
from github.release_notes import IssuesParser
from github.release_notes import GithubIssuesParser
from github.release_notes import ChangeNotesLinesParser

from github.release_notes import BaseChangeNotesProvider
from github.release_notes import StaticChangeNotesProvider
from github.release_notes import DirectoryChangeNotesProvider
from github.release_notes import GithubChangeNotesProvider

from github.release_notes import GithubApiNotFoundError

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


class TestIssuesParser(unittest.TestCase):

    def test_issue_numbers(self):
        start_line = '# Issues'
        change_note = '{}\r\nfix #2\r\nfix #3\r\nfix #5\r\n'.format(start_line)
        parser = IssuesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2, 3, 5])

    def test_issue_numbers_and_other_numbers(self):
        start_line = '# Issues'
        change_note = '{}\r\nfixes #2 but not # 3 or 5'.format(start_line)
        parser = IssuesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2])

    def test_multiple_issue_numbers_per_line(self):
        start_line = '# Issues'
        change_note = '{}\r\nfix #2 also does fix #3 and fix #5\r\n'.format(
            start_line)
        parser = IssuesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2, 3, 5])


class TestGithubIssuesParser(unittest.TestCase):

    def test_issue_numbers(self):
        start_line = '# Issues'
        change_note = '{}\r\nFixes #2, Closed #3 and Resolve #5'.format(
            start_line)
        parser = GithubIssuesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2, 3, 5])

    def test_issue_numbers_and_other_numbers(self):
        start_line = '# Issues'
        change_note = '{}\r\nFixes #2 but not #5'.format(
            start_line)
        parser = GithubIssuesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2])

    def test_no_issue_numbers(self):
        start_line = '# Issues'
        change_note = '{}\r\n#2 and #3 are fixed by this change'.format(
            start_line)
        parser = GithubIssuesParser(None, None, start_line)
        parser.parse(change_note)
        self.assertEqual(parser.content, [])


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
        provider = StaticChangeNotesProvider('test', ['abc', 'd', 'e'])
        assert list(provider()) == ['abc', 'd', 'e']


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


class TestGithubChangeNotesProvider(unittest.TestCase):

    def setUp(self):
        # Set up the mock release_tag lookup response
        self.repo_api_url = 'https://api.github.com/repos/TestOwner/TestRepo'
        # Tag that does not exist
        self.invalid_tag = 'prod/1.4'
        # The current production release
        self.current_tag = 'prod/1.3'
        # The previous production release with no change notes vs 1.3
        self.last_tag = 'prod/1.2'
        # The second previous production release with one change note vs 1.3
        self.last2_tag = 'prod/1.1'
        # The third previous production release with three change notes vs 1.3
        self.last3_tag = 'prod/1.0'

        self.current_tag_sha = 'abcdefchijklmnopqrstuvwxyz0123456789ABCD'
        self.last_tag_sha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcd'

        self.github_info = {
            'github_owner': 'TestOwner',
            'github_repo': 'TestRepo',
            'github_username': 'TestUser',
            'github_password': 'TestPass',
        }

    def create_generator(self):
        generator = BaseReleaseNotesGenerator()
        generator.github_info = self.github_info.copy()
        return generator

    @responses.activate
    def test_invalid_current_tag(self):
        api_url = '{}/git/refs/tags/{}'.format(
            self.repo_api_url, self.invalid_tag)
        expected_response = {
            'message': 'Not Found',
            'documentation_url': 'https://developer.github.com/v3'
        }

        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
            status=httplib.NOT_FOUND,
        )

        generator = self.create_generator()
        provider = GithubChangeNotesProvider(generator, self.invalid_tag)
        with self.assertRaises(GithubApiNotFoundError):
            provider.current_tag_info

    def _get_expected_tag_ref(self, tag, sha):
        return {
            'ref': 'refs/tags/{}'.format(tag),
            'url': 'https://api.github.com/repos/TestOwner/TestRepo/git/refs/tags/{}'.format(tag),
            'object': {
                'type': 'tags',
                'sha': sha,
                'url': 'https://api.github.com/repos/TestOwner/TestRepo/git/tags/{}'.format(sha),
            }
        }

    def _get_expected_tag(self, tag, sha, tag_date=None):
        if not tag_date:
            tag_date = '2014-11-07T22:01:45Z'

        return {
            'tag': tag,
            'sha': sha,
            'url': 'https://api.github.com/repos/TestOwner/TestRepo/git/tags/{}'.format(sha),
            'message': 'message',
            'tagger': {
                'name': 'Test User',
                'email': 'testuser@mailinator.com',
                'date': tag_date,
            },
            'object': {
                'type': 'commit',
                'sha': sha,
                'url': 'https://api.github.com/repos/TestOwner/TestRepo/git/commits/{}'.format(sha),
            },
        }

    @responses.activate
    def test_current_tag_without_last(self):

        # Mock the current tag ref
        api_url = '{}/git/refs/tags/{}'.format(
            self.repo_api_url, self.current_tag)
        expected_response_current_tag_ref = self._get_expected_tag_ref(
            self.current_tag, self.current_tag_sha)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_current_tag_ref,
        )

        # Mock the current tag
        api_url = '{}/git/tags/{}'.format(self.repo_api_url,
                                          self.current_tag_sha)
        expected_response_current_tag = self._get_expected_tag(
            self.current_tag, self.current_tag_sha)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_current_tag,
        )

        # Mock the last tag ref
        api_url = '{}/git/refs/tags/{}'.format(
            self.repo_api_url, self.last_tag)
        expected_response_last_tag_ref = self._get_expected_tag_ref(
            self.last_tag, self.last_tag_sha)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_last_tag_ref,
        )

        # Mock the last tag
        api_url = '{}/git/tags/{}'.format(self.repo_api_url, self.last_tag_sha)
        expected_response_last_tag = self._get_expected_tag(
            self.last_tag, self.last_tag_sha)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_last_tag,
        )

        # Mock the list all tags call
        api_url = '{}/git/refs/tags/prod/'.format(self.repo_api_url)
        expected_response_list_tag_refs = [
            expected_response_current_tag_ref,
            expected_response_last_tag_ref,
            self._get_expected_tag_ref(self.last2_tag, 'last2_tag_sha'),
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_list_tag_refs,
        )

        generator = self.create_generator()
        provider = GithubChangeNotesProvider(generator, self.current_tag)

        self.assertEquals(provider.current_tag_info[
                          'ref'], expected_response_current_tag_ref)
        self.assertEquals(provider.current_tag_info[
                          'tag'], expected_response_current_tag)
        self.assertEquals(provider.last_tag_info[
                          'ref'], expected_response_last_tag_ref)
        self.assertEquals(provider.last_tag_info[
                          'tag'], expected_response_last_tag)

    @responses.activate
    def test_current_tag_without_last_no_last_found(self):
        pass

    @responses.activate
    def test_no_pull_requests_in_repo(self):
        pass

    @responses.activate
    def test_no_pull_requests_in_range(self):
        pass

    @responses.activate
    def test_one_pull_request_in_range(self):
        pass

    @responses.activate
    def test_multiple_pull_requests_in_range(self):
        pass
