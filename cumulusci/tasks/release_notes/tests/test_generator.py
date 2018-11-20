# coding=utf-8

import datetime
import json
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
        self.mock_util.mock_list_releases(tag=tag, body="foo\n# Changes\nbar")
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
        self.mock_util.mock_list_releases(tag=tag, body="# Changes\nbar\n# Foo\nfoo")
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
        self.mock_util.mock_list_releases(
            tag=tag, body="foo\n# Changes\nbar\n# Foo\nfoo"
        )
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
        self.mock_util.mock_list_releases(
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
        self.mock_util.mock_list_releases(
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
        self.mock_util.mock_list_releases(tag=tag, body="foo")
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
        generator._get_release = mock.Mock(return_value=None)
        with self.assertRaises(CumulusCIException):
            result = generator()
