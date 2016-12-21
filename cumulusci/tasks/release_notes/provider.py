import re
import os

from datetime import datetime
from distutils.version import LooseVersion

from cumulusci.tasks.release_notes.exceptions import LastReleaseTagNotFoundError
from cumulusci.tasks.release_notes.github_api import GithubApiMixin
from cumulusci.tasks.release_notes.exceptions import GithubApiNoResultsError
from cumulusci.tasks.release_notes.exceptions import GithubApiNotFoundError


class BaseChangeNotesProvider(object):

    def __init__(self, release_notes_generator):
        self.release_notes_generator = release_notes_generator

    def __call__(self):
        """ Subclasses should provide an implementation that returns an
        iterable of each change note """
        raise NotImplementedError()


class StaticChangeNotesProvider(BaseChangeNotesProvider):

    def __init__(self, release_notes_generator, change_notes):
        super(StaticChangeNotesProvider, self).__init__(
            release_notes_generator)
        self.change_notes = change_notes

    def __call__(self):
        for change_note in self.change_notes:
            yield change_note


class DirectoryChangeNotesProvider(BaseChangeNotesProvider):

    def __init__(self, release_notes_generator, directory):
        super(DirectoryChangeNotesProvider, self).__init__(
            release_notes_generator)
        self.directory = directory

    def __call__(self):
        for item in os.listdir(self.directory):
            yield open('{}/{}'.format(self.directory, item)).read()


class ProviderGithubApiMixin(GithubApiMixin):

    @property
    def current_tag(self):
        return self.release_notes_generator.current_tag

    @property
    def github_info(self):
        # By default, look for github config info in the release_notes
        # property.  Subclasses can override this if needed
        return self.release_notes_generator.github_info


class GithubChangeNotesProvider(BaseChangeNotesProvider, ProviderGithubApiMixin):
    """ Provides changes notes by finding all merged pull requests to
        the default branch between two tags.

        Expects the passed release_notes_generator instance to have a github_info
        property that contains a dictionary of settings for accessing Github:
            - github_repo
            - github_owner
            - github_username
            - github_password

        Will optionally use the following if set provided by release_notes_generator
            - master_branch: Name of the default branch.
                Defaults to 'master'
            - prefix_prod: Tag prefix for production release tags.
                Defaults to 'prod/'
    """

    def __init__(self, release_notes_generator, current_tag, last_tag=None):
        super(GithubChangeNotesProvider, self).__init__(
            release_notes_generator)
        #self.current_tag = current_tag
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
            self._current_tag_info['commit'] = self._get_commit_info(
                self._current_tag_info)
        return self._current_tag_info

    @property
    def last_tag_info(self):
        if not hasattr(self, '_last_tag_info'):
            if self.last_tag:
                self._last_tag_info = self._get_tag_info(self.last_tag)
                self._last_tag_info['commit'] = self._get_commit_info(
                    self._last_tag_info)
            else:
                self._last_tag_info = None
        return self._last_tag_info

    def _get_commit_info(self, tag_info):
        commit_sha = tag_info['tag']['object']['sha']
        return self.call_api('/git/commits/{}'.format(commit_sha))

    @property
    def start_date(self):
        return self._get_commit_date(self.current_tag_info['commit'])

    @property
    def end_date(self):
        if self.last_tag_info:
            return self._get_commit_date(self.last_tag_info['commit'])

    def _get_commit_date(self, commit_info):
        commit_date = commit_info['author']['date']
        return datetime.strptime(commit_date, "%Y-%m-%dT%H:%M:%SZ")

    def _get_tag_info(self, tag):
        tag_info = {
            'ref': self.call_api('/git/refs/tags/{}'.format(tag)),
        }
        try:
            tag_info['tag'] = self.call_api(
                '/git/tags/{}'.format(tag_info['ref']['object']['sha']))
        except GithubApiNotFoundError:
            tag_info['tag'] = None
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
        try:
            refs = self.call_api('/git/refs/tags/{}'.format(self.prefix_prod))
        except GithubApiNotFoundError:
            # no production tags exist
            refs = []
        for ref in refs:
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

        merge_sha = pull_request['merge_commit_sha']
        if self.last_tag:
            last_tag_sha = self.last_tag_info['commit']['sha']
            if merge_sha == last_tag_sha:
                # Github commit dates can be different from the merged_at date
                return False

        current_tag_sha = self.current_tag_info['commit']['sha']
        if merge_sha == current_tag_sha:
            return True

        # include PRs before current tag
        if merged_date <= self.start_date:
            if self.end_date:
                # include PRs after last tag
                if merged_date > self.end_date and merge_sha != last_tag_sha:
                    return True
            else:
                # no last tag, include all PRs before current tag
                return True

        return False
