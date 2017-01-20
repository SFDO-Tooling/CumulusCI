import httplib
import re
import os
import requests
import json

from datetime import datetime
from distutils.version import LooseVersion


class BaseReleaseNotesGenerator(object):

    def __init__(self):
        self.change_notes = []
        self.init_parsers()
        self.init_change_notes()

    def __call__(self):
        self._parse_change_notes()
        return self.render()

    def init_change_notes(self):
        self.change_notes = self._init_change_notes()

    def _init_change_notes(self):
        """ Subclasses should override this method to return an initialized
        subclass of BaseChangeNotesProvider """
        return []

    def init_parsers(self):
        """ Initializes the parser instances as the list self.parsers """
        self.parsers = []
        self._init_parsers()

    def _init_parsers(self):
        """ Subclasses should override this method to initialize their
        parsers """
        pass

    def _parse_change_notes(self):
        """ Parses all change_notes in self.change_notes() through all parsers
        in self.parsers """
        for change_note in self.change_notes():
            self._parse_change_note(change_note)

    def _parse_change_note(self, change_note):
        """ Parses an individual change note through all parsers in
        self.parsers """
        for parser in self.parsers:
            parser.parse(change_note)

    def render(self):
        """ Returns the rendered release notes from all parsers as a string """
        release_notes = []
        for parser in self.parsers:
            parser_content = parser.render()
            if parser_content is not None:
                release_notes.append(parser_content)
        return u'\r\n\r\n'.join(release_notes)


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


class BaseChangeNotesProvider(object):

    def __init__(self, release_notes_generator):
        self.release_notes_generator = release_notes_generator

    def __call__(self):
        """ Subclasses should provide an implementation that returns an
        iterable of each change note """
        raise NotImplementedError()


class GithubApiNotFoundError(BaseException):
    pass


class GithubApiNoResultsError(BaseException):
    pass


class GithubApiMixin(object):
    github_api_base_url = 'https://api.github.com'

    @property
    def github_owner(self):
        return self.github_info['github_owner']

    @property
    def github_repo(self):
        return self.github_info['github_repo']

    @property
    def github_username(self):
        return self.github_info['github_username']

    @property
    def github_password(self):
        return self.github_info['github_password']

    @property
    def master_branch(self):
        return self.github_info.get('master_branch', 'master')

    @property
    def prefix_prod(self):
        return self.github_info.get('prefix_prod', 'prod/')

    @property
    def github_info(self):
        # By default, look for github config info in the release_notes
        # property.  Subclasses can override this if needed
        return self.release_notes_generator.github_info

    def call_api(self, subpath, data=None):
        """ Takes a subpath under the repository (ex: /releases) and returns
        the json data from the api """
        api_url = '{}/repos/{}/{}{}'.format(
            self.github_api_base_url, self.github_owner, self.github_repo,
            subpath)

        # Use Github Authentication if available for the repo
        kwargs = {}
        if self.github_owner and self.github_owner:
            kwargs['auth'] = (self.github_owner, self.github_password)

        if data:
            resp = requests.post(api_url, data=json.dumps(data), **kwargs)
        else:
            resp = requests.get(api_url, **kwargs)

        if resp.status_code == httplib.NOT_FOUND:
            raise GithubApiNotFoundError(resp.content)

        try:
            data = json.loads(resp.content)
            return data
        except:
            return resp.status_code


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
        return line.strip()

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

    def _get_default_regex(self):
        return '#(\d+)'

    def _render_content(self):
        issues = []
        for issue in self.content:
            issues.append('#{}'.format(issue))
        return u'\r\n'.join(issues)


class GithubIssuesParser(IssuesParser, GithubApiMixin):

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


class StaticChangeNotesProvider(BaseChangeNotesProvider):

    def __init__(self, release_notes, change_notes):
        super(StaticChangeNotesProvider, self).__init__(release_notes)
        self.change_notes = change_notes

    def __call__(self):
        for change_note in self.change_notes:
            yield change_note


class DirectoryChangeNotesProvider(BaseChangeNotesProvider):

    def __init__(self, release_notes, directory):
        super(DirectoryChangeNotesProvider, self).__init__(release_notes)
        self.directory = directory

    def __call__(self):
        for item in os.listdir(self.directory):
            yield open('{}/{}'.format(self.directory, item)).read()


class LastReleaseTagNotFoundError(BaseException):
    pass


