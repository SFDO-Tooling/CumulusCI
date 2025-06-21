import os


class BaseChangeNotesProvider(object):
    def __init__(self, release_notes_generator):
        self.release_notes_generator = release_notes_generator

    def __call__(self):
        """Subclasses should provide an implementation that returns an
        iterable of each change note"""
        raise NotImplementedError()


class StaticChangeNotesProvider(BaseChangeNotesProvider):
    def __init__(self, release_notes_generator, change_notes):
        super(StaticChangeNotesProvider, self).__init__(release_notes_generator)
        self.change_notes = change_notes

    def __call__(self):
        for change_note in self.change_notes:
            yield change_note


class DirectoryChangeNotesProvider(BaseChangeNotesProvider):
    def __init__(self, release_notes_generator, directory):
        super(DirectoryChangeNotesProvider, self).__init__(release_notes_generator)
        self.directory = directory

    def __call__(self):
        for item in sorted(os.listdir(self.directory)):
            yield open("{}/{}".format(self.directory, item)).read()


# For backwards-compatibility
import cumulusci.vcs.github.release_notes.provider as githubProvider
from cumulusci.utils.deprecation import warn_moved


class GithubChangeNotesProvider(githubProvider.GithubChangeNotesProvider):
    """Deprecated: use cumulusci.vcs.github.release_notes.provider.GithubChangeNotesProvider instead"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved("cumulusci.vcs.github.release_notes.provider", __name__)
