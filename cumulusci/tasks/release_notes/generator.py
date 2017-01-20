import httplib
import re
import os
import requests
import json

from datetime import datetime
from distutils.version import LooseVersion

from cumulusci.tasks.release_notes.github_api import GithubApiMixin
from cumulusci.tasks.release_notes.parser import ChangeNotesLinesParser
from cumulusci.tasks.release_notes.parser import IssuesParser
from cumulusci.tasks.release_notes.parser import GithubIssuesParser
from cumulusci.tasks.release_notes.parser import CommentingGithubIssuesParser
from cumulusci.tasks.release_notes.provider import StaticChangeNotesProvider
from cumulusci.tasks.release_notes.provider import DirectoryChangeNotesProvider
from cumulusci.tasks.release_notes.provider import GithubChangeNotesProvider
from cumulusci.tasks.release_notes.exceptions import GithubApiNotFoundError


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


class PublishingGithubReleaseNotesGenerator(GithubReleaseNotesGenerator, GithubApiMixin):

    def __call__(self):
        content = super(PublishingGithubReleaseNotesGenerator, self).__call__()
        return self.publish(content)

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
            CommentingGithubIssuesParser(self, 'Issues Closed')
        )

    def publish(self, content):
        release = self._get_release()
        return self._update_release(release, content)

    def _get_release(self):
        # Query for the release
        return self.call_api('/releases/tags/{}'.format(self.current_tag))

    def _update_release(self, release, content):

        if release['body']:
            new_body = []
            current_parser = None
            is_start_line = False
            for parser in self.parsers:
                parser.replaced = False

            # update existing sections
            for line in release['body'].splitlines():

                if current_parser:
                    if current_parser._is_end_line(current_parser._process_line(line)):
                        parser_content = current_parser.render()
                        if parser_content:
                            # replace existing section with new content
                            new_body.append(parser_content + '\r\n')
                        current_parser = None

                for parser in self.parsers:
                    if parser._render_header().strip() == parser._process_line(line).strip():
                        parser.replaced = True
                        current_parser = parser
                        is_start_line = True
                        break
                    else:
                        is_start_line = False

                if is_start_line:
                    continue
                if current_parser:
                    continue
                else:
                    # preserve existing sections
                    new_body.append(line.strip())

            # catch section without end line
            if current_parser:
                new_body.append(current_parser.render())

            # add new sections at bottom
            for parser in self.parsers:
                parser_content = parser.render()
                if parser_content and not parser.replaced:
                    new_body.append(parser_content + '\r\n')

            release['body'] = u'\r\n'.join(new_body)
        else:
            release['body'] = content

        if release.get('id'):
            resp = self.call_api(
                '/releases/{}'.format(release['id']), data=release)
        else:
            resp = self.call_api('/releases', data=release)

        return release['body']