class GithubChangeNotesProvider(BaseChangeNotesProvider, GithubApiMixin):
    """ Provides changes notes by finding all merged pull requests to
        the default branch between two tags.

        Expects the passed release_notes instance to have a github_info
        property that contains a dictionary of settings for accessing Github:
            - github_repo
            - github_owner
            - github_username
            - github_password

        Will optionally use the following if set provided by release_notes
            - master_branch: Name of the default branch.
                Defaults to 'master'
            - prefix_prod: Tag prefix for production release tags.
                Defaults to 'prod/'
    """

    def __init__(self, release_notes, current_tag, last_tag=None):
        super(GithubChangeNotesProvider, self).__init__(release_notes)
        self.current_tag = current_tag
        self._last_tag = last_tag
        self._start_date = None
        self._end_date = None

    def __call__(self):
        for pull_request in self._get_pull_requests():
            yield pull_request['body']

    @property
    def last_tag(self):
        if not self._last_tag:
            self._last_tag = self._get_last_tag()
        return self._last_tag

    @property
    def current_tag_info(self):
        if not hasattr(self, '_current_tag_info'):
            self._current_tag_info = self._get_tag_info(self.current_tag)
        return self._current_tag_info

    @property
    def last_tag_info(self):
        if not hasattr(self, '_last_tag_info'):
            self._last_tag_info = self._get_tag_info(self.last_tag)
        return self._last_tag_info

    @property
    def start_date(self):
        tag_date = self.current_tag_info['tag']['tagger']['date']
        return datetime.strptime(tag_date, "%Y-%m-%dT%H:%M:%SZ")

    @property
    def end_date(self):
        return if not self.last_tag
        tag_date = self.last_tag_info['tag']['tagger']['date']
        return datetime.strptime(tag_date, "%Y-%m-%dT%H:%M:%SZ")

    def _get_tag_info(self, tag):
        tag_info = {
            'ref': self.call_api('/git/refs/tags/{}'.format(tag)),
        }
        tag_info['tag'] = self.call_api(
            '/git/tags/{}'.format(tag_info['ref']['object']['sha']))
        return tag_info

    def _get_version_from_tag(self, tag):
        if tag.startswith(self.prefix_prod):
            return tag.replace(self.prefix_prod, '')
        elif tag.startswith(self.prefix_beta):
            return tag.replace(self.prefix_beta, '')
        raise ValueError(
            'Could not determine version number from tag {}'.format(tag))

    def _get_last_tag(self):
        """ Gets the last release tag before self.current_tag """

        current_version = LooseVersion(
            self._get_version_from_tag(self.current_tag))

        versions = []
        for ref in self.call_api('/git/refs/tags/{}'.format(self.prefix_prod)):
            ref_prefix = 'refs/tags/{}'.format(self.prefix_prod)

            # If possible to match a version number, extract the version number
            if re.search('%s[0-9][0-9]*\.[0-9][0-9]*' % ref_prefix, ref['ref']):
                version = LooseVersion(ref['ref'].replace(ref_prefix, ''))
                # Skip the current_version and any newer releases
                if version >= current_version:
                    continue
                versions.append(version)

        if versions:
            versions.sort()
            versions.reverse()
            return '%s%s' % (self.prefix_prod, versions[0])

        raise LastReleaseTagNotFoundError(
            'Could not locate the last release tag')

    def _get_pull_requests(self):
        """ Gets all pull requests from the repo since we can't do a filtered
        date merged search """
        try:
            pull_requests = self.call_api(
                '/pulls?state=closed&base={}'.format(self.master_branch)
            )
        except GithubApiNoResultsError:
            pull_requests = []

        for pull_request in pull_requests:
            if self._include_pull_request(pull_request):
                yield pull_request

    def _include_pull_request(self, pull_request):
        """ Checks if the given pull_request was merged to the default branch
        between self.start_date and self.end_date """

        if pull_request['state'] == 'open':
            return False

        if pull_request['base']['ref'] != self.master_branch:
            return False

        merged_date = pull_request.get('merged_at')
        if not merged_date:
            return False

        merged_date = datetime.strptime(merged_date, "%Y-%m-%dT%H:%M:%SZ")

        if merged_date < self.start_date and merged_date > self.end_date:
            return True

        return False


class StaticReleaseNotesGenerator(BaseReleaseNotesGenerator):

    def __init__(self, change_notes):
        self._change_notes = change_notes
        super(StaticReleaseNotesGenerator, self).__init__()

    def _init_parsers(self):
        self.parsers.append(ChangeNotesLinesParser(
            self, 'Critical Changes'))
        self.parsers.append(ChangeNotesLinesParser(self, 'Changes'))
        self.parsers.append(IssuesParser(
            self, 'Issues Closed'))

    def _init_change_notes(self):
        return StaticChangeNotesProvider(self, self._change_notes)


class DirectoryReleaseNotesGenerator(BaseReleaseNotesGenerator):

    def __init__(self, directory):
        self.directory = directory
        super(DirectoryReleaseNotesGenerator, self).__init__()

    def _init_parsers(self):
        self.parsers.append(ChangeNotesLinesParser(
            self, 'Critical Changes'))
        self.parsers.append(ChangeNotesLinesParser(self, 'Changes'))
        self.parsers.append(IssuesParser(
            self, 'Issues Closed'))

    def _init_change_notes(self):
        return DirectoryChangeNotesProvider(self, self.directory)


class GithubReleaseNotesGenerator(BaseReleaseNotesGenerator):

    def __init__(self, github_info, current_tag, last_tag=None):
        self.github_info = github_info
        self.current_tag = current_tag
        self.last_tag = last_tag
        super(GithubReleaseNotesGenerator, self).__init__()

    def _init_parsers(self):
        self.parsers.append(
            ChangeNotesLinesParser(
                self,
                'Critical Changes',
            )
        )
        self.parsers.append(
            ChangeNotesLinesParser(self, 'Changes')
        )
        self.parsers.append(
            GithubIssuesParser(self, 'Issues Closed')
        )

    def _init_change_notes(self):
        return GithubChangeNotesProvider(
            self,
            self.current_tag,
            self.last_tag
        )
