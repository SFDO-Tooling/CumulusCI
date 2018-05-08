import re
import os

from cumulusci.core.exceptions import GithubApiNotFoundError
from exceptions import GithubIssuesError


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
        self.h2 = {} # dict of h2 sections - key=header, value is list of lines
        self.h2_title = None # has value when in h2 section

    def parse(self, change_note):
        change_note = self._process_change_note(change_note)
        for line in change_note.splitlines():
            line = self._process_line(line)

            # Look for the starting line of the section
            if self._is_start_line(line):
                self._in_section = True
                continue

            # Look for h2
            if line.startswith('## '):
                self.h2_title = re.sub('\s+#+$', '', line[3:]).lstrip()
                continue

            # Add all content once in the section
            if self._in_section:

                # End when the end of section is found
                if self._is_end_line(line):
                    # If the line starts the section again, continue
                    if self._is_start_line(line):
                        continue
                    self._in_section = False
                    self.h2_title = None
                    continue

                # Skip excluded lines
                if self._is_excluded_line(line):
                    continue

                self._add_line(line)

        self._in_section = False

    def _process_change_note(self, change_note):
        # subclasses override this if some manipulation is needed
        return change_note

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
        line = self._add_link(line)
        if self.h2_title:
            if self.h2_title not in self.h2:
                self.h2[self.h2_title] = []
            self.h2[self.h2_title].append(line)
            return
        self.content.append(line)

    def _add_link(self, line):
        return line

    def render(self):
        if not self.content and not self.h2:
            return None
        content = []
        content.append(self._render_header())
        if self.content:
            content.append(self._render_content())
        if self.h2:
            content.append(self._render_h2())
        return u'\r\n'.join(content)

    def _render_header(self):
        return u'# {}\r\n'.format(self.title)

    def _render_content(self):
        return u'\r\n'.join(self.content)

    def _render_h2(self):
        content = []
        for h2_title in self.h2.keys():
            content.append(u'\r\n## {}\r\n'.format(h2_title))
            content.append(u'\r\n'.join(self.h2[h2_title]))
        return u'\r\n'.join(content)


class GithubLinesParser(ChangeNotesLinesParser):

    def __init__(self, release_notes_generator, title):
        super(GithubLinesParser, self).__init__(release_notes_generator, title)
        self.link_pr = release_notes_generator.link_pr
        self.pr_number = None
        self.pr_url = None

    def _process_change_note(self, pull_request):
        self.pr_number = pull_request.number
        self.pr_url = pull_request.html_url
        return pull_request.body

    def _add_link(self, line):
        if self.link_pr:
            line += ' [[PR{}]({})]'.format(self.pr_number, self.pr_url)
        return line


class IssuesParser(ChangeNotesLinesParser):

    def __init__(self, release_notes_generator, title, issue_regex=None):
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

    def _get_default_regex(self):
        return '#(\d+)'

    def _render_content(self):
        issues = []
        for issue in sorted(self.content):
            issues.append('#{}'.format(issue))
        return u'\r\n'.join(issues)


class GithubIssuesParser(IssuesParser):
    ISSUE_COMMENT = {
        'beta': 'Included in beta release',
        'prod': 'Included in production release',
    }

    def __init__(self, release_notes_generator, title, issue_regex=None):
        super(GithubIssuesParser, self).__init__(
            release_notes_generator,
            title,
            issue_regex,
        )
        if not release_notes_generator.has_issues:
            raise GithubIssuesError(
                'Cannot use {}'.format(self.__class__.__name__) +
                ' because issues are disabled for this repository.'
            )
        self.link_pr = release_notes_generator.link_pr
        self.pr_number = None
        self.pr_url = None
        self.publish = release_notes_generator.do_publish
        self.github = release_notes_generator.github

    def _add_line(self, line):
        # find issue numbers per line
        issue_numbers = re.findall(self.issue_regex, line, flags=re.IGNORECASE)
        for issue_number in issue_numbers:
            self.content.append({
                'issue_number': int(issue_number),
                'pr_number': self.pr_number,
                'pr_url': self.pr_url,
            })

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
        for item in sorted(self.content, key=lambda k: k['issue_number']):
            issue = self._get_issue(item['issue_number'])
            txt = '#{}: {}'.format(item['issue_number'], issue.title)
            if self.link_pr:
                txt += ' [[PR{}]({})]'.format(
                    item['pr_number'],
                    item['pr_url'],
                )
            content.append(txt)
            if self.publish:
                self._add_issue_comment(issue)
        return u'\r\n'.join(content)

    def _get_issue(self, issue_number):
        issue = self.github.issue(
            self.release_notes_generator.github_info['github_owner'],
            self.release_notes_generator.github_info['github_repo'],
            issue_number,
        )
        if not issue:
            raise GithubApiNotFoundError('Issue #{} not found'.format(issue_number))
        return issue

    def _process_change_note(self, pull_request):
        self.pr_number = pull_request.number
        self.pr_url = pull_request.html_url
        return pull_request.body

    def _add_issue_comment(self, issue):
        # Ensure all issues have a comment on which release they were fixed
        prefix_beta = self.release_notes_generator.github_info['prefix_beta']
        prefix_prod = self.release_notes_generator.github_info['prefix_prod']
        if self.release_notes_generator.current_tag.startswith(prefix_beta):
            is_beta = True
        elif self.release_notes_generator.current_tag.startswith(prefix_prod):
            is_beta = False
        else:
            # not production or beta tag, don't comment
            return
        if is_beta:
            comment_prefix = self.ISSUE_COMMENT['beta']
            version_parts = re.findall(
                '{}(\d+\.\d+)-Beta_(\d+)'.format(prefix_beta),
                self.release_notes_generator.current_tag,
            )
            version_str = '{} (Beta {})'.format(*version_parts[0])
        else:
            comment_prefix = self.ISSUE_COMMENT['prod']
            version_str = self.release_notes_generator.current_tag.replace(
                prefix_prod,
                '',
            )
        has_comment = False
        for comment in issue.iter_comments():
            if comment.body.startswith(comment_prefix):
                has_comment = True
                break
        if not has_comment:
            issue.create_comment('{} {}'.format(comment_prefix, version_str))
