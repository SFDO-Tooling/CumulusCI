import httplib
import os
import unittest

import responses

from cumulusci.tasks.release_notes.generator import GithubReleaseNotesGenerator
from cumulusci.tasks.release_notes.parser import ChangeNotesLinesParser
from cumulusci.tasks.release_notes.parser import CommentingGithubIssuesParser
from cumulusci.tasks.release_notes.parser import GithubIssuesParser
from cumulusci.tasks.release_notes.parser import IssuesParser
from cumulusci.tasks.release_notes.exceptions import GithubApiNotFoundError
from cumulusci.tasks.release_notes.tests.util_github_api import GithubApiTestMixin


class TestChangeNotesLinesParser(unittest.TestCase):

    def setUp(self):
        self.title = 'Title'

    def test_parse_no_start_line(self):
        change_note = 'foo\r\nbar\r\n'
        parser = ChangeNotesLinesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [])

    def test_parse_start_line_no_content(self):
        change_note = '# {}\r\n\r\n'.format(self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [])

    def test_parse_start_line_no_end_line(self):
        change_note = '# {}\r\nfoo\r\nbar'.format(self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, ['foo', 'bar'])

    def test_parse_start_line_end_at_header(self):
        change_note = '# {}\r\nfoo\r\n# Another Header\r\nbar'.format(
            self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, ['foo'])

    def test_parse_start_line_no_content_no_end_line(self):
        change_note = '# {}'.format(self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [])

    def test_parse_multiple_start_lines_without_end_lines(self):
        change_note = '# {0}\r\nfoo\r\n# {0}\r\nbar\r\n'.format(self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, ['foo', 'bar'])

    def test_parse_multiple_start_lines_with_end_lines(self):
        change_note = '# {0}\r\nfoo\r\n\r\n# {0}\r\nbar\r\n\r\nincluded\r\n\r\n# not included'.format(
            self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, ['foo', 'bar', 'included'])

    def test_parse_multi_level_indent(self):
        change_note = '# {0}\r\nfoo \r\n    bar  \r\n        baz \r\n'.format(
            self.title)
        parser = ChangeNotesLinesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, ['foo', '    bar', '        baz'])

    def test_render_no_content(self):
        parser = ChangeNotesLinesParser(None, self.title)
        self.assertEqual(parser.render(), None)

    def test_render_one_content(self):
        parser = ChangeNotesLinesParser(None, self.title)
        content = ['foo']
        parser.content = content
        self.assertEqual(parser.render(),
                         '# {}\r\n\r\n{}'.format(self.title, content[0]))

    def test_render_multiple_content(self):
        parser = ChangeNotesLinesParser(None, self.title)
        content = ['foo', 'bar']
        parser.content = content
        self.assertEqual(parser.render(),
                         '# {}\r\n\r\n{}'.format(self.title, '\r\n'.join(content)))


class TestIssuesParser(unittest.TestCase):

    def setUp(self):
        self.title = 'Issues'

    def test_issue_numbers(self):
        change_note = '# {}\r\nfix #2\r\nfix #3\r\nfix #5\r\n'.format(
            self.title)
        parser = IssuesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2, 3, 5])

    def test_issue_numbers_and_other_numbers(self):
        change_note = '# {}\r\nfixes #2 but not # 3 or 5'.format(self.title)
        parser = IssuesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2])

    def test_multiple_issue_numbers_per_line(self):
        change_note = '# {}\r\nfix #2 also does fix #3 and fix #5\r\n'.format(
            self.title)
        parser = IssuesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2, 3, 5])


