from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.tasks.release_notes.generator import (
    GithubReleaseNotesGenerator,
    ParentPullRequestNotesGenerator,
)
from cumulusci.core.github import (
    markdown_link_to_pr,
    is_pull_request_merged,
    is_label_on_pull_request,
    get_pull_requests_by_commit,
    get_pull_requests_with_base_branch,
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
    isn't found, the task exits and no actions are taken.

    If the build_notes_label is present on the pull request, then all notes from the
    child pull request are aggregated into the parent pull request. if the build_notes_label
    is not detected on the parent pull request then a link to the child pull request
    is placed under the "Unaggregated Pull Requests" header.

    When given the parent_branch_name option, this task will query for a corresponding pull request.
    If a pull request is not found, the task exits. If a pull request is found, then all notes
    from child pull requests are re-aggregated and the body of the parent is replaced entirely.
    """
    UNAGGREGATED_PR_HEADER = "\r\n\r\n# Unaggregated Pull Requests"

    task_options = {
        "branch_name": {
            "description": "Name of branch to check for parent status, and if so, reaggregate change notes from child branches.",
            "required": True,
        },
        "build_notes_label": {
            "description": (
                "Name of the label that indicates that change notes on parent pull "
                "requests should be reaggregated when a child branch pull request is created."
            ),
            "required": True,
        },
        "force": {
            "description": "force rebuilding of change notes from child branches in the given branch.",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super(ParentPullRequestNotes, self)._init_options(kwargs)
        self.options["branch_name"] = self.options.get("branch_name")
        self.options["build_notes_label"] = self.options.get("build_notes_label")
        self.options["force"] = self.options.get("force")

    def _setup_self(self):
        self.repo = self.get_repo()
        self.commit = self.repo.commit(self.project_config.repo_commit)
        self.branch_name = self.options.get("branch_name")
        self.force_rebuild_change_notes = process_bool_arg(self.options["force"])
        self.generator = ParentPullRequestNotesGenerator(
            self.github, self.repo, self.project_config
        )

    def _run_task(self):
        self._setup_self()

        if self.force_rebuild_change_notes:
            pull_request = self._get_parent_pull_request()
            if pull_request:
                self.generator.aggregate_child_change_notes(pull_request)

        elif self._has_parent_branch() and self._commit_is_merge():
            parent_pull_request = self._get_parent_pull_request()
            if parent_pull_request:
                if is_label_on_pull_request(
                    self.repo,
                    parent_pull_request,
                    self.options.get("build_notes_label"),
                ):
                    self.generator.aggregate_child_change_notes(parent_pull_request)
                else:
                    child_branch_name = self._get_child_branch_name_from_merge_commit()
                    if child_branch_name:
                        self._update_unaggregated_pr_header(
                            parent_pull_request, child_branch_name
                        )

    def _has_parent_branch(self):
        feature_prefix = self.project_config.project__git__prefix_feature
        return (
            self.branch_name.startswith(feature_prefix) and "__" not in self.branch_name
        )

    def _commit_is_merge(self):
        return len(self.commit.parents) > 1

    def _get_parent_pull_request(self):
        """Attempts to retrieve a pull request for the given branch."""
        requests = get_pull_requests_with_base_branch(
            self.repo, self.repo.default_branch, self.branch_name
        )
        if len(requests) > 0:
            return requests[0]
        else:
            self.logger.info(f"Pull request not found for branch {self.branch_name}.")

    def _get_child_branch_name_from_merge_commit(self):
        pull_requests = get_pull_requests_by_commit(
            self.github, self.repo, self.commit.sha
        )
        merged_prs = list(filter(is_pull_request_merged, pull_requests))

        child_branch_name = None
        if len(merged_prs) == 1:
            return merged_prs[0].head.ref

        else:
            self.logger.error(
                f"Received multiple pull requests, expected one, for commit sha: {self.commit.sha}"
            )

        return child_branch_name

    def _update_unaggregated_pr_header(
        self, pull_request_to_update, branch_name_to_add
    ):
        """Updates the 'Unaggregated Pull Requests' section header with a link
        to the new child branch pull request"""

        self._add_header(pull_request_to_update)

        pull_requests = get_pull_requests_with_base_branch(
            self.repo,
            branch_name_to_add.split("__")[0],
            branch_name_to_add,
            state="all",
        )

        if len(pull_requests) == 0:
            self.logger.info(f"No pull request for branch {branch_name_to_add} found.")
        elif len(pull_requests) > 1:
            self.logger.error(
                f"Expected one pull request, found {len(pull_requests)} for branch {branch_name_to_add}"
            )
        else:
            self._add_link_to_pr(pull_request_to_update, pull_requests[0])

    def _add_header(self, pull_request):
        """Appends the header to the pull_request.body if not already present"""
        if self.UNAGGREGATED_PR_HEADER not in pull_request.body:
            pull_request.body += self.UNAGGREGATED_PR_HEADER

    def _add_link_to_pr(self, to_update, to_link):
        """Updates pull request to_update with a link to pull
        request to_link if one does not already exist."""
        body = to_update.body
        pull_request_link = markdown_link_to_pr(to_link)
        if pull_request_link not in body:
            body += "\r\n* " + pull_request_link
            to_update.update(body=body)
