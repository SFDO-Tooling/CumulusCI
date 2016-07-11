import re

# NOT IMPLEMENTED
#import github_api

# Assumptions
# - All overrides will be done via new Python classes


class BaseReleaseNotesGenerator(object):

    def __init__(self):
        self.change_notes = []
        self.init_parsers()

    def init_parsers(self):
        """ Initializes the parser instances as the list self.parsers """
        self.parsers = []
        self._init_parsers()

    def _init_parsers(self):
        """ Subclasses should override this method to initialize their parsers """
        pass

    def add(self, change_note):
        """ Adds Markdown content to self.change_notes and parses through all parsers in self.parsers """
        self.change_notes.append(change_note)
        self._parse_change_note(change_note)

    def _parse_change_notes(self):
        """ Parses all change_notes in self.change_notes through all parsers in self.parsers """
        for change_note in self.change_notes:
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
        print self.title
        self._render()
        print

    def _render(self):
        raise NotImplementedError()


class ChangeNotesLinesParser(BaseChangeNotesParser):

    def __init__(self, title, start_line):
        super(ChangeNotesLinesParser, self).__init__(title)
        if not start_line:
            raise ValueError('start_line cannot be empty')
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


class GithubIssuesParser(ChangeNotesLinesParser):

    def add_line(self, line):
        issue_number = re.sub(r'.*fix.* #(\d*).*$', r'\1',
                              line, flags=re.IGNORECASE)
        self.content.append(issue_number)

    # def _render_issue(self, issue_number):
        #issue = github_api.get_issue(issue_number)
        # print '#{}: {}'.format(issue_number, issue['title'])


class ReleaseNotesGenerator(BaseReleaseNotesGenerator):

    def _init_parsers(self):
        self.parsers.append(ChangeNotesLinesParser(
            'Critical Changes', '# Warning'))
        self.parsers.append(ChangeNotesLinesParser(
            'Changes', '# Info'))
        self.parsers.append(GithubIssuesParser(
            'Issues Closed', '# Issues'))