class TestGithubIssuesParser(unittest.TestCase, GithubApiTestMixin):

    def setUp(self):
        self.init_github()

        self.title = 'Issues'
        # Set up the mock release_tag lookup response
        self.issue_number_valid = 123
        self.issue_number_invalid = 456

    def test_issue_numbers(self):
        change_note = '# {}\r\nFixes #2, Closed #3 and Resolve #5'.format(
            self.title)
        parser = GithubIssuesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2, 3, 5])

    def test_issue_numbers_and_other_numbers(self):
        change_note = '# {}\r\nFixes #2 but not #5'.format(
            self.title)
        parser = GithubIssuesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [2])

    def test_no_issue_numbers(self):
        change_note = '# {}\r\n#2 and #3 are fixed by this change'.format(
            self.title)
        parser = GithubIssuesParser(None, self.title)
        parser.parse(change_note)
        self.assertEqual(parser.content, [])

    @responses.activate
    def test_render_issue_number_valid(self):
        api_url = '{}/issues/{}'.format(
            self.repo_api_url, self.issue_number_valid)
        expected_response = self._get_expected_issue(self.issue_number_valid)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
        )
        generator = self._create_generator()
        parser = GithubIssuesParser(generator, self.title)
        parser.content = [self.issue_number_valid]
        expected_render = '# {}\r\n\r\n#{}: {}'.format(
            self.title,
            self.issue_number_valid,
            expected_response['title'],
        )
        self.assertEqual(parser.render(), expected_render)

    @responses.activate
    def test_render_issue_number_invalid(self):
        api_url = '{}/issues/{}'.format(
            self.repo_api_url, self.issue_number_invalid)
        expected_response = self._get_expected_not_found()
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
            status=httplib.NOT_FOUND,
        )
        generator = self._create_generator()
        parser = GithubIssuesParser(generator, self.title)
        parser.content = [self.issue_number_invalid]
        with self.assertRaises(GithubApiNotFoundError):
            parser.render()

    def _create_generator(self):
        generator = GithubReleaseNotesGenerator(
            self.github_info.copy(), 'prod/1.1')
        return generator


