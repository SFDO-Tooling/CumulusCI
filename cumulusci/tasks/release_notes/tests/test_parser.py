import http.client
from unittest import mock
import unittest

import responses

from cumulusci.tasks.release_notes.exceptions import GithubIssuesError
from cumulusci.tasks.release_notes.generator import GithubReleaseNotesGenerator
from cumulusci.tasks.release_notes.parser import BaseChangeNotesParser
from cumulusci.tasks.release_notes.parser import ChangeNotesLinesParser
from cumulusci.tasks.release_notes.parser import GithubIssuesParser
from cumulusci.tasks.release_notes.parser import GithubLinesParser
from cumulusci.tasks.release_notes.parser import IssuesParser
from cumulusci.tasks.release_notes.parser import InstallLinkParser
from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.core.github import get_github_api
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tasks.release_notes.tests.utils import MockUtil

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


class TestBaseChangeNotesParser(unittest.TestCase):
    def test_parse(self):
        parser = BaseChangeNotesParser("Title")
        with self.assertRaises(NotImplementedError):
            parser.parse()

    def test_render(self):
        parser = BaseChangeNotesParser("Title")
        with self.assertRaises(NotImplementedError):
            parser.render()


class TestChangeNotesLinesParser(unittest.TestCase):
    def setUp(self):
        self.title = "Title"

    def test_parse_no_start_line(self):
        change_note = "foo\r\nbar\r\n"
        parser = ChangeNotesLinesParser(None, self.title)
        line_added = parser.parse(change_note)
        self.assertEqual(parser.content, [])
        self.assertFalse(line_added)

    def test_parse_start_line_no_content(self):
        change_note = "# {}\r\n\r\n".format(self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        line_added = parser.parse(change_note)
        self.assertEqual(parser.content, [])
        self.assertFalse(line_added)

    def test_parse_start_line_no_end_line(self):
        change_note = "# {}\r\nfoo\r\nbar".format(self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        line_added = parser.parse(change_note)
        self.assertEqual(parser.content, ["foo", "bar"])
        self.assertEqual(True, line_added)

    def test_parse_start_line_end_at_header(self):
        change_note = "# {}\r\nfoo\r\n# Another Header\r\nbar".format(self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        line_added = parser.parse(change_note)
        self.assertEqual(parser.content, ["foo"])
        self.assertTrue(line_added)

    def test_parse_start_line_no_content_no_end_line(self):
        change_note = "# {}".format(self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        line_added = parser.parse(change_note)
        self.assertEqual(parser.content, [])
        self.assertFalse(line_added)

    def test_parse_multiple_start_lines_without_end_lines(self):
        change_note = "# {0}\r\nfoo\r\n# {0}\r\nbar\r\n".format(self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        line_added = parser.parse(change_note)
        self.assertEqual(parser.content, ["foo", "bar"])
        self.assertTrue(line_added)

    def test_parse_multiple_start_lines_with_end_lines(self):
        change_note = "# {0}\r\nfoo\r\n\r\n# {0}\r\nbar\r\n\r\nincluded\r\n\r\n# not included".format(
            self.title
        )
        parser = ChangeNotesLinesParser(None, self.title)
        line_added = parser.parse(change_note)
        self.assertEqual(parser.content, ["foo", "bar", "included"])
        self.assertTrue(line_added)

    def test_parse_multi_level_indent(self):
        change_note = "# {0}\r\nfoo \r\n    bar  \r\n        baz \r\n".format(
            self.title
        )
        parser = ChangeNotesLinesParser(None, self.title)
        line_added = parser.parse(change_note)
        self.assertEqual(parser.content, ["foo", "    bar", "        baz"])
        self.assertTrue(line_added)

    def test_parse_subheading(self):
        change_note = "# {0}\r\n## Subheading\r\nfoo".format(self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        line_added = parser.parse(change_note)
        self.assertEqual([], parser.content)
        self.assertEqual({"Subheading": ["foo"]}, parser.h2)
        self.assertTrue(line_added)

    def test_parse_subheading_from_another_section(self):
        change_note = "## Subheading\r\n# {0}\r\nfoo".format(self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        line_added = parser.parse(change_note)
        self.assertEqual(["foo"], parser.content)
        self.assertEqual({}, parser.h2)
        self.assertTrue(line_added)

    def test_render_no_content(self):
        parser = ChangeNotesLinesParser(None, self.title)
        self.assertEqual(parser.render(), "")

    def test_render_one_content(self):
        parser = ChangeNotesLinesParser(None, self.title)
        content = ["foo"]
        parser.content = content
        self.assertEqual(
            parser.render(), "# {}\r\n\r\n{}".format(self.title, content[0])
        )

    def test_render_multiple_content(self):
        parser = ChangeNotesLinesParser(None, self.title)
        content = ["foo", "bar"]
        parser.content = content
        self.assertEqual(
            parser.render(), "# {}\r\n\r\n{}".format(self.title, "\r\n".join(content))
        )

    def test_render_subheadings(self):
        parser = ChangeNotesLinesParser(None, self.title)
        parser.h2 = {"Subheading": ["foo"]}
        self.assertEqual(
            parser.render(),
            "# {}\r\n\r\n\r\n## Subheading\r\n\r\nfoo".format(self.title),
        )


class TestGithubLinesParser(unittest.TestCase):
    def setUp(self):
        self.title = "Title"

    def test_parse(self):
        generator = mock.Mock(link_pr=True)
        parser = GithubLinesParser(generator, self.title)
        pr = mock.Mock(
            number=1, html_url="http://pr", body="# {}\r\n\r\nfoo".format(self.title)
        )
        parser.parse(pr)
        self.assertEqual(1, parser.pr_number)
        self.assertEqual("http://pr", parser.pr_url)
        self.assertEqual(["foo [[PR1](http://pr)]"], parser.content)

    def test_parse_empty_pull_request_body(self):
        generator = mock.Mock(link_pr=True)
        parser = GithubLinesParser(generator, self.title)
        pr = mock.Mock(number=1, html_url="http://pr", body=None)
        line_added = parser.parse(pr)
        assert not line_added


class TestIssuesParser(unittest.TestCase):
    def setUp(self):
        self.title = "Issues"

    def test_issue_numbers(self):
        change_note = "# {}\r\nfix #2\r\nfix #3\r\nfix #5\r\n".format(self.title)
        parser = IssuesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2, 3, 5])

    def test_issue_numbers_with_links(self):
        change_note = "# {}\r\nfix [#2](https://issue)\r\nfix [#3](http://issue)\r\nfix #5\r\n".format(
            self.title
        )
        parser = IssuesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2, 3, 5])

    def test_issue_numbers_and_other_numbers(self):
        change_note = "# {}\r\nfixes #2 but not # 3 or 5".format(self.title)
        parser = IssuesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2])

    def test_multiple_issue_numbers_per_line(self):
        change_note = "# {}\r\nfix #2 also does fix #3 and fix #5\r\n".format(
            self.title
        )
        parser = IssuesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2, 3, 5])

    def test_render(self):
        parser = IssuesParser(None, self.title)
        parser.content = ["1: foo"]
        self.assertEqual("# Issues\r\n\r\n#1: foo", parser.render())


