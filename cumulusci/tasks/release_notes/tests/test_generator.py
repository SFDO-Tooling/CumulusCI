# coding=utf-8
from unittest import mock
import os
import json
import pytest
import unittest
import responses

from github3.repos.repo import Repository
from github3.pulls import ShortPullRequest

from cumulusci.core.github import get_github_api
from cumulusci.tests.util import create_project_config
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tasks.release_notes.tests.utils import MockUtil
from cumulusci.tasks.release_notes.parser import BaseChangeNotesParser
from cumulusci.tasks.release_notes.generator import render_empty_pr_section
from cumulusci.tasks.release_notes.generator import (
    BaseReleaseNotesGenerator,
    StaticReleaseNotesGenerator,
    GithubReleaseNotesGenerator,
    DirectoryReleaseNotesGenerator,
    ParentPullRequestNotesGenerator,
)

__location__ = os.path.split(os.path.realpath(__file__))[0]

PARSER_CONFIG = [
    {
        "class_path": "cumulusci.tasks.release_notes.parser.GithubLinesParser",
        "title": "Critical Changes",
    },
    {
        "class_path": "cumulusci.tasks.release_notes.parser.GithubLinesParser",
        "title": "Changes",
    },
    {
        "class_path": "cumulusci.tasks.release_notes.parser.GithubIssuesParser",
        "title": "Issues Closed",
    },
    {"class_path": None},
]


class DummyParser(BaseChangeNotesParser):
    def parse(self, change_note):
        pass

    def _render(self):
        return "dummy parser output"


class TestBaseReleaseNotesGenerator(unittest.TestCase):
    def test_render_no_parsers(self):
        release_notes = BaseReleaseNotesGenerator()
        content = release_notes.render()
        self.assertEqual(content, "")

    def test_render_dummy_parsers(self):
        release_notes = BaseReleaseNotesGenerator()
        release_notes.parsers.append(DummyParser("Dummy 1"))
        release_notes.parsers.append(DummyParser("Dummy 2"))
        expected = (
            u"# Dummy 1\r\n\r\ndummy parser output\r\n\r\n"
            + u"# Dummy 2\r\n\r\ndummy parser output"
        )
        self.assertEqual(release_notes.render(), expected)


class TestStaticReleaseNotesGenerator(unittest.TestCase):
    def test_init_parser(self):
        release_notes = StaticReleaseNotesGenerator([])
        assert len(release_notes.parsers) == 3


class TestDirectoryReleaseNotesGenerator(unittest.TestCase):
    def test_init_parser(self):
        release_notes = DirectoryReleaseNotesGenerator("change_notes")
        assert len(release_notes.parsers) == 3

    def test_full_content(self):
        change_notes_dir = os.path.join(__location__, "change_notes", "full")
        release_notes = DirectoryReleaseNotesGenerator(change_notes_dir)

        content = release_notes()
        expected = "# Critical Changes\r\n\r\n* This will break everything!\r\n\r\n# Changes\r\n\r\nHere's something I did. It was really cool\r\nOh yeah I did something else too!\r\n\r\n# Issues Closed\r\n\r\n#2345\r\n#6236"
        print(expected)
        print("-------------------------------------")
        print(content)

        self.assertEqual(content, expected)


