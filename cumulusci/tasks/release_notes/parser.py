import re
import os

from cumulusci.tasks.release_notes.github_api import GithubApiMixin


class BaseChangeNotesParser(object):

    def __init__(self, title):
        self.title = title
        self.content = []

    def parse(self):
        raise NotImplementedError()

    def render(self):
        return '# {}\r\n\r\n{}'.format(self.title, self._render())

    def _render(self):
        raise NotImplementedError()


class ChangeNotesLinesParser(BaseChangeNotesParser):

    def __init__(self, release_notes_generator, title):
        super(ChangeNotesLinesParser, self).__init__(title)
        self.release_notes_generator = release_notes_generator
        self.title = title
        self._in_section = False

    def parse(self, change_note):
        for line in change_note.splitlines():
            line = self._process_line(line)

            # Look for the starting line of the section
            if self._is_start_line(line):
                self._in_section = True
                continue

            # Add all content once in the section
            if self._in_section:

                # End when the end of section is found
                if self._is_end_line(line):
                    # If the line starts the section again, continue
                    if self._is_start_line(line):
                        continue
                    self._in_section = False
                    continue

                # Skip excluded lines
                if self._is_excluded_line(line):
                    continue

                self._add_line(line)

        self._in_section = False

    def _process_line(self, line):
        try:
            line = unicode(line, 'utf-8')
        except TypeError:
            pass
        return line.rstrip()

    def _is_excluded_line(self, line):
        if not line:
            return True

    def _is_start_line(self, line):
        if self.title:
            return line.upper() == '# {}'.format(self.title.upper())

    def _is_end_line(self, line):
        # Also treat any new top level heading as end of section
        if line.startswith('# '):
            return True

    def _add_line(self, line):
        self.content.append(line)

    def render(self):
        if not self.content:
            return None
        content = []
        content.append(self._render_header())
        content.append(self._render_content())
        return u'\r\n'.join(content)

    def _render_header(self):
        return u'# {}\r\n'.format(self.title)

    def _render_content(self):
        return u'\r\n'.join(self.content)


class IssuesParser(ChangeNotesLinesParser):

    def __init__(self, release_notes_generator, title,
                 issue_regex=None):
        super(IssuesParser, self).__init__(
            release_notes_generator,
            title,
        )
        if issue_regex:
            self.issue_regex = issue_regex
        else:
            self.issue_regex = self._get_default_regex()

    def _add_line(self, line):
        # find issue numbers per line
        issue_numbers = re.findall(self.issue_regex, line, flags=re.IGNORECASE)
        for issue_number in issue_numbers:
            self.content.append(int(issue_number))
        self.content.sort()

    def _get_default_regex(self):
        return '#(\d+)'

    def _render_content(self):
        issues = []
        for issue in self.content:
            issues.append('#{}'.format(issue))
        return u'\r\n'.join(issues)


class ParserGithubApiMixin(GithubApiMixin):

    @property
    def current_tag(self):
        return self.release_notes_generator.current_tag

    @property
    def github_info(self):
        # By default, look for github config info in the release_notes
        # property.  Subclasses can override this if needed
        return self.release_notes_generator.github_info


class GithubIssuesParser(IssuesParser, ParserGithubApiMixin):

    def _get_default_regex(self):
        keywords = (
            'close',
            'closes',
            'closed',
            'fix',
            'fixes',
            'fixed',
            'resolve',
            'resolves',
            'resolved',
        )
        return r'(?:{})\s#(\d+)'.format('|'.join(keywords))

    def _render_content(self):
        content = []
        for issue_number in self.content:
            issue_info = self._get_issue_info(issue_number)
            issue_title = issue_info['title']
            content.append('#{}: {}'.format(issue_number, issue_title))
        return u'\r\n'.join(content)

    def _get_issue_info(self, issue_number):
        return self.call_api('/issues/{}'.format(issue_number))


class CommentingGithubIssuesParser(GithubIssuesParser):

    message_prod = 'Included in production release'
    message_beta = 'Included in beta release'

    def _get_issue_info(self, issue_number):
        self._add_issue_comment(issue_number)
        return super(CommentingGithubIssuesParser, self)._get_issue_info(issue_number)

    def _add_issue_comment(self, issue_number):
        # Ensure all issues have a comment on which release they were fixed
        gh_issue_comments = self.call_api(
            '/issues/{}/comments'.format(issue_number))
        has_comment = False

        current_tag_info = self.current_tag_info

        for comment in gh_issue_comments:
            if current_tag_info['is_prod']:
                if comment['body'].startswith(self.message_prod):
                    has_comment = True
            elif current_tag_info['is_beta']:
                if comment['body'].startswith(self.message_beta):
                    has_comment = True

        if not has_comment:
            data = {}
            if current_tag_info['is_prod']:
                data['body'] = '{} {}'.format(
                    self.message_prod,
                    current_tag_info['version_number'],
                )
            elif current_tag_info['is_beta']:
                data['body'] = '{} {}'.format(
                    self.message_beta,
                    current_tag_info['version_number'],
                )

            if data:
                self.call_api(
                    '/issues/{}/comments'.format(issue_number),
                    data=data,
                )