class TestGithubIssuesParser(unittest.TestCase, GithubApiTestMixin):
    def setUp(self):
        self.init_github()
        self.gh = get_github_api("TestUser", "TestPass")
        self.title = "Issues"
        # Set up the mock release_tag lookup response
        self.issue_number_valid = 123
        self.issue_number_invalid = 456
        self.pr_number = 789
        self.pr_url = "https://github.com/{}/{}/pulls/{}".format(
            "TestOwner", "TestRepo", self.pr_number
        )
        self.mock_util = MockUtil("TestOwner", "TestRepo")

    @responses.activate
    def test_issue_numbers(self):
        self.mock_util.mock_get_repo()
        change_note = "# {}\r\nFixes #2, Closed #3 and Resolve #5".format(self.title)
        self.mock_util.mock_pull_request(self.pr_number, body=change_note)
        generator = self._create_generator()
        repo = generator.get_repo()
        pull_request = repo.pull_request(self.pr_number)
        parser = GithubIssuesParser(generator, self.title)
        parser.parse(pull_request)
        pr_url = "https://github.com/TestOwner/TestRepo/pulls/{}".format(self.pr_number)
        expected_content = self._create_expected_content([2, 3, 5], pr_url)
        self.assertEqual(parser.content, expected_content)

    @responses.activate
    def test_issue_numbers_and_other_numbers(self):
        self.mock_util.mock_get_repo()
        change_note = "# {}\r\nFixes #2 but not #5".format(self.title)
        self.mock_util.mock_pull_request(self.pr_number, body=change_note)
        generator = self._create_generator()
        repo = generator.get_repo()
        pull_request = repo.pull_request(self.pr_number)
        parser = GithubIssuesParser(generator, self.title)
        parser.parse(pull_request)
        pr_url = "https://github.com/TestOwner/TestRepo/pulls/{}".format(self.pr_number)
        expected_content = self._create_expected_content([2], pr_url)
        self.assertEqual(parser.content, expected_content)

    @responses.activate
    def test_no_issue_numbers(self):
        pr_number = 1
        self.mock_util.mock_get_repo()
        change_note = "# {}\r\n#2 and #3 are fixed by this change".format(self.title)
        self.mock_util.mock_pull_request(pr_number, body=change_note)
        generator = self._create_generator()
        repo = generator.get_repo()
        pull_request = repo.pull_request(pr_number)
        parser = GithubIssuesParser(generator, self.title)
        parser.parse(pull_request)
        self.assertEqual(parser.content, [])

    @responses.activate
    def test_render_issue_number_valid(self):
        api_url = "{}/issues/{}".format(self.repo_api_url, self.issue_number_valid)
        expected_response = self._get_expected_issue(self.issue_number_valid)
        self.mock_util.mock_get_repo()
        responses.add(method=responses.GET, url=api_url, json=expected_response)
        generator = self._create_generator()
        generator.link_pr = True
        parser = GithubIssuesParser(generator, self.title)
        parser.content = [
            {
                "issue_number": self.issue_number_valid,
                "pr_number": self.pr_number,
                "pr_url": self.pr_url,
            }
        ]
        expected_render = self._create_expected_render(
            self.issue_number_valid, expected_response["title"], True
        )
        self.assertEqual(parser.render(), expected_render)

    @responses.activate
    def test_render_issue_number_invalid(self):
        api_url = "{}/issues/{}".format(self.repo_api_url, self.issue_number_invalid)
        expected_response = self._get_expected_not_found()
        self.mock_util.mock_get_repo()
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
            status=http.client.NOT_FOUND,
        )
        generator = self._create_generator()
        parser = GithubIssuesParser(generator, self.title)
        parser.content = [
            {
                "issue_number": self.issue_number_invalid,
                "pr_number": self.pr_number,
                "pr_url": self.pr_url,
            }
        ]
        with self.assertRaises(GithubApiNotFoundError):
            parser.render()

    def test_init__issues_disabled(self):
        generator = mock.Mock(has_issues=False)
        with self.assertRaises(GithubIssuesError):
            GithubIssuesParser(generator, self.title)

    def _create_expected_content(self, issue_numbers, pr_url):
        y = []
        for n in issue_numbers:
            y.append({"issue_number": n, "pr_number": self.pr_number, "pr_url": pr_url})
        return y

    def _create_expected_render(self, issue_number, issue_title, link_pr):
        render = "# {}\r\n\r\n#{}: {}".format(self.title, issue_number, issue_title)
        if link_pr:
            render += " [[PR{}]({})]".format(self.pr_number, self.pr_url)
        return render

    def _create_generator(self):
        generator = GithubReleaseNotesGenerator(
            self.gh, self.github_info.copy(), PARSER_CONFIG, "release/1.1"
        )
        return generator


