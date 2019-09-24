# coding=utf-8
import re
import mock
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
from cumulusci.tasks.release_notes.generator import markdown_link_to_pr
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
]


class DummyParser(BaseChangeNotesParser):
    def parse(self, change_note):
        pass

    def _render(self):
        return "dummy parser output".format(self.title)


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
            self.gh, github_info, PARSER_CONFIG, self.current_tag
        )
        self.assertEqual(generator.github_info, github_info)
        self.assertEqual(generator.current_tag, self.current_tag)
        self.assertEqual(generator.last_tag, None)
        self.assertEqual(generator.change_notes.current_tag, self.current_tag)
        self.assertEqual(generator.change_notes._last_tag, None)

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
    def test_mark_down_link_to_pr(self):
        self.mock_util.mock_get_repo()
        self.mock_util.mock_pull_request(
            1, body="# Changes\r\n\r\nfoo", title="Title 1"
        )
        generator = self._create_generator()
        pr = generator.get_repo().pull_request(1)
        actual_link = markdown_link_to_pr(pr)
        expected_link = "{} [[PR{}]({})]".format(pr.title, pr.number, pr.html_url)
        self.assertEquals(expected_link, actual_link)

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
        self.assertEquals(3, len(content))
        self.assertEquals("\n# Pull requests with no release notes", content[0])
        self.assertEquals(
            "\n* {} [[PR{}]({})]".format(pr1.title, pr1.number, pr1.html_url),
            content[1],
        )
        self.assertEquals(
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
        self.assertEquals(4, len(split_content))
        self.assertEquals("new content", split_content[0])
        self.assertEquals("\n# Pull requests with no release notes", split_content[1])
        self.assertEquals(
            "\n* Pull Request #{0} [[PR{0}]({1})]".format(pr1.number, pr1.html_url),
            split_content[2],
        )
        self.assertEquals(
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
        self.assertEquals(2, len(generator.empty_change_notes))
        self.assertEquals(2, generator.empty_change_notes[0].number)
        self.assertEquals(3, generator.empty_change_notes[1].number)

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
            "master_branch": "master",
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
        assert 6 == len(generator.parsers)
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

        mock_util.mock_pulls(pulls=[pr1_json, pr2_json, pr3_json])

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

    @responses.activate
    def test_aggregate_child_change_notes__update_fails(
        self, generator, mock_util, gh_api
    ):
        self.init_github()
        pr_json = self._get_expected_pull_request(1, 1, "Small dev note")
        mock_util.mock_pulls(pulls=[pr_json])

        parent_body = "Body of Parent PR"
        pr_json = self._get_expected_pull_request(3, 3, parent_body)
        parent_pr = ShortPullRequest(pr_json, gh_api)
        parent_pr.head.label = "repo:some-other-branch"

        parent_pr.update = mock.Mock(return_value=False)
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

    @responses.activate
    def test_update_unaggregated_pr_header__no_pull_request_found(
        self, generator, mock_util, repo, gh_api
    ):
        self.init_github()
        mock_util.mock_pulls(pulls=[])
        mock_util.mock_pulls(pulls=self._get_expected_pull_requests(3))
        pr_to_update = ShortPullRequest(
            self._get_expected_pull_request(20, 20, "Body here"), gh_api
        )

        # No pull requests are returned
        with pytest.raises(CumulusCIException):
            generator.update_unaggregated_pr_header(pr_to_update, "branch_name")

        # More than one pull request returned
        with pytest.raises(CumulusCIException):
            generator.update_unaggregated_pr_header(pr_to_update, "branch_name")

    @responses.activate
    def test_update_unaggregated_pr_header(self, generator, mock_util, repo, gh_api):
        def pr_update_callback(request):
            """Method to intercept the call to
            github3.pull.ShortPullRequest.update()"""
            payload = json.loads(request.body)
            resp_body = self._get_expected_pull_request(1, 1, payload["body"])
            return (200, {}, json.dumps(resp_body))

        pr_num = 1
        pr_update_api_url = "https://github.com/TestOwner/TestRepo/pulls/{}".format(
            pr_num
        )
        # Mock endpoint that updates the pull request
        responses.add_callback(
            responses.PATCH,
            pr_update_api_url,
            callback=pr_update_callback,
            content_type="application/json",
        )

        BODY = "Sample Body"
        TEST_BRANCH_NAME = "feature/long__child-branch"
        self.init_github()
        pr_to_update = ShortPullRequest(
            self._get_expected_pull_request(pr_num, pr_num, BODY), gh_api
        )

        NEW_PR_BODY = "* Random Dev Note\r\n\r\n# Changes\r\n\r\n* Now more code!"
        unaggregated_pr_json = self._get_expected_pull_request(2, 2, NEW_PR_BODY)
        unaggregated_pr_json["base"]["ref"] = "feature/long"
        # Mock pull request for retrieval by branch name
        mock_util.mock_pulls(pulls=[unaggregated_pr_json])

        generator.update_unaggregated_pr_header(pr_to_update, TEST_BRANCH_NAME)
        pr_link = markdown_link_to_pr(ShortPullRequest(unaggregated_pr_json, gh_api))
        assert generator.UNAGGREGATED_SECTION_HEADER in pr_to_update.body
        assert pr_link in pr_to_update.body

        # Ensure we don't duplicate things
        generator.update_unaggregated_pr_header(pr_to_update, TEST_BRANCH_NAME)
        num_headers = len(
            re.findall(generator.UNAGGREGATED_SECTION_HEADER, pr_to_update.body)
        )
        assert 1 == num_headers
        num_pr_links = len(
            re.findall(
                r"Pull Request #2 \[\[PR2\]\(https://github.com/TestOwner/TestRepo/pulls/2\)\]",
                pr_to_update.body,
            )
        )
        assert 1 == num_pr_links