class TestGithubReleaseNotesGenerator(unittest.TestCase, GithubApiTestMixin):
    def setUp(self):
        self.current_tag = "prod/1.4"
        self.last_tag = "prod/1.3"
        self.github_info = {
            "github_owner": "TestOwner",
            "github_repo": "TestRepo",
            "github_username": "TestUser",
            "github_password": "TestPass",
        }
        self.gh = get_github_api("TestUser", "TestPass")
        self.mock_util = MockUtil("TestOwner", "TestRepo")

    @responses.activate
    def test_init_without_last_tag(self):
        github_info = self.github_info.copy()
        self.mock_util.mock_get_repo()
        generator = GithubReleaseNotesGenerator(
            self.gh, github_info, PARSER_CONFIG, self.current_tag, version_id="04t"
        )
        self.assertEqual(generator.github_info, github_info)
        self.assertEqual(generator.current_tag, self.current_tag)
        self.assertEqual(generator.last_tag, None)
        self.assertEqual(generator.change_notes.current_tag, self.current_tag)
        self.assertEqual(generator.change_notes._last_tag, None)
        self.assertEqual("04t", generator.version_id)

    @responses.activate
    def test_init_with_last_tag(self):
        github_info = self.github_info.copy()
        self.mock_util.mock_get_repo()
        generator = GithubReleaseNotesGenerator(
            self.gh, github_info, PARSER_CONFIG, self.current_tag, self.last_tag
        )
        self.assertEqual(generator.github_info, github_info)
        self.assertEqual(generator.current_tag, self.current_tag)
        self.assertEqual(generator.last_tag, self.last_tag)
        self.assertEqual(generator.change_notes.current_tag, self.current_tag)
        self.assertEqual(generator.change_notes._last_tag, self.last_tag)

    @responses.activate
    def test_render_empty_pr_section(self):
        self.mock_util.mock_get_repo()
        self.mock_util.mock_pull_request(1, body="# Changes\r\n\r\nfoo")
        self.mock_util.mock_pull_request(2, body="# Changes\r\n\r\nbar")
        generator = self._create_generator()
        repo = generator.get_repo()
        pr1 = repo.pull_request(1)
        pr2 = repo.pull_request(2)
        generator.empty_change_notes.extend([pr1, pr2])
        content = render_empty_pr_section(generator.empty_change_notes)
        self.assertEqual(3, len(content))
        self.assertEqual("\n# Pull requests with no release notes", content[0])
        self.assertEqual(
            "\n* {} [[PR{}]({})]".format(pr1.title, pr1.number, pr1.html_url),
            content[1],
        )
        self.assertEqual(
            "\n* {} [[PR{}]({})]".format(pr2.title, pr2.number, pr2.html_url),
            content[2],
        )

    @responses.activate
    def test_update_content_with_empty_release_body(self):
        self.mock_util.mock_get_repo()
        self.mock_util.mock_pull_request(88, body="Just a small note.")
        self.mock_util.mock_pull_request(89, body="")
        generator = self._create_generator()
        repo = generator.get_repo()
        pr1 = repo.pull_request(88)
        pr2 = repo.pull_request(89)
        generator.include_empty_pull_requests = True
        generator.empty_change_notes = [pr1, pr2]
        release = mock.Mock(body=None)
        content = generator._update_release_content(release, "new content")

        split_content = content.split("\r\n")
        self.assertEqual(4, len(split_content))
        self.assertEqual("new content", split_content[0])
        self.assertEqual("\n# Pull requests with no release notes", split_content[1])
        self.assertEqual(
            "\n* Pull Request #{0} [[PR{0}]({1})]".format(pr1.number, pr1.html_url),
            split_content[2],
        )
        self.assertEqual(
            "\n* Pull Request #{0} [[PR{0}]({1})]".format(pr2.number, pr2.html_url),
            split_content[3],
        )

    @responses.activate
    def test_detect_empty_change_note(self):
        self.mock_util.mock_get_repo()
        self.mock_util.mock_pull_request(1, body="# Changes\r\n\r\nfoo")
        self.mock_util.mock_pull_request(2, body="Nothing under headers we track")
        self.mock_util.mock_pull_request(3, body="")
        generator = self._create_generator()
        repo = generator.get_repo()
        pr1 = repo.pull_request(1)
        pr2 = repo.pull_request(2)
        pr3 = repo.pull_request(3)

        generator._parse_change_note(pr1)
        generator._parse_change_note(pr2)
        generator._parse_change_note(pr3)

        # PR1 is "non-empty" second two are "empty"
        self.assertEqual(2, len(generator.empty_change_notes))
        self.assertEqual(2, generator.empty_change_notes[0].number)
        self.assertEqual(3, generator.empty_change_notes[1].number)

    def _create_generator(self):
        generator = GithubReleaseNotesGenerator(
            self.gh, self.github_info.copy(), PARSER_CONFIG, self.current_tag
        )
        return generator


