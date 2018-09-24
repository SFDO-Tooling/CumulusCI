import os
from cumulusci.core.exceptions import GithubException
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.tasks.github.util import CommitDir


class CommitApexDocs(BaseGithubTask):

    task_options = {
        "branch": {"description": "Branch name; default=project__apexdoc__branch"},
        "dir_local": {
            "description": "Local dir of ApexDocs (contains index.html). "
            + "default=repo_root/ApexDocumentation"
        },
        "dir_repo": {
            "description": "Location relative to repo root. "
            + "default=project__apexdoc__repo_dir"
        },
        "dry_run": {"description": "Execute a dry run if True (default=False)"},
        "commit_message": {
            "description": 'Message for commit; default="Update Apex docs"'
        },
    }

    def _run_task(self):

        # args
        branch = self.options.get(
            "branch", self.project_config.project__apexdoc__branch
        )
        if not branch:
            raise GithubException("Unable to determine branch name")
        local_dir = self.options.get("dir_local")
        if not local_dir:
            local_base_dir = (
                self.project_config.project__apexdoc__dir
                if self.project_config.project__apexdoc__dir
                else self.project_config.repo_root
            )
            local_dir = os.path.join(local_base_dir, "ApexDocumentation")
        repo_dir = self.options.get(
            "dir_repo", self.project_config.project__apexdoc__repo_dir
        )
        dry_run = process_bool_arg(self.options.get("dry_run", False))
        commit_message = self.options.get("commit_message", "Update Apex docs")

        # get API
        repo = self.get_repo()

        # commit
        author = {"name": self.github.user().name, "email": self.github_config.email}
        commit_dir = CommitDir(repo, self.logger, author)
        commit_dir(local_dir, branch, repo_dir, commit_message, dry_run)