class TestCommentingGithubIssuesParser(unittest.TestCase, GithubApiTestMixin):

    def setUp(self):
        self.init_github()

        self.title = 'Issues'
        self.issue_number_without_comments = 1
        self.issue_number_with_beta_comment = 2
        self.issue_number_without_beta_comment = 3
        self.issue_number_with_prod_comment = 4
        self.issue_number_without_prod_comment = 5
        self.tag_prod = 'prod/1.2'
        self.tag_beta = 'beta/1.2-Beta_3'
        self.tag_not_prod_or_beta = 'foo'
        self.version_number_prod = '1.1'
        self.version_number_beta = '1.2 (Beta 3)'

    def _create_generator(self, tag):
        generator = GithubReleaseNotesGenerator(self.github_info.copy(), tag)
        return generator

    @responses.activate
    def test_render_issue_without_comments(self):
        issue_number = self.issue_number_without_comments
        tag = self.tag_not_prod_or_beta

        # Mock the issue
        api_url = '{}/issues/{}'.format(
            self.repo_api_url,
            issue_number,
        )
        expected_issue = self._get_expected_issue(issue_number)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_issue,
        )

        # Mock the comments list
        api_url = '{}/issues/{}/comments'.format(
            self.repo_api_url,
            issue_number,
        )
        responses.add(
            method=responses.GET,
            url=api_url,
            body=[],
            content_type='application/json',
        )

        generator = self._create_generator(tag)
        parser = CommentingGithubIssuesParser(generator, self.title)
        parser.content = [issue_number]
        expected_render = '# {}\r\n\r\n#{}: {}'.format(
            self.title,
            issue_number,
            expected_issue['title'],
        )
        self.assertEqual(parser.render(), expected_render)

        # Only 2 api calls were made, ensuring comment creation
        # was not attempted
        self.assertEqual(len(responses.calls._calls), 2)

    @responses.activate
    def test_render_issue_with_beta_comment(self):
        issue_number = self.issue_number_with_beta_comment
        tag = self.tag_beta

        # Mock the issue
        api_url = '{}/issues/{}'.format(
            self.repo_api_url,
            issue_number,
        )
        expected_issue = self._get_expected_issue(issue_number)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_issue,
        )

        # Mock the comments list
        api_url = '{}/issues/{}/comments'.format(
            self.repo_api_url,
            issue_number,
        )
        expected_comment_1 = self._get_expected_issue_comment(
            CommentingGithubIssuesParser.message_beta,
        )
        expected_comments = [
            expected_comment_1,
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_comments,
        )

        generator = self._create_generator(tag)
        parser = CommentingGithubIssuesParser(generator, self.title)
        parser.content = [issue_number]
        expected_render = '# {}\r\n\r\n#{}: {}'.format(
            self.title,
            issue_number,
            expected_issue['title'],
        )
        self.assertEqual(parser.render(), expected_render)

        # Only 2 api calls were made, ensuring comment creation
        # was not attempted
        self.assertEqual(len(responses.calls._calls), 2)

    @responses.activate
    def test_render_issue_without_beta_comment(self):
        issue_number = self.issue_number_without_beta_comment
        tag = self.tag_beta

        # Mock the issue
        api_url = '{}/issues/{}'.format(
            self.repo_api_url,
            issue_number,
        )
        expected_issue = self._get_expected_issue(issue_number)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_issue,
        )

        # Mock the comments list
        api_url = '{}/issues/{}/comments'.format(
            self.repo_api_url,
            issue_number,
        )
        expected_comment_1 = self._get_expected_issue_comment(
            'Some other comment',
        )
        expected_comments = [
            expected_comment_1,
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            body=[],
            content_type='application/json',
        )

        # Mock the comment post response
        api_url = '{}/issues/{}/comments'.format(
            self.repo_api_url,
            issue_number,
        )
        expected_comment_1 = self._get_expected_issue_comment(
            '{} {}'.format(
                CommentingGithubIssuesParser.message_beta,
                self.version_number_beta,
            )
        )
        responses.add(
            method=responses.POST,
            url=api_url,
            json=expected_comment_1,
        )

        generator = self._create_generator(tag)
        parser = CommentingGithubIssuesParser(generator, self.title)
        parser.content = [issue_number]
        expected_render = '# {}\r\n\r\n#{}: {}'.format(
            self.title,
            issue_number,
            expected_issue['title'],
        )
        self.assertEqual(parser.render(), expected_render)

        # 3 api calls were made, ensuring comment creation
        # was attempted
        self.assertEqual(len(responses.calls._calls), 3)

    @responses.activate
    def test_render_issue_with_prod_comment(self):
        issue_number = self.issue_number_with_prod_comment
        tag = self.tag_prod

        # Mock the issue
        api_url = '{}/issues/{}'.format(
            self.repo_api_url,
            issue_number,
        )
        expected_issue = self._get_expected_issue(issue_number)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_issue,
        )

        # Mock the comments list
        api_url = '{}/issues/{}/comments'.format(
            self.repo_api_url,
            issue_number,
        )
        expected_comment_1 = self._get_expected_issue_comment(
            CommentingGithubIssuesParser.message_prod,
        )
        expected_comments = [
            expected_comment_1,
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_comments,
        )

        generator = self._create_generator(tag)
        parser = CommentingGithubIssuesParser(generator, self.title)
        parser.content = [issue_number]
        expected_render = '# {}\r\n\r\n#{}: {}'.format(
            self.title,
            issue_number,
            expected_issue['title'],
        )
        self.assertEqual(parser.render(), expected_render)

        # Only 2 api calls were made, ensuring comment creation
        # was not attempted
        self.assertEqual(len(responses.calls._calls), 2)

    @responses.activate
    def test_render_issue_without_prod_comment(self):
        issue_number = self.issue_number_without_prod_comment
        tag = self.tag_prod

        # Mock the issue
        api_url = '{}/issues/{}'.format(
            self.repo_api_url,
            issue_number,
        )
        expected_issue = self._get_expected_issue(issue_number)
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_issue,
        )

        # Mock the comments list
        api_url = '{}/issues/{}/comments'.format(
            self.repo_api_url,
            issue_number,
        )
        expected_comment_1 = self._get_expected_issue_comment(
            'Some other comment',
        )
        expected_comments = [
            expected_comment_1,
        ]
        responses.add(
            method=responses.GET,
            url=api_url,
            body=[],
            content_type='application/json',
        )

        # Mock the comment post response
        api_url = '{}/issues/{}/comments'.format(
            self.repo_api_url,
            issue_number,
        )
        expected_comment_1 = self._get_expected_issue_comment(
            '{} {}'.format(
                CommentingGithubIssuesParser.message_prod,
                self.version_number_prod,
            )
        )
        responses.add(
            method=responses.POST,
            url=api_url,
            json=expected_comment_1,
        )

        generator = self._create_generator(tag)
        parser = CommentingGithubIssuesParser(generator, self.title)
        parser.content = [issue_number]
        expected_render = '# {}\r\n\r\n#{}: {}'.format(
            self.title,
            issue_number,
            expected_issue['title'],
        )
        self.assertEqual(parser.render(), expected_render)

        # 3 api calls were made, ensuring comment creation
        # was attempted
        self.assertEqual(len(responses.calls._calls), 3)