class TestPublishingGithubReleaseNotesGenerator(unittest.TestCase, GithubApiTestMixin):
    def setUp(self):
        self.init_github()
        self.github_info = {
            "github_owner": "TestOwner",
            "github_repo": "TestRepo",
            "github_username": "TestUser",
            "github_password": "TestPass",
            "default_branch": "main",
        }
        self.gh = get_github_api("TestUser", "TestPass")
        self.mock_util = MockUtil("TestOwner", "TestRepo")

    @responses.activate
    def test_publish_update_unicode(self):
        tag = "prod/1.4"
        note = u"“Unicode quotes”"
        expected_release_body = u"# Changes\r\n\r\n{}".format(note)
        # mock GitHub API responses
        self.mock_util.mock_get_repo()
        # create generator instance
        generator = self._create_generator(tag)
        # inject content into Changes parser
        generator.parsers[1].content.append(note)
        # render content
        content = generator.render()
        # verify
        self.assertEqual(len(responses.calls._calls), 1)
        self.assertEqual(content, expected_release_body)

    @responses.activate
    def test_publish_update_no_body(self):
        tag = "prod/1.4"
        expected_release_body = "# Changes\r\n\r\nfoo"
        # mock GitHub API responses
        self.mock_util.mock_get_repo()
        # create generator
        generator = self._create_generator(tag)
        # inject content into Changes parser
        generator.parsers[1].content.append("foo")
        # render content
        content = generator.render()
        # verify
        self.assertEqual(len(responses.calls._calls), 1)
        self.assertEqual(content, expected_release_body)

    @responses.activate
    def test_publish_update_content_before(self):
        tag = "prod/1.4"
        expected_release_body = "foo\r\n# Changes\r\n\r\nbaz"
        # mock GitHub API responses
        self.mock_util.mock_get_repo()
        self.mock_util.mock_get_release(tag=tag, body="foo\n# Changes\nbar")
        # create generator
        generator = self._create_generator(tag)
        # inject content into parser
        generator.parsers[1].content.append("baz")
        # render and update content
        content = generator.render()
        release = generator._get_release()
        content = generator._update_release_content(release, content)
        # verify
        self.assertEqual(len(responses.calls._calls), 3)
        self.assertEqual(content, expected_release_body)

    @responses.activate
    def test_publish_update_content_after(self):
        tag = "prod/1.4"
        expected_release_body = "# Changes\r\n\r\nbaz\r\n\r\n# Foo\r\nfoo"
        # mock GitHub API responses
        self.mock_util.mock_get_repo()
        self.mock_util.mock_get_release(tag=tag, body="# Changes\nbar\n# Foo\nfoo")
        # create generator
        generator = self._create_generator(tag)
        # inject content into parser
        generator.parsers[1].content.append("baz")
        # render and update content
        content = generator.render()
        release = generator._get_release()
        content = generator._update_release_content(release, content)
        # verify
        self.assertEqual(len(responses.calls._calls), 3)
        self.assertEqual(content, expected_release_body)

    @responses.activate
    def test_publish_update_content_before_and_after(self):
        tag = "prod/1.4"
        expected_release_body = "foo\r\n# Changes\r\n\r\nbaz\r\n\r\n# Foo\r\nfoo"
        # mock GitHub API responses
        self.mock_util.mock_get_repo()
        self.mock_util.mock_get_release(tag=tag, body="foo\n# Changes\nbar\n# Foo\nfoo")
        # create generator
        generator = self._create_generator(tag)
        # inject content into parser
        generator.parsers[1].content.append("baz")
        # render and update content
        content = generator.render()
        release = generator._get_release()
        content = generator._update_release_content(release, content)
        # verify
        self.assertEqual(len(responses.calls._calls), 3)
        self.assertEqual(content, expected_release_body)

    @responses.activate
    def test_publish_update_content_between(self):
        tag = "prod/1.4"
        expected_release_body = (
            "# Critical Changes\r\n\r\nfaz\r\n\r\n"
            "# Foo\r\nfoo\r\n# Changes\r\n\r\nfiz"
        )
        # mock GitHub API responses
        self.mock_util.mock_get_repo()
        self.mock_util.mock_get_release(
            tag=tag, body="# Critical Changes\nbar\n# Foo\nfoo\n# Changes\nbiz"
        )
        # create generator
        generator = self._create_generator(tag)
        # inject content into parser
        generator.parsers[0].content.append("faz")
        generator.parsers[1].content.append("fiz")
        # render and update content
        content = generator.render()
        release = generator._get_release()
        content = generator._update_release_content(release, content)
        # verify
        self.assertEqual(len(responses.calls._calls), 3)
        self.assertEqual(content, expected_release_body)

    @responses.activate
    def test_publish_update_content_before_after_and_between(self):
        tag = "prod/1.4"
        expected_release_body = (
            "goo\r\n# Critical Changes\r\n\r\nfaz\r\n\r\n"
            "# Foo\r\nfoo\r\n# Changes\r\n\r\nfiz\r\n\r\n# Zoo\r\nzoo"
        )
        # mock GitHub API responses
        self.mock_util.mock_get_repo()
        self.mock_util.mock_get_release(
            tag=tag,
            body=(
                "goo\n# Critical Changes\nbar\n"
                "# Foo\nfoo\n# Changes\nbiz\n# Zoo\nzoo"
            ),
        )
        # create generator
        generator = self._create_generator(tag)
        # inject content into parser
        generator.parsers[0].content.append("faz")
        generator.parsers[1].content.append("fiz")
        # render and update content
        content = generator.render()
        release = generator._get_release()
        content = generator._update_release_content(release, content)
        # verify
        self.assertEqual(len(responses.calls._calls), 3)
        self.assertEqual(content, expected_release_body)

    @responses.activate
    def test_publish_update_content_missing(self):
        tag = "prod/1.4"
        expected_release_body = "foo\r\n# Changes\r\n\r\nbaz\r\n"
        # mock GitHub API responses
        self.mock_util.mock_get_repo()
        self.mock_util.mock_get_release(tag=tag, body="foo")
        # create generator
        generator = self._create_generator(tag)
        # inject content into parser
        generator.parsers[1].content.append("baz")
        # render and update content
        content = generator.render()
        release = generator._get_release()
        content = generator._update_release_content(release, content)
        # verify
        self.assertEqual(len(responses.calls._calls), 3)
        self.assertEqual(content, expected_release_body)

    def _create_generator(self, current_tag, last_tag=None):
        generator = GithubReleaseNotesGenerator(
            self.gh, self.github_info.copy(), PARSER_CONFIG, current_tag, last_tag
        )
        return generator

    @mock.patch(
        "cumulusci.tasks.release_notes.generator.BaseReleaseNotesGenerator.__call__"
    )
    @responses.activate
    def test_call(self, base_generator):
        self.mock_util.mock_get_repo()
        generator = self._create_generator("prod/1.0")
        generator.do_publish = True
        release = mock.Mock()
        generator._get_release = mock.Mock(return_value=release)
        generator._update_release_content = mock.Mock(
            return_value=mock.sentinel.content
        )
        result = generator()
        self.assertIs(mock.sentinel.content, result)
        base_generator.assert_called_once()
        release.edit.assert_called_once()

    @responses.activate
    def test_call__no_release(self):
        self.mock_util.mock_get_repo()
        generator = self._create_generator("prod/1.0")
        responses.add(
            method=responses.GET,
            url="{}/releases/tags/prod/1.0".format(self.mock_util.repo_url),
            status=404,
        )
        with self.assertRaises(CumulusCIException):
            generator()


