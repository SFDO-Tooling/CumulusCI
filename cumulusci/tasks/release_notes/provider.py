import os
import pytz
import time
from datetime import datetime
from distutils.version import LooseVersion

import github3.exceptions

from cumulusci.core.exceptions import GithubApiError
from cumulusci.core.exceptions import GithubApiNotFoundError


class BaseChangeNotesProvider(object):
    def __init__(self, release_notes_generator):
        self.release_notes_generator = release_notes_generator

    def __call__(self):
        """ Subclasses should provide an implementation that returns an
        iterable of each change note """
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


class GithubChangeNotesProvider(BaseChangeNotesProvider):
    """ Provides changes notes by finding all merged pull requests to
    the default branch between two tags.

    Expects the passed release_notes_generator instance to have a github_info
    property that contains a dictionary of settings for accessing Github:

        - github_repo
        - github_owner
        - github_username
        - github_password
        - default_branch
        - prefix_prod: Tag prefix for production release tags. Defaults to 'prod/'
    """

    def __init__(self, release_notes_generator, current_tag, last_tag=None):
        super(GithubChangeNotesProvider, self).__init__(release_notes_generator)
        self.current_tag = current_tag
        self._last_tag = last_tag
        self._start_date = None
        self._end_date = None
        self.repo = release_notes_generator.get_repo()
        self.github_info = release_notes_generator.github_info

    def __call__(self):
        for pull_request in self._get_pull_requests():
            yield pull_request

    @property
    def last_tag(self):
        if not self._last_tag:
            self._last_tag = self._get_last_tag()
        return self._last_tag

    @property
    def current_tag_info(self):
        if not hasattr(self, "_current_tag_info"):
            tag = self._get_tag_info(self.current_tag)
            self._current_tag_info = {"tag": tag, "commit": self._get_commit_info(tag)}
        return self._current_tag_info

    @property
    def last_tag_info(self):
        if not hasattr(self, "_last_tag_info"):
            if self.last_tag:
                tag = self._get_tag_info(self.last_tag)
                self._last_tag_info = {"tag": tag, "commit": self._get_commit_info(tag)}
            else:
                self._last_tag_info = None
        return self._last_tag_info

    def _get_commit_info(self, tag):
        return self.repo.git_commit(tag.object.sha)

    @property
    def start_date(self):
        return self._get_commit_date(self.current_tag_info["commit"])

    @property
    def end_date(self):
        if self.last_tag_info:
            return self._get_commit_date(self.last_tag_info["commit"])

    def _get_commit_date(self, commit):
        t = time.strptime(commit.author["date"], "%Y-%m-%dT%H:%M:%SZ")
        return datetime(t[0], t[1], t[2], t[3], t[4], t[5], t[6], pytz.UTC)

    def _get_tag_info(self, tag_name):
        try:
            tag = self.repo.ref("tags/{}".format(tag_name))
        except github3.exceptions.NotFoundError:
            raise GithubApiNotFoundError("Tag not found: {}".format(tag_name))
        if tag.object.type != "tag":
            raise GithubApiError(
                "Tag {} is lightweight, must be annotated.".format(tag_name)
            )
        return self.repo.tag(tag.object.sha)

    def _get_version_from_tag(self, tag):
        if tag.startswith(self.github_info["prefix_prod"]):
            return tag.replace(self.github_info["prefix_prod"], "")
        elif tag.startswith(self.github_info["prefix_beta"]):
            return tag.replace(self.github_info["prefix_beta"], "")
        raise ValueError("Could not determine version number from tag {}".format(tag))

    def _get_last_tag(self):
        """ Gets the last release tag before self.current_tag """

        current_version = LooseVersion(
            self._get_version_from_tag(self.release_notes_generator.current_tag)
        )

        versions = []
        for tag in self.repo.tags():
            if not tag.name.startswith(self.github_info["prefix_prod"]):
                continue
            version = LooseVersion(self._get_version_from_tag(tag.name))
            if version >= current_version:
                continue
            versions.append(version)
        if versions:
            versions.sort()
            return "{}{}".format(self.github_info["prefix_prod"], versions[-1])

    def _get_pull_requests(self):
        """ Gets all pull requests from the repo since we can't do a filtered
        date merged search """
        for pull in self.repo.pull_requests(
            state="closed", base=self.github_info["default_branch"], direction="asc"
        ):
            if self._include_pull_request(pull):
                yield pull

    def _include_pull_request(self, pull_request):
        """ Checks if the given pull_request was merged to the default branch
        between self.start_date and self.end_date """

        merged_date = pull_request.merged_at
        if not merged_date:
            return False
        if self.last_tag:
            last_tag_sha = self.last_tag_info["commit"].sha
            if pull_request.merge_commit_sha == last_tag_sha:
                # Github commit dates can be different from the merged_at date
                return False

        current_tag_sha = self.current_tag_info["commit"].sha
        if pull_request.merge_commit_sha == current_tag_sha:
            return True

        # include PRs before current tag
        if merged_date <= self.start_date:
            if self.end_date:
                # include PRs after last tag
                if (
                    merged_date > self.end_date
                    and pull_request.merge_commit_sha != last_tag_sha
                ):
                    return True
            else:
                # no last tag, include all PRs before current tag
                return True

        return False
