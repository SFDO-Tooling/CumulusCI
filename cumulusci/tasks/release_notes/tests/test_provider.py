from datetime import datetime
from datetime import timedelta
import httplib
import os
import shutil
import tempfile
import unittest

import requests
import responses

from cumulusci.tasks.release_notes.generator import GithubReleaseNotesGenerator
from cumulusci.tasks.release_notes.provider import BaseChangeNotesProvider
from cumulusci.tasks.release_notes.provider import StaticChangeNotesProvider
from cumulusci.tasks.release_notes.provider import DirectoryChangeNotesProvider
from cumulusci.tasks.release_notes.provider import GithubChangeNotesProvider
from cumulusci.tasks.release_notes.exceptions import GithubApiNotFoundError
from cumulusci.tasks.release_notes.exceptions import LastReleaseTagNotFoundError
from cumulusci.tasks.release_notes.tests.util_github_api import GithubApiTestMixin

__location__ = os.path.split(os.path.realpath(__file__))[0]
date_format = '%Y-%m-%dT%H:%M:%SZ'


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
        self.current_tag_commit_sha = self._random_sha()
        self.current_tag_commit_date = datetime.now()
        self.last_tag_sha = self._random_sha()
        self.last_tag_commit_sha = self._random_sha()
        self.last_tag_commit_date = datetime.now() - timedelta(days=1)
        self.last2_tag_sha = self._random_sha()

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

    def _mock_current_tag(self):
        api_url = '{}/git/tags/{}'.format(self.repo_api_url,
                                          self.current_tag_sha)
        expected_response = self._get_expected_tag(
            self.current_tag,
            self.current_tag_sha,
            self.current_tag_commit_sha,
            self.current_tag_commit_date,
        )
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
        )
        return expected_response

    def _mock_current_tag_commit(self):
        api_url = '{}/git/commits/{}'.format(self.repo_api_url,
            self.current_tag_commit_sha)
        expected_response = {
            'author': {
                'date': datetime.strftime(self.current_tag_commit_date, date_format),
            },
            'sha': self.current_tag_commit_sha,
        }
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
        )

    def _mock_current_tag_ref(self):
        api_url = '{}/git/refs/tags/{}'.format(
            self.repo_api_url, self.current_tag)
        expected_response_current_tag_ref = self._get_expected_tag_ref(
            self.current_tag, self.current_tag_sha)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_current_tag_ref,
        )

    def _mock_invalid_tag(self):
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

    def _mock_last_tag(self):
        api_url = '{}/git/tags/{}'.format(self.repo_api_url, self.last_tag_sha)
        expected_response = self._get_expected_tag(
            self.last_tag,
            self.last_tag_sha,
            self.last_tag_commit_sha,
            self.last_tag_commit_date,
        )
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
        )
        return expected_response

    def _mock_last_tag_commit(self):
        api_url = '{}/git/commits/{}'.format(self.repo_api_url,
            self.last_tag_commit_sha)
        expected_response = {
            'author': {
                'date': datetime.strftime(self.last_tag_commit_date, date_format),
            },
            'sha': self.last_tag_commit_sha,
        }
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
        )

    def _mock_last_tag_ref(self):
        api_url = '{}/git/refs/tags/{}'.format(
            self.repo_api_url, self.last_tag)
        expected_response_last_tag_ref = self._get_expected_tag_ref(
            self.last_tag, self.last_tag_sha)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response_last_tag_ref,
        )

    def _mock_list_pull_requests_one_in_range(self):
        api_url = '{}/pulls'.format(self.repo_api_url)
        expected_response = [
            self._get_expected_pull_request(1, 101, 'pull 1',
                datetime.now() - timedelta(seconds=60)),
            self._get_expected_pull_request(2, 102, 'pull 2',
                datetime.now() - timedelta(days=4)),
            self._get_expected_pull_request(3, 103, 'pull 3',
                datetime.now() - timedelta(days=5)),
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
        )

    def _mock_list_pull_requests_multiple_in_range(self):
        api_url = '{}/pulls'.format(self.repo_api_url)
        expected_response = [
            self._get_expected_pull_request(1, 101, 'pull 1',
                datetime.now() - timedelta(seconds=60)),
            self._get_expected_pull_request(2, 102, 'pull 2',
                datetime.now() - timedelta(seconds=90)),
            self._get_expected_pull_request(3, 103, 'pull 3',
                datetime.now() - timedelta(seconds=120)),
            self._get_expected_pull_request(4, 104, 'pull 4',
                datetime.now() - timedelta(days=4)),
            self._get_expected_pull_request(5, 105, 'pull 5',
                datetime.now() - timedelta(days=5)),
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
        )

    def _mock_list_tags_multiple(self):
        api_url = '{}/git/refs/tags/prod/'.format(self.repo_api_url)
        expected_response = [
            self._get_expected_tag_ref(self.current_tag, self.current_tag_sha),
            self._get_expected_tag_ref(self.last_tag, self.last_tag_sha),
            self._get_expected_tag_ref(self.last2_tag, self.last2_tag_sha),
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
        )

    def _mock_list_tags_single(self):
        api_url = '{}/git/refs/tags/prod/'.format(self.repo_api_url)
        expected_response = [
            self._get_expected_tag_ref(self.current_tag, self.current_tag_sha),
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
        )

    @responses.activate
    def test_invalid_current_tag(self):
        self._mock_invalid_tag()
        generator = self._create_generator(self.invalid_tag)
        provider = GithubChangeNotesProvider(generator, self.invalid_tag)
        with self.assertRaises(GithubApiNotFoundError):
            provider.current_tag_info

    @responses.activate
    def test_current_tag_without_last(self):
        self._mock_current_tag_ref()
        current_tag = self._mock_current_tag()
        self._mock_current_tag_commit()
        self._mock_last_tag_ref()
        last_tag = self._mock_last_tag()
        self._mock_last_tag_commit()
        self._mock_list_tags_multiple()

        generator = self._create_generator(self.current_tag)
        provider = GithubChangeNotesProvider(generator, self.current_tag)

        self.assertEqual(provider.current_tag_info['ref'],
            self._get_expected_tag_ref(self.current_tag, self.current_tag_sha))
        self.assertEqual(provider.current_tag_info['tag'], current_tag)
        self.assertEqual(provider.last_tag_info['ref'],
            self._get_expected_tag_ref(self.last_tag, self.last_tag_sha))
        self.assertEqual(provider.last_tag_info['tag'], last_tag)

    @responses.activate
    def test_current_tag_without_last_no_last_found(self):
        self._mock_current_tag_ref()
        self._mock_current_tag()
        self._mock_current_tag_commit()
        self._mock_list_tags_single()

        generator = self._create_generator(self.current_tag)
        provider = GithubChangeNotesProvider(generator, self.current_tag)

        self.assertEqual(provider.last_tag, None)
        self.assertEqual(provider.last_tag_info, None)

    @responses.activate
    def test_no_pull_requests_in_repo(self):
        # Mock the tag calls
        self._mock_current_tag_ref()
        self._mock_current_tag()
        self._mock_current_tag_commit()
        self._mock_last_tag_ref()
        self._mock_last_tag()
        self._mock_last_tag_commit()

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
        self._mock_current_tag_ref()
        self._mock_current_tag()
        self._mock_current_tag_commit()
        self._mock_last_tag_ref()
        self._mock_last_tag()
        self._mock_last_tag_commit()

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
        self._mock_current_tag_ref()
        self._mock_current_tag()
        self._mock_current_tag_commit()
        self._mock_last_tag_ref()
        self._mock_last_tag()
        self._mock_last_tag_commit()
        self._mock_list_pull_requests_one_in_range()

        generator = self._create_generator(self.current_tag, self.last_tag)
        provider = GithubChangeNotesProvider(
            generator, self.current_tag, self.last_tag)
        self.assertEqual(list(provider()), ['pull 1'])

    @responses.activate
    def test_multiple_pull_requests_in_range(self):
        # Mock the tag calls
        self._mock_current_tag_ref()
        self._mock_current_tag()
        self._mock_current_tag_commit()
        self._mock_last_tag_ref()
        self._mock_last_tag()
        self._mock_last_tag_commit()
        self._mock_list_pull_requests_multiple_in_range()

        generator = self._create_generator(self.current_tag, self.last_tag)
        provider = GithubChangeNotesProvider(
            generator, self.current_tag, self.last_tag)
        self.assertEqual(list(provider()), ['pull 1', 'pull 2', 'pull 3'])