class TestParentPullRequestNotesGenerator(GithubApiTestMixin):
    @pytest.fixture
    def mock_util(self):
        return MockUtil("TestOwner", "TestRepo")

    @pytest.fixture
    def repo(self, gh_api):
        repo_json = self._get_expected_repo("TestOwner", "TestRepo")
        return Repository(repo_json, gh_api)

    @pytest.fixture
    def generator(self, gh_api):
        repo_json = GithubApiTestMixin()._get_expected_repo("TestOwner", "TestRepo")
        repo = Repository(repo_json, gh_api)
        return ParentPullRequestNotesGenerator(gh_api, repo, create_project_config())

    def test_init_parsers(self, generator):
        assert 7 == len(generator.parsers)
        assert generator.parsers[-1]._in_section

    @responses.activate
    def test_aggregate_child_change_notes(self, generator, mock_util, gh_api):
        def request_intercept(request):
            """Assert that the body is correct"""
            body = json.loads(request.body)["body"]
            assert (
                "# Critical Changes\r\n\r\n* Everything works now. [[PR2](https://github.com/TestOwner/TestRepo/pulls/2)]"
                in body
            )
            assert (
                "# Changes\r\n\r\n* Now, more code! [[PR1](https://github.com/TestOwner/TestRepo/pulls/1)]"
                in body
            )
            assert "# Notes From Child PRs\r\n\r\n* Dev note 1 [[PR1](https://github.com/TestOwner/TestRepo/pulls/1)]\r\n\r\n* Dev note 2 [[PR2](https://github.com/TestOwner/TestRepo/pulls/2)]"
            assert (
                "# Pull requests with no release notes\r\n\n* Pull Request #4 [[PR4](https://github.com/TestOwner/TestRepo/pulls/4)]"
                in body
            )
            assert "Should not be in body" not in body
            return (200, {}, json.dumps(self._get_expected_pull_request(3, 3, body)))

        self.init_github()
        dev_note1 = "* Dev note 1"
        dev_note2 = "* Dev note 2"
        change = "# Changes\r\n\r\n* Now, more code!"
        critical_change = "# Critical Changes\r\n\r\n* Everything works now."

        pr1_json = self._get_expected_pull_request(1, 1, dev_note1 + "\r\n" + change)
        pr2_json = self._get_expected_pull_request(
            2, 2, dev_note2 + "\r\n" + critical_change
        )
        pr3_json = self._get_expected_pull_request(4, 4, None)
        pr3_json["body"] = ""

        pr4_json = self._get_expected_pull_request(5, 5, "Should not be in body")
        # simulate merge from main back into parent
        pr4_json["head"]["ref"] = "main"

        mock_util.mock_pulls(pulls=[pr1_json, pr2_json, pr3_json, pr4_json])

        pr_json = self._get_expected_pull_request(3, 3, "Body of Parent PR")
        parent_pr = ShortPullRequest(pr_json, gh_api)
        parent_pr.head.label = "repo:some-other-branch"

        responses.add_callback(
            responses.PATCH,
            "https://github.com/TestOwner/TestRepo/pulls/3",  # TODO: again, no '.api' needed in this endpoint?
            callback=request_intercept,
            content_type="application/json",
        )
        generator.aggregate_child_change_notes(parent_pr)

    @mock.patch(
        "cumulusci.tasks.release_notes.generator.get_pull_requests_with_base_branch"
    )
    def test_aggregate_child_change_notes__update_fails(
        self, get_pull, generator, mock_util, gh_api
    ):
        self.init_github()
        parent_body = "Body of Parent PR"
        pr_json = self._get_expected_pull_request(3, 3, parent_body)
        parent_pr = ShortPullRequest(pr_json, gh_api)
        parent_pr.merged_at = "Yesterday"
        parent_pr.head.label = "repo:some-other-branch"
        parent_pr.update = mock.Mock(return_value=False)

        get_pull.return_value = [parent_pr]
        with pytest.raises(CumulusCIException):
            generator.aggregate_child_change_notes(parent_pr)
        parent_pr.update.assert_called_once()

    @responses.activate
    def test_aggregate_child_change_notes__empty_change_note(
        self, generator, mock_util, gh_api
    ):
        self.init_github()
        mock_util.mock_pulls()  # no change notes returned

        parent_pr = ShortPullRequest(
            self._get_expected_pull_request(3, 3, "Body"), gh_api
        )
        parent_pr.head.label = "repo:branch"

        generator.aggregate_child_change_notes(parent_pr)
        assert 0 == len(generator.change_notes)
