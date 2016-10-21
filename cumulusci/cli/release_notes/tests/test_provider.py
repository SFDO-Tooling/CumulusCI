from datetime import datetime
from datetime import timedelta
import httplib
import os
import shutil
import tempfile
import unittest

import requests
import responses

from cumulusci.cli.release_notes.generator import GithubReleaseNotesGenerator
from cumulusci.cli.release_notes.provider import BaseChangeNotesProvider
from cumulusci.cli.release_notes.provider import StaticChangeNotesProvider
from cumulusci.cli.release_notes.provider import DirectoryChangeNotesProvider
from cumulusci.cli.release_notes.provider import GithubChangeNotesProvider
from cumulusci.cli.release_notes.exceptions import GithubApiNotFoundError
from cumulusci.cli.release_notes.exceptions import LastReleaseTagNotFoundError
from cumulusci.cli.release_notes.tests.util_github_api import GithubApiTestMixin

__location__ = os.path.split(os.path.realpath(__file__))[0]


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


class TestGithubChangeNotesProvider(unittest.TestCase, GithubApiTestMixin):

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

        self.current_tag_sha = self._random_sha()
        self.last_tag_sha = self._random_sha()

        self.github_info = {
            'github_owner': 'TestOwner',
            'github_repo': 'TestRepo',
            'github_username': 'TestUser',
            'github_password': 'TestPass',
        }

    def _create_generator(self, current_tag, last_tag=None):
        generator = GithubReleaseNotesGenerator(
            self.github_info.copy(),
            current_tag,
            last_tag=last_tag
        )
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

        generator = self._create_generator(self.invalid_tag)
        provider = GithubChangeNotesProvider(generator, self.invalid_tag)
        with self.assertRaises(GithubApiNotFoundError):
            provider.current_tag_info

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

        generator = self._create_generator(self.current_tag)
        provider = GithubChangeNotesProvider(generator, self.current_tag)

        self.assertEqual(provider.current_tag_info['ref'],
                         expected_response_current_tag_ref)
        self.assertEqual(provider.current_tag_info['tag'],
                         expected_response_current_tag)
        self.assertEqual(provider.last_tag_info['ref'],
                         expected_response_last_tag_ref)
        self.assertEqual(provider.last_tag_info['tag'],
                         expected_response_last_tag)

    @responses.activate
    def test_current_tag_without_last_no_last_found(self):
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

        # Mock the list all tags call
        api_url = '{}/git/refs/tags/prod/'.format(self.repo_api_url)
        expected_response_list_tag_refs = [
            expected_response_current_tag_ref,
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_list_tag_refs,
        )
        generator = self._create_generator(self.current_tag)
        provider = GithubChangeNotesProvider(generator, self.current_tag)

        self.assertEqual(provider.last_tag, None)
        self.assertEqual(provider.last_tag_info, None)

    def _mock_pull_request_tags(self):
        # Mock the current tag ref
        api_url = '{}/git/refs/tags/{}'.format(
            self.repo_api_url,
            self.current_tag,
        )
        expected_response_current_tag_ref = self._get_expected_tag_ref(
            self.current_tag,
            self.current_tag_sha,
        )
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_current_tag_ref,
        )

        # Mock the current tag
        api_url = '{}/git/tags/{}'.format(
            self.repo_api_url,
            self.current_tag_sha,
        )
        expected_response_current_tag = self._get_expected_tag(
            self.current_tag,
            self.current_tag_sha,
            datetime.now(),
        )
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_current_tag,
        )

        # Mock the last tag ref
        api_url = '{}/git/refs/tags/{}'.format(
            self.repo_api_url,
            self.last_tag
        )
        expected_response_last_tag_ref = self._get_expected_tag_ref(
            self.last_tag,
            self.last_tag_sha,
        )
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_last_tag_ref,
        )

        # Mock the last tag
        api_url = '{}/git/tags/{}'.format(
            self.repo_api_url,
            self.last_tag_sha,
        )
        expected_response_last_tag = self._get_expected_tag(
            self.last_tag,
            self.last_tag_sha,
            datetime.now() - timedelta(days=1),
        )
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_last_tag,
        )

    @responses.activate
    def test_no_pull_requests_in_repo(self):
        # Mock the tag calls
        self._mock_pull_request_tags()

        # Mock the list all pull requests call
        api_url = '{}/pulls'.format(self.repo_api_url)
        expected_response_list_pull_requests = []
        responses.add(
            method=responses.GET,
            url=api_url,
            body=expected_response_list_pull_requests,
            content_type='application/json',
        )

        generator = self._create_generator(self.current_tag, self.last_tag)
        provider = GithubChangeNotesProvider(
            generator, self.current_tag, self.last_tag)
        self.assertEqual(list(provider()), [])

    @responses.activate
    def test_no_pull_requests_in_range(self):
        # Mock the tag calls
        self._mock_pull_request_tags()

        # Mock the list all pull requests call
        api_url = '{}/pulls'.format(self.repo_api_url)
        expected_pull_request_1 = self._get_expected_pull_request(
            pull_id=1,
            issue_number=101,
            body='pull 1',
            merged_date=datetime.now() - timedelta(days=2),
        )
        expected_response_list_pull_requests = [
            expected_pull_request_1,
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_list_pull_requests,
        )

        generator = self._create_generator(self.current_tag, self.last_tag)
        provider = GithubChangeNotesProvider(
            generator, self.current_tag, self.last_tag)
        self.assertEqual(list(provider()), [])

    @responses.activate
    def test_one_pull_request_in_range(self):
        # Mock the tag calls
        self._mock_pull_request_tags()

        # Mock the list all pull requests call
        api_url = '{}/pulls'.format(self.repo_api_url)
        expected_pull_request_1 = self._get_expected_pull_request(
            pull_id=1,
            issue_number=101,
            body='pull 1',
            merged_date=datetime.now() - timedelta(seconds=60),
        )
        expected_pull_request_2 = self._get_expected_pull_request(
            pull_id=2,
            issue_number=102,
            body='pull 2',
            merged_date=datetime.now() - timedelta(days=2),
        )
        expected_response_list_pull_requests = [
            expected_pull_request_1,
            expected_pull_request_2,
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_list_pull_requests,
        )

        generator = self._create_generator(self.current_tag, self.last_tag)
        provider = GithubChangeNotesProvider(
            generator, self.current_tag, self.last_tag)
        self.assertEqual(list(provider()), ['pull 1'])

    @responses.activate
    def test_multiple_pull_requests_in_range(self):
        # Mock the tag calls
        self._mock_pull_request_tags()

        # Mock the list all pull requests call
        api_url = '{}/pulls'.format(self.repo_api_url)
        expected_pull_request_1 = self._get_expected_pull_request(
            pull_id=1,
            issue_number=101,
            body='pull 1',
            merged_date=datetime.now() - timedelta(seconds=60),
        )
        expected_pull_request_2 = self._get_expected_pull_request(
            pull_id=2,
            issue_number=102,
            body='pull 2',
            merged_date=datetime.now() - timedelta(seconds=90),
        )
        expected_pull_request_3 = self._get_expected_pull_request(
            pull_id=3,
            issue_number=103,
            body='pull 3',
            merged_date=datetime.now() - timedelta(seconds=120),
        )
        expected_pull_request_4 = self._get_expected_pull_request(
            pull_id=4,
            issue_number=104,
            body='pull 4',
            merged_date=datetime.now() - timedelta(days=4),
        )
        expected_pull_request_5 = self._get_expected_pull_request(
            pull_id=5,
            issue_number=105,
            body='pull 5',
            merged_date=datetime.now() - timedelta(days=5),
        )
        expected_response_list_pull_requests = [
            expected_pull_request_1,
            expected_pull_request_2,
            expected_pull_request_3,
            expected_pull_request_4,
            expected_pull_request_5,
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_list_pull_requests,
        )

        generator = self._create_generator(self.current_tag, self.last_tag)
        provider = GithubChangeNotesProvider(
            generator, self.current_tag, self.last_tag)
        self.assertEqual(list(provider()), ['pull 1', 'pull 2', 'pull 3'])