class TestCommentingGithubIssuesParser(unittest.TestCase, GithubApiTestMixin):
    def setUp(self):
        self.init_github()
        self.gh = get_github_api("TestUser", "TestPass")
        self.mock_util = MockUtil("TestOwner", "TestRepo")
        self.title = "Issues"
        self.issue_number_without_comments = 1
        self.issue_number_with_beta_comment = 2
        self.issue_number_without_beta_comment = 3
        self.issue_number_with_prod_comment = 4
        self.issue_number_without_prod_comment = 5
        self.pr_number = 6
        self.pr_url = "https://github.com/TestOwner/TestRepo/pulls/{}".format(
            self.pr_number
        )
        self.tag_prod = "release/1.2"
        self.tag_beta = "beta/1.2-Beta_3"
        self.tag_not_prod_or_beta = "foo"
        self.version_number_prod = "1.1"
        self.version_number_beta = "1.2 (Beta 3)"

    def _create_generator(self, tag):
        generator = GithubReleaseNotesGenerator(
            self.gh, self.github_info.copy(), PARSER_CONFIG, tag, publish=True
        )
        return generator

    @responses.activate
    def test_render_issue_without_comments(self):
        issue_number = self.issue_number_without_comments
        tag = self.tag_not_prod_or_beta
        self.mock_util.mock_get_repo()
        self.mock_util.mock_post_comment(issue_number)

        # Mock the issue
        api_url = "{}/issues/{}".format(self.repo_api_url, issue_number)
        expected_issue = self._get_expected_issue(issue_number)
        responses.add(method=responses.GET, url=api_url, json=expected_issue)

        # Mock the comments list
        api_url = "{}/issues/{}/comments".format(self.repo_api_url, issue_number)
        responses.add(
            method=responses.GET, url=api_url, json=[], content_type="application/json"
        )

        generator = self._create_generator(tag)
        parser = GithubIssuesParser(generator, self.title)
        parser.content = [
            {
                "issue_number": issue_number,
                "pr_number": self.pr_number,
                "pr_url": self.pr_url,
            }
        ]
        expected_render = self._create_expected_render(
            issue_number, expected_issue["title"], False
        )
        render = parser.render()
        self.assertEqual(render, expected_render)
        self.assertEqual(len(responses.calls._calls), 2)

    @responses.activate
    def test_render_issue_with_beta_comment(self):
        issue_number = self.issue_number_with_beta_comment
        tag = self.tag_beta
        self.mock_util.mock_get_repo()
        self.mock_util.mock_post_comment(issue_number)

        # Mock the issue
        api_url = "{}/issues/{}".format(self.repo_api_url, issue_number)
        expected_issue = self._get_expected_issue(issue_number)
        responses.add(method=responses.GET, url=api_url, json=expected_issue)

        # Mock the comments list
        api_url = "{}/issues/{}/comments".format(self.repo_api_url, issue_number)
        expected_comment_1 = self._get_expected_issue_comment(
            GithubIssuesParser.ISSUE_COMMENT["beta"]
        )
        expected_comments = [expected_comment_1]
        responses.add(method=responses.GET, url=api_url, json=expected_comments)

        generator = self._create_generator(tag)
        parser = GithubIssuesParser(generator, self.title)
        parser.content = [
            {
                "issue_number": issue_number,
                "pr_number": self.pr_number,
                "pr_url": self.pr_url,
            }
        ]
        expected_render = self._create_expected_render(
            issue_number, expected_issue["title"], False
        )
        render = parser.render()
        self.assertEqual(render, expected_render)
        self.assertEqual(len(responses.calls._calls), 3)

    @responses.activate
    def test_render_issue_without_beta_comment(self):
        issue_number = self.issue_number_without_beta_comment
        tag = self.tag_beta
        self.mock_util.mock_get_repo()
        # Mock the issue
        api_url = "{}/issues/{}".format(self.repo_api_url, issue_number)
        expected_issue = self._get_expected_issue(issue_number)
        responses.add(method=responses.GET, url=api_url, json=expected_issue)

        # Mock the comments list
        api_url = "{}/issues/{}/comments".format(self.repo_api_url, issue_number)
        expected_comment_1 = self._get_expected_issue_comment("Some other comment")
        responses.add(
            method=responses.GET, url=api_url, json=[], content_type="application/json"
        )

        # Mock the comment post response
        api_url = "{}/issues/{}/comments".format(self.repo_api_url, issue_number)
        expected_comment_1 = self._get_expected_issue_comment(
            "{} {}".format(
                GithubIssuesParser.ISSUE_COMMENT["beta"], self.version_number_beta
            )
        )
        responses.add(method=responses.POST, url=api_url, json=expected_comment_1)

        generator = self._create_generator(tag)
        parser = GithubIssuesParser(generator, self.title)
        parser.content = [
            {
                "issue_number": issue_number,
                "pr_number": self.pr_number,
                "pr_url": self.pr_url,
            }
        ]
        expected_render = self._create_expected_render(
            issue_number, expected_issue["title"], False
        )
        self.assertEqual(parser.render(), expected_render)
        self.assertEqual(len(responses.calls._calls), 4)

    @responses.activate
    def test_render_issue_with_prod_comment(self):
        issue_number = self.issue_number_with_prod_comment
        tag = self.tag_prod

        self.mock_util.mock_get_repo()

        # Mock the issue
        api_url = "{}/issues/{}".format(self.repo_api_url, issue_number)
        expected_issue = self._get_expected_issue(issue_number)
        responses.add(method=responses.GET, url=api_url, json=expected_issue)

        # Mock the comments list
        api_url = "{}/issues/{}/comments".format(self.repo_api_url, issue_number)
        expected_comment_1 = self._get_expected_issue_comment(
            GithubIssuesParser.ISSUE_COMMENT["prod"]
        )
        expected_comments = [expected_comment_1]
        responses.add(method=responses.GET, url=api_url, json=expected_comments)

        generator = self._create_generator(tag)
        parser = GithubIssuesParser(generator, self.title)
        parser.content = [
            {
                "issue_number": issue_number,
                "pr_number": self.pr_number,
                "pr_url": self.pr_url,
            }
        ]
        expected_render = self._create_expected_render(
            issue_number, expected_issue["title"], False
        )
        self.assertEqual(parser.render(), expected_render)
        self.assertEqual(len(responses.calls._calls), 3)

    @responses.activate
    def test_render_issue_without_prod_comment(self):
        issue_number = self.issue_number_without_prod_comment
        tag = self.tag_prod
        self.mock_util.mock_get_repo()
        # Mock the issue
        api_url = "{}/issues/{}".format(self.repo_api_url, issue_number)
        expected_issue = self._get_expected_issue(issue_number)
        responses.add(method=responses.GET, url=api_url, json=expected_issue)

        # Mock the comments list
        api_url = "{}/issues/{}/comments".format(self.repo_api_url, issue_number)
        expected_comment_1 = self._get_expected_issue_comment("Some other comment")
        responses.add(
            method=responses.GET, url=api_url, json=[], content_type="application/json"
        )

        # Mock the comment post response
        api_url = "{}/issues/{}/comments".format(self.repo_api_url, issue_number)
        expected_comment_1 = self._get_expected_issue_comment(
            "{} {}".format(
                GithubIssuesParser.ISSUE_COMMENT["prod"], self.version_number_prod
            )
        )
        responses.add(method=responses.POST, url=api_url, json=expected_comment_1)

        generator = self._create_generator(tag)
        parser = GithubIssuesParser(generator, self.title)
        parser.content = [
            {
                "issue_number": issue_number,
                "pr_number": self.pr_number,
                "pr_url": self.pr_url,
            }
        ]
        expected_render = self._create_expected_render(
            issue_number, expected_issue["title"], False
        )
        render = parser.render()
        self.assertEqual(render, expected_render)
        self.assertEqual(len(responses.calls._calls), 4)

    def _create_expected_render(self, issue_number, issue_title, link_pr):
        render = "# {}\r\n\r\n#{}: {}".format(self.title, issue_number, issue_title)
        if link_pr:
            render += " [[PR{}]({})]".format(self.pr_number, self.pr_url)
        return render


class TestInstallLinkParser:
    def test_no_package_version(self):
        generator = mock.Mock(link_pr=True)
        generator.version_id = None
        parser = InstallLinkParser(generator, "Title")
        parser.parse("abc")
        assert parser.render() == ""

    def test_package_version(self):
        generator = mock.Mock(link_pr=True)
        generator.version_id = "foo bar"
        parser = InstallLinkParser(generator, "Title")
        parser.parse("abc")
        output = parser.render()
        assert (
            "https://login.salesforce.com/packaging/installPackage.apexp?p0=foo+bar"
            in output
        )
        assert (
            "https://test.salesforce.com/packaging/installPackage.apexp?p0=foo+bar"
            in output
        )
