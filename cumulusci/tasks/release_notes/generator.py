from typing import List

from cumulusci.tasks.release_notes.parser import ChangeNotesLinesParser, IssuesParser
from cumulusci.tasks.release_notes.provider import (
    DirectoryChangeNotesProvider,
    StaticChangeNotesProvider,
)


class BaseReleaseNotesGenerator(object):
    def __init__(self):
        self.change_notes: List[BaseReleaseNotesGenerator] = []
        self.empty_change_notes: List[BaseReleaseNotesGenerator] = []
        self.init_parsers()
        self.init_change_notes()
        self.version_id = None
        self.trial_info = False
        self.sandbox_date = None
        self.production_date = None

    def __call__(self):
        self._parse_change_notes()
        return self.render()

    def init_change_notes(self):
        self.change_notes = self._init_change_notes()

    def _init_change_notes(self):
        """Subclasses should override this method to return an initialized
        subclass of BaseChangeNotesProvider"""
        return []

    def init_parsers(self):
        """Initializes the parser instances as the list self.parsers"""
        self.parsers = []
        self._init_parsers()

    def _init_parsers(self):
        """Subclasses should override this method to initialize their
        parsers"""
        pass

    def _parse_change_notes(self):
        """Parses all change_notes in self.change_notes() through all parsers
        in self.parsers"""
        for change_note in self.change_notes():
            self._parse_change_note(change_note)

    def _parse_change_note(self, change_note):
        """Parses an individual change note through all parsers in
        self.parsers. If no lines were added then appends the change
        note to the list of empty PRs"""
        line_added_by_parsers = False
        for parser in self.parsers:
            line_added = parser.parse(change_note)
            if not line_added_by_parsers:
                line_added_by_parsers = line_added

        if not line_added_by_parsers:
            self.empty_change_notes.append(change_note)

    def render(self):
        """Returns the rendered release notes from all parsers as a string"""
        release_notes = []
        for parser in self.parsers:
            parser_content = parser.render()
            if parser_content:
                release_notes.append(parser_content)
        return "\r\n\r\n".join(release_notes)


class StaticReleaseNotesGenerator(BaseReleaseNotesGenerator):
    def __init__(self, change_notes):
        self._change_notes = change_notes
        super(StaticReleaseNotesGenerator, self).__init__()

    def _init_parsers(self):
        self.parsers.append(ChangeNotesLinesParser(self, "Critical Changes"))
        self.parsers.append(ChangeNotesLinesParser(self, "Changes"))
        self.parsers.append(IssuesParser(self, "Issues Closed"))

    def _init_change_notes(self):
        return StaticChangeNotesProvider(self, self._change_notes)


class DirectoryReleaseNotesGenerator(BaseReleaseNotesGenerator):
    def __init__(self, directory):
        self.directory = directory
        super(DirectoryReleaseNotesGenerator, self).__init__()

    def _init_parsers(self):
        self.parsers.append(ChangeNotesLinesParser(self, "Critical Changes"))
        self.parsers.append(ChangeNotesLinesParser(self, "Changes"))
        self.parsers.append(IssuesParser(self, "Issues Closed"))

    def _init_change_notes(self):
        return DirectoryChangeNotesProvider(self, self.directory)


def render_empty_pr_section(empty_change_notes):
    section_lines = []
    if empty_change_notes:
        section_lines.append("\n# Pull requests with no release notes")
        for change_note in empty_change_notes:
            section_lines.append("\n* {}".format(markdown_link_to_pr(change_note)))
    return section_lines


def markdown_link_to_pr(change_note):
    return f"{change_note.title} [[PR{change_note.number}]({change_note.html_url})]"


# For backwards-compatibility
import cumulusci.vcs.github.release_notes.generator as githubGenerator
from cumulusci.utils.deprecation import warn_moved


class GithubReleaseNotesGenerator(githubGenerator.GithubReleaseNotesGenerator):
    """Deprecated: use cumulusci.vcs.github.release_notes.generator.GithubReleaseNotesGenerator instead"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved(
            "cumulusci.vcs.github.release_notes.generator.GithubReleaseNotesGenerator",
            __name__,
        )


class ParentPullRequestNotesGenerator(githubGenerator.ParentPullRequestNotesGenerator):
    """Deprecated: use cumulusci.vcs.github.release_notes.generator.ParentPullRequestNotesGenerator instead"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved(
            "cumulusci.vcs.github.release_notes.generator.ParentPullRequestNotesGenerator",
            __name__,
        )
