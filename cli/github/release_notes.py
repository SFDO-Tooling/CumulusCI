import re

# NOT IMPLEMENTED
#import github_api

# Assumptions
# - All overrides will be done via new Python classes

SFDO_ISSUE_REGEX = r'.*fix.* #(\d*).*$'


class BaseReleaseNotesGenerator(object):

    def __init__(self):
        self.change_notes = []
        self.init_parsers()
        self.init_change_notes()

    def init_change_notes(self):
        self.change_notes = self._init_change_notes()

    def _init_change_notes(self):
        """ Subclasses should override this method to return an initialized subclass of BaseChangeNotesProvider """
        return []

    def init_parsers(self):
        """ Initializes the parser instances as the list self.parsers """
        self.parsers = []
        self._init_parsers()

    def _init_parsers(self):
        """ Subclasses should override this method to initialize their parsers """
        pass

    def _parse_change_notes(self):
        """ Parses all change_notes in self.change_notes() through all parsers in self.parsers """
        for change_note in self.change_notes():
            self._parse_change_note(change_note)

    def _parse_change_note(self, change_note):
        """ Parses an individual change note through all parsers in self.parsers """
        for parser in self.parsers:
            parser.parse(change_notes)

    def render(self):
        """ Returns the rendered release notes from all parsers as a string """
        release_notes = []
        for parser in self.parsers:
            release_notes.append(parser.render())
        return u'\r\n'.join(release_notes)


class BaseChangeNotesParser(object):

    def __init__(self, title):
        self.title = title
        self.content = []

    def parse(self):
        raise NotImplementedError()

    def render(self):
        return '# {}\r\n{}'.format(self.title, self._render())

    def _render(self):
        raise NotImplementedError()


class BaseChangeNotesProvider(object):

    def __init__(self, release_notes_generator):
        self.release_notes_generator = release_notes_generator

    def __call__(self):
        """ Subclasses should provide an implementation that returns an iterable of each change note """
        raise NotImplemented


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
        """ Takes a subpath under the repository (ex: /releases) and returns the json data from the api """
        api_url = '{}/repos/{}/{}{}'.format(
            self.github_api_base_url, self.github_owner, self.github_repo, subpath)

        # Use Github Authentication if available for the repo
        kwargs = {}
        if self.github_owner and self.github_owner:
            kwargs['auth'] = (self.github_owner, self.github_password)

        if data:
            resp = requests.post(api_url, data=json.dumps(data), **kwargs)
        else:
            resp = requests.get(api_url, **kwargs)

        try:
            data = json.loads(resp.content)
            return data
        except:
            return resp.status_code


class ChangeNotesLinesParser(BaseChangeNotesParser):

    def __init__(self, release_notes_generator, title, start_line):
        super(ChangeNotesLinesParser, self).__init__(title)
        if not start_line:
            raise ValueError('start_line cannot be empty')
        self.release_notes_generator = release_notes_generator
        self.start_line = start_line
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
        return line == self.start_line

    def _is_end_line(self, line):
        if not line:
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
        return u'# {}'.format(self.title)

    def _render_content(self):
        return u'\r\n'.join(self.content)


class IssuesParser(ChangeNotesLinesParser):

    def __init__(self, release_notes_generator, title, start_line, issue_regex=None):
        super(IssuesParser, self).__init__(
            release_notes_generator, title, start_line)
        if issue_regex:
            self.issue_regex = issue_regex
        else:
            self.issue_regex = SFDO_ISSUE_REGEX
        print self.issue_regex

    def _add_line(self, line):
        # find one or more issue numbers (modify regex)
        issue_number = re.sub(self.issue_regex, r'\1',
                              line, flags=re.IGNORECASE)
        # loop here
        if issue_number:
            self.content.append(int(issue_number))


class GithubIssuesParser(IssuesParser):

    def _add_line(self, line):
        issue_number = re.sub(r'.*fix.* #(\d*).*$', r'\1',
                              line, flags=re.IGNORECASE)
        self.content.append(issue_number)

    # def _render_issue(self, issue_number):
        #issue = github_api.get_issue(issue_number)
        # print '#{}: {}'.format(issue_number, issue['title'])


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


class GithubChangeNotesProvider(BaseChangeNotesProvider, GithubApiMixin):
    """ Provides changes notes by finding all merged pull requests to
        the default branch between two tags.

        Expects the passed release_notes instance to have a github_info property
        that contains a dictionary of settings for accessing Github:
            - github_repo
            - github_owner
            - github_username
            - github_password

        Will optionally use the following if set provided by release_notes
            - master_branch: Name of the default branch.  Defaults to master
            - prefix_prod: Tag prefix for production release tags.  Defaults to prod/
    """

    def __init__(self, release_notes, current_tag, last_tag=None):
        super(GithubChangeNotesProvider, self).__init__(release_notes)
        self.current_tag = current_tag
        self._last_tag = last_tag
        self._start_date = None
        self._end_date = None

    def __call__(self):
        for pull_request in self._get_pull_requests:
            yield pull_request['body']

    @property
    def last_tag(self):
        if self._last_tag:
            return self._last_tag

        self._last_tag = self._get_last_tag
        return self._last_tag

    @property
    def start_date(self):
        pass

    @property
    def end_date(self):
        pass

    def _get_last_tag(self):
        """ Gets the last release tag before self.current_tag """
        pass

    def _get_pull_requests(self):
        """ Gets all pull requests from the repo since we can't do a filtered date merged search """
        for pull_request in pull_requests:
            if self._include_pull_request(pull_request):
                yield pull_request

    def _include_pull_request(self, pull_request):
        """ Checks if the given pull_request was merged to the default branch between self.start_date and self.end_date """
        pass


class StaticReleaseNotesGenerator(BaseReleaseNotesGenerator):

    def __init__(self, change_notes):
        self._change_notes = change_notes
        super(StaticReleaseNotesGenerator, self).__init__()

    def _init_parsers(self):
        self.parsers.append(ChangeNotesLinesParser(
            self, 'Critical Changes', '# Warning'))
        self.parsers.append(ChangeNotesLinesParser(self, 'Changes', '# Info'))
        self.parsers.append(GithubIssuesParser(
            self, 'Issues Closed', '# Issues'))

    def _init_change_notes(self):
        return StaticChangeNotesProvider(self, self._change_notes)


class DirectoryReleaseNotesGenerator(BaseReleaseNotesGenerator):

    def __init__(self, directory):
        self.directory = directory
        super(DirectoryReleaseNotesGenerator, self).__init__()

    def _init_parsers(self):
        self.parsers.append(ChangeNotesLinesParser(
            self, 'Critical Changes', '# Warning'))
        self.parsers.append(ChangeNotesLinesParser(self, 'Changes', '# Info'))
        self.parsers.append(GithubIssuesParser(
            self, 'Issues Closed', '# Issues'))

    def _init_change_notes(self):
        return DirectoryChangeNotesProvider(self, self.directory)
