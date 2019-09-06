# -*- coding: utf-8 -*-
"""Release Note Tasks

Classes:
    GithubReleaseNotes
    ParentPullRequestNotes
"""
from github3.pulls import ShortPullRequest
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.release_notes.generator import (
    GithubReleaseNotesGenerator,
    ParentPullRequestNotesGenerator,
)
from cumulusci.core.github import (
    create_pull_request,
    is_label_on_pull_request,
    add_labels_to_pull_request,
    get_pull_request_by_branch_name,
)


class GithubReleaseNotes(BaseGithubTask):

    task_options = {
        "tag": {
            "description": (
                "The tag to generate release notes for." + " Ex: release/1.2"
            ),
            "required": True,
        },
        "last_tag": {
            "description": (
                "Override the last release tag. This is useful"
                + " to generate release notes if you skipped one or more"
                + " releases."
            )
        },
        "link_pr": {
            "description": (
                "If True, insert link to source pull request at" + " end of each line."
            )
        },
        "publish": {"description": "Publish to GitHub release if True (default=False)"},
        "include_empty": {
            "description": "If True, include links to PRs that have no release notes (default=False)"
        },
    }

    def _run_task(self):
        github_info = {
            "github_owner": self.project_config.repo_owner,
            "github_repo": self.project_config.repo_name,
            "github_username": self.github_config.username,
            "github_password": self.github_config.password,
            "master_branch": self.project_config.project__git__default_branch,
            "prefix_beta": self.project_config.project__git__prefix_beta,
            "prefix_prod": self.project_config.project__git__prefix_release,
        }

        generator = GithubReleaseNotesGenerator(
            self.github,
            github_info,
            self.project_config.project__git__release_notes__parsers.values(),
            self.options["tag"],
            self.options.get("last_tag"),
            process_bool_arg(self.options.get("link_pr", False)),
            process_bool_arg(self.options.get("publish", False)),
            self.get_repo().has_issues,
            process_bool_arg(self.options.get("include_empty", False)),
        )

        release_notes = generator()
        self.logger.info("\n" + release_notes)


class ParentPullRequestNotes(BaseGithubTask):
    task_docs = """
    Aggregate change notes from child pull request(s) to its corresponding
    parent's pull request.
    
    When given the branch_name option, this task will: (1) check if the base branch
    of the corresponding pull request starts with the feature branch prefix and if so (2) attempt
    to query for a pull request corresponding to this parent feature branch. (3) if a pull request
    isn't found, one is created and the BUILD_NOTES_LABEL is applied to it.

    If the BUILD_NOTES_LABEL is present on the pull request, then all notes from the 
    child pull request are aggregated into the parent pull request. If the BUILD_NOTES_LABEL
    is not detected on the parent pull request then a link to the child pull request
    is placed under the "Unaggregated Pull Reqeusts" header.

    When given the parent_branch_name option, this task will query for a corresponding pull request.
    If a pull request is not found, the task exits. If a pull request is found, then all notes
    from child pull requests are re-aggregated and the body of the parent is replace entirely.
    """

    BUILD_NOTES_LABEL = "Build Change Notes"

    task_options = {
        "branch_name": {"description": "Name of branch with a pull request"},
        "parent_branch_name": {
            "description": "name of the parent branch to rebuild change notes for"
        },
    }

    def _run_task(self):
        branch_name = self.options.get("branch_name")
        parent_branch_name = self.options.get("parent_branch_name")

        if (not branch_name and not parent_branch_name) or (
            branch_name and parent_branch_name
        ):
            raise TaskOptionsError(
                "You must specify either branch_name or (exclusive) parent_branch_name."
            )

        self.repo = self.get_repo()
        generator = ParentPullRequestNotesGenerator(
            self.github, self.repo, self.project_config
        )

        if branch_name:
            self._handle_branch_name_option(generator, branch_name)
        elif parent_branch_name:
            self._handle_parent_branch_name_option(generator, parent_branch_name)

    def _handle_branch_name_option(self, generator, branch_name):
        parent_pull_request = None
        pull_request = get_pull_request_by_branch_name(self.repo, branch_name)

        if not pull_request:
            self.logger.info(
                "Pull request not found for branch: {}.\nExiting...".format(branch_name)
            )
            return

        base_branch = pull_request.base.ref
        feature_prefix = self.project_config.project__git__prefix_feature
        if not base_branch.startswith(feature_prefix):
            self.logger.info("Pull request's base is not a feature branch.\nExiting...")
            return

        parent_pull_request = self._get_parent_pull_request(base_branch)
        if is_label_on_pull_request(
            self.repo, parent_pull_request, self.BUILD_NOTES_LABEL
        ):
            generator.aggregate_child_change_notes(parent_pull_request)
        else:
            generator.update_unaggregated_pr_header(parent_pull_request, branch_name)

    def _handle_parent_branch_name_option(self, generator, parent_branch_name):
        pull_request = get_pull_request_by_branch_name(self.repo, parent_branch_name)
        if not pull_request:
            # If we don't find a pull request for a specified parent
            # branch we don't create one. Notify the user, and exit
            self.logger.info(
                "No pull request found for branch: {}.\nExiting...".format(
                    parent_branch_name
                )
            )
        elif is_label_on_pull_request(self.repo, pull_request, self.BUILD_NOTES_LABEL):
            # We can only aggregate child change notes when given the parent_branch option
            #
            # We aren't able to append to the 'Unaggregated Pull Reqeusts' header.
            # We don't know at what time the label was applied to the pull request;
            # and therefore, we cannot determine which child pull requests are already
            # aggregated into the parent pull request, and which ones should be
            # included in the 'Unaggregated Pull Requests' section.
            generator.aggregate_child_change_notes(pull_request)
        else:
            self.logger.info(
                (
                    "Missing label '{}', on pull request #{}. "
                    "If you want to recreate the body of this pull request "
                    "please apply the label '{}' and run this command again. "
                    "Note that any existing modifications to the change "
                    "notes will be lost."
                ).format(
                    self.BUILD_NOTES_LABEL, pull_request.number, self.BUILD_NOTES_LABEL
                )
            )

    def _get_parent_pull_request(self, branch_name):
        """Attempts to retrieve a pull request for the given branch.
        If one is not found, then it is created and the 'Build Change Notes' 
        label is applied to it."""
        parent_pull_request = get_pull_request_by_branch_name(self.repo, branch_name)
        if not parent_pull_request:
            self.logger.info(
                "Pull request not found. Creating pull request for branch: {} with base of 'master'.".format(
                    branch_name
                )
            )
            parent_pull_request = create_pull_request(self.repo, branch_name)
            add_labels_to_pull_request(
                self.repo, parent_pull_request.number, self.BUILD_NOTES_LABEL
            )
        return parent_pull_request
