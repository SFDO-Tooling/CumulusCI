from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.tasks.release_notes.generator import (
    GithubReleaseNotesGenerator,
    ParentPullRequestNotesGenerator,
)
from github3.pulls import ShortPullRequest
from cumulusci.core.exceptions import TaskOptionsError


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
    task_options = {
        "branch_name": {"description": "Name of branch with a pull request"},
        "parent_branch_name": {
            "description": "name of the parent branch to rebuild change notes for (default=None)"
        },
    }

    def _run_task(self):
        branch_name = self.options.get("branch_name")
        parent_branch_name = self.options.get("parent_branch_name")

        if not branch_name and not parent_branch_name:
            raise TaskOptionsError(
                "You must specify either branch_name or parent_branch_name."
            )

        parent_notes_generator = ParentPullRequestNotesGenerator(
            self.github,
            self.get_repo(),
            self.project_config.repo_owner,
            self.project_config.project__git__release_notes__parsers.values(),
            self.project_config.project__git__prefix_feature,
            branch_name,
            parent_branch_name,
        )
        parent_notes_generator.execute()
