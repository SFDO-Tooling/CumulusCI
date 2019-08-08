# coding=utf-8

import mock
import os
import unittest

import responses

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.github import get_github_api
from cumulusci.tasks.release_notes.generator import BaseReleaseNotesGenerator
from cumulusci.tasks.release_notes.generator import StaticReleaseNotesGenerator
from cumulusci.tasks.release_notes.generator import DirectoryReleaseNotesGenerator
from cumulusci.tasks.release_notes.generator import GithubReleaseNotesGenerator
from cumulusci.tasks.release_notes.parser import BaseChangeNotesParser
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tasks.release_notes.tests.utils import MockUtil

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
        actual_link = generator._mark_down_link_to_pr(pr)
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
        content = generator._render_empty_pr_section()
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
