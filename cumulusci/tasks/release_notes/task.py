import copy

from cumulusci.core.github import markdown_link_to_pr
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.base_source_control_task import BaseSourceControlTask
from cumulusci.tasks.release_notes.generator import BaseReleaseNotesGenerator
from cumulusci.utils.deprecation import warn_moved
from cumulusci.vcs.bootstrap import (
    get_pull_requests_with_base_branch,
    is_label_on_pull_request,
    is_pull_request_merged,
)
from cumulusci.vcs.models import AbstractPullRequest, AbstractRepo


class AllVcsReleaseNotes(BaseSourceControlTask):
    filename: str = "vcs_release_notes.html"

    task_options = {
        "repos": {
            "description": (
                "The list of owner, repo key pairs for which to generate release notes."
                + " Ex: 'owner': SalesforceFoundation 'repo': 'NPSP'"
            ),
            "required": True,
        },
    }

    def _run_task(self):
        table_of_contents = "<h1>Table of Contents</h1><ul>"
        body = ""
        for project in self.options["repos"]:
            if project["owner"] and project["repo"]:
                options = copy.deepcopy(self.options)
                options["repo_owner"] = project["owner"]
                options["repo_name"] = project["repo"]

                release = (
                    self.vcs_service.get_repository(options=options)
                    .latest_release()
                    .body
                )
                table_of_contents += (
                    f"""<li><a href="#{project['repo']}">{project['repo']}</a></li>"""
                )
                release_project_header = (
                    f"""<h1 id="{project['repo']}">{project['repo']}</h1>"""
                )
                release_html = self.vcs_service.markdown(
                    release,
                    mode="gfm",
                    context="{}/{}".format(project["owner"], project["repo"]),
                )
                body += f"{release_project_header}<hr>{release_html}<hr>"
        table_of_contents += "</ul><br><hr>"
        head = "<head><title>Release Notes</title></head>"
        body = f"<body>{table_of_contents}{body}</body>"
        result = f"<html>{head}{body}</html>"
        with open(self.filename, "w") as f:
            f.write(result)


class VcsReleaseNotes(BaseSourceControlTask):
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
        "publish": {"description": "Publish to VCS release if True (default=False)"},
        "include_empty": {
            "description": "If True, include links to PRs that have no release notes (default=False)"
        },
        "version_id": {
            "description": "The package version id used by the InstallLinksParser to add install urls"
        },
        "trial_info": {
            "description": "If True, Includes trialforce template text for this product."
        },
        "sandbox_date": {
            "description": "The date of the sandbox release in ISO format (Will default to None)"
        },
        "production_date": {
            "description": "The date of the production release in ISO format (Will default to None)"
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options["link_pr"] = process_bool_arg(self.options.get("link_pr", False))
        self.options["publish"] = process_bool_arg(self.options.get("publish", False))
        self.options["include_empty"] = process_bool_arg(
            self.options.get("include_empty", False)
        )
        self.options["trial_info"] = self.options.get("trial_info", False)
        self.options["sandbox_date"] = self.options.get("sandbox_date", None)
        self.options["production_date"] = self.options.get("production_date", None)

    def _run_task(self):
        release_notes: BaseReleaseNotesGenerator = (
            self.vcs_service.release_notes_generator(self.options)
        )
        self.logger.info("\n" + release_notes())


class ParentPullRequestNotes(BaseSourceControlTask):
    task_docs = """
    Aggregate change notes from child pull request(s) to a corresponding parent pull request.

    When given the branch_name option, this task will: (1) check if the base branch
    of the corresponding pull request starts with the feature branch prefix and if so (2) attempt
    to query for a pull request corresponding to this parent feature branch. (3) if a pull request
    isn't found, the task exits and no actions are taken.

    If the build_notes_label is present on the pull request, then all notes from the
    child pull request are aggregated into the parent pull request. if the build_notes_label
    is not detected on the parent pull request then a link to the child pull request
    is placed under the "Unaggregated Pull Requests" header.

    If you have a pull request on branch feature/myFeature that you would like to rebuild notes
    for use the branch_name and force options:
        cci task run vcs_parent_pr_notes --branch-name feature/myFeature --force True
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
        self.repo: AbstractRepo = self.get_repo()
        self.commit = self.repo.get_commit(self.project_config.repo_commit)
        self.branch_name = self.options.get("branch_name")
        self.force_rebuild_change_notes = process_bool_arg(
            self.options["force"] or False
        )
        self.generator: BaseReleaseNotesGenerator = (
            self.vcs_service.parent_pr_notes_generator(self.repo)
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
        pull_requests: list[
            AbstractPullRequest
        ] = self.repo.get_pull_requests_by_commit(self.commit.sha)
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
        pull_request.body = "" if pull_request.body is None else pull_request.body
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


# Deprecated aliases for backwards compatibility
# These classes are deprecated and will be removed in future versions.
# Use the new AllVcsReleaseNotes and VcsReleaseNotes classes instead.


class AllGithubReleaseNotes(AllVcsReleaseNotes):
    """Deprecated: use cumulusci.tasks.release_notes.task.AllVcsReleaseNotes instead"""

    filename: str = "github_release_notes.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved(
            "cumulusci.tasks.release_notes.task.AllVcsReleaseNotes",
            f"{__name__}.AllGithubReleaseNotes",
        )


class GithubReleaseNotes(VcsReleaseNotes):
    """Deprecated: use cumulusci.tasks.release_notes.task.VcsReleaseNotes instead"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved(
            "cumulusci.tasks.release_notes.task.VcsReleaseNotes",
            f"{__name__}.GithubReleaseNotes",
        )
