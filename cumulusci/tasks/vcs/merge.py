from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.base_source_control_task import BaseSourceControlTask
from cumulusci.utils.git import is_release_branch
from cumulusci.vcs.models import AbstractBranch, AbstractRepoCommit


class MergeBranch(BaseSourceControlTask):
    task_docs = """
    Merges the most recent commit on the current branch into other branches depending on the value of source_branch.

    If source_branch is a branch that does not start with the specified branch_prefix, then the commit will be
    merged to all branches that begin with branch_prefix and are not themselves child branches (i.e. branches don't contain '__' in their name).

    If source_branch begins with branch_prefix, then the commit is merged to all child branches of source_branch.
    """
    task_options = {  # TODO: should use `class Options instead`
        "commit": {
            "description": "The commit to merge into feature branches.  Defaults to the current head commit."
        },
        "source_branch": {
            "description": "The source branch to merge from.  Defaults to project__git__default_branch."
        },
        "branch_prefix": {
            "description": "A list of prefixes of branches that should receive the merge.  Defaults to project__git__prefix_feature"
        },
        "skip_future_releases": {
            "description": "If true, then exclude branches that start with the branch prefix if they are not for the lowest release number. Defaults to True."
        },
        "update_future_releases": {
            "description": "If true, then include release branches that are not the lowest release number even if they are not child branches. Defaults to False."
        },
        "create_pull_request_on_conflict": {
            "description": "If true, then create a pull request when a merge conflict arises. Defaults to True."
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        if "commit" not in self.options:
            self.options["commit"] = self.project_config.repo_commit
        if "branch_prefix" not in self.options:
            self.options[
                "branch_prefix"
            ] = self.project_config.project__git__prefix_feature
        if "source_branch" not in self.options:
            self.options[
                "source_branch"
            ] = self.project_config.project__git__default_branch
        if "skip_future_releases" not in self.options:
            self.options["skip_future_releases"] = True
        else:
            self.options["skip_future_releases"] = process_bool_arg(
                self.options.get("skip_future_releases")
            )
        self.options["update_future_releases"] = process_bool_arg(
            self.options.get("update_future_releases") or False
        )
        if "create_pull_request_on_conflict" not in self.options:
            self.options["create_pull_request_on_conflict"] = True
        else:
            self.options["create_pull_request_on_conflict"] = process_bool_arg(
                self.options.get("create_pull_request_on_conflict")
            )

    def _init_task(self):
        super()._init_task()
        self.repo = self.get_repo()

    def _run_task(self):
        self._validate_source_branch(self.options["source_branch"])
        branches_to_merge = self._get_branches_to_merge()

        for branch in branches_to_merge:
            self._merge(
                branch.name,
                self.options["source_branch"],
                self.options["commit"],
            )

    def _validate_source_branch(self, source_branch):
        """Validates that the source branch exists in the repository"""
        branch: AbstractBranch = self.repo.branch(source_branch)
        self.options["source_branch"] = branch.name

    def _get_existing_prs(self, source_branch, branch_prefix):
        """Returns the existing pull requests from the source branch
        to other branches that are candidates for merging."""
        existing_prs = []
        for pr in self.repo.pull_requests(state="open"):
            if pr.base_ref.startswith(branch_prefix) and pr.head_ref == source_branch:
                existing_prs.append(pr.base_ref)
        return existing_prs

    def _get_branches_to_merge(self):
        """
        If source_branch is the default branch (or a branch that doesn't start with a prefix), we
        gather all branches with branch_prefix that are not child branches.
        NOTE: We only include the _next_ closest release branch when automerging from main.
        A change on main may conflict with the current contents of the lowest release branch.
        In this case, we would like for that conflict to only need to be resolved once
        (not once for each release branch).

        If source_branch starts with branch prefix, we gather
        all branches with branch_prefix that are direct descendents of source_branch.

        If update_future_releases is True, and source_branch is a release branch
        then we also collect all future release branches.
        """
        repo_branches = list(self.repo.branches())
        next_release = self._get_next_release(repo_branches)
        skip_future_releases = self.options["skip_future_releases"]
        update_future_releases = self._update_future_releases(next_release)

        child_branches = []
        main_descendents = []
        release_branches = []
        for branch in repo_branches:
            # check for adding future release branches
            if update_future_releases and self._is_future_release_branch(
                branch.name, next_release
            ):
                release_branches.append(branch)
                continue

            # check if we looking at the source_branch
            if branch.name == self.options["source_branch"]:
                self.logger.debug(f"Skipping branch {branch.name}: is source branch")
                continue

            # check for branch prefix match
            elif not branch.name.startswith(self.options["branch_prefix"]):
                self.logger.debug(
                    f"Skipping branch {branch.name}: does not match prefix '{self.options['branch_prefix']}'"
                )
                continue

            # check if source_branch doesn't have prefix and is not a child (e.g. main)
            elif (
                not self.options["source_branch"].startswith(
                    self.options["branch_prefix"]
                )
                and "__" not in branch.name
            ):
                # only merge to the lowest numbered release branch
                # when merging from a branch without a prefix (e.g. main)
                if skip_future_releases and self._is_future_release_branch(
                    branch.name, next_release
                ):
                    continue
                main_descendents.append(branch)

            # else, we have a branch that starts with branch_prefix
            # check is this branch is a direct descendent
            elif self._is_source_branch_direct_descendent(branch.name):
                child_branches.append(branch)

            # else not a direct descendent
            else:
                self.logger.debug(
                    f"Skipping branch {branch.name}: is not a direct descendent of {self.options['source_branch']}"
                )

        to_merge = []
        if child_branches:
            self.logger.debug(
                f"Found child branches to update: {[branch.name for branch in child_branches]}"
            )
            to_merge = child_branches
        elif self.options["source_branch"].startswith(self.options["branch_prefix"]):
            self.logger.debug(
                f"No children found for branch {self.options['source_branch']}"
            )

        if release_branches:
            self.logger.debug(
                f"Found future release branches to update: {[branch.name for branch in release_branches]}"
            )
            to_merge = to_merge + release_branches

        if main_descendents:
            self.logger.debug(
                f"Found descendents of {self.options['source_branch']} to update: {[branch.name for branch in main_descendents]}"
            )
            to_merge = to_merge + main_descendents

        return to_merge

    def _get_next_release(self, repo_branches):
        """Returns the integer that corresponds to the lowest release number found on all release branches.
        NOTE: We assume that once a release branch is merged that it will be deleted.
        """
        release_nums = [
            self._get_release_number(branch.name)
            for branch in repo_branches
            if self._is_release_branch(branch.name)
        ]
        next_release = sorted(release_nums)[0] if release_nums else None
        return next_release

    def _update_future_releases(self, next_release):
        """Determines whether or not to update future releases.
        Returns True if all of the below checks are True. False otherwise.

        Checks:
        (1) Did we receive the 'update_future_release' flag?
        (2) Is the source_branch a release branch?
        (3) Is it the lowest numbered release branch that exists?

        NOTE: This functionality assumes that the lowest numbered release branch in the repo is
        the next closest release. Put another way, once a release branch is merged we assume that it is immediately deleted.
        """
        update_future_releases = False
        if (
            self.options["update_future_releases"]
            and self._is_release_branch(self.options["source_branch"])
            and next_release == self._get_release_number(self.options["source_branch"])
        ):
            update_future_releases = True
        return update_future_releases

    def _is_release_branch(self, branch_name):
        """A release branch begins with the given prefix"""
        return is_release_branch(branch_name, self.options["branch_prefix"])

    def _get_release_number(self, branch_name) -> int:
        """Get the release number from a release branch name.

        Assumes we already know it is a release branch.
        """
        return int(branch_name.split(self.options["branch_prefix"])[1])

    def _merge(self, branch_name, source, commit):
        """Attempt to merge a commit from source to branch with branch_name"""
        compare = self.repo.compare_commits(branch_name, commit, source)
        if not compare or not compare.files:
            self.logger.info(f"Skipping branch {branch_name}: no file diffs found")
            return

        ret = self.repo.merge(branch_name, commit, source)
        if isinstance(ret, AbstractRepoCommit):
            self.logger.info(
                f"Merged {compare.behind_by} commits into branch: {branch_name}"
            )
        elif ret is None:
            if self.options["create_pull_request_on_conflict"]:
                self._create_conflict_pull_request(branch_name, source)
            else:
                self.logger.info(
                    f"Merge conflict on branch {branch_name}: skipping pull request creation"
                )

    def _create_conflict_pull_request(self, branch_name, source):
        """Attempt to create a pull request from source into branch_name if merge operation encounters a conflict"""
        if branch_name in self._get_existing_prs(
            self.options["source_branch"], self.options["branch_prefix"]
        ):
            self.logger.info(
                f"Merge conflict on branch {branch_name}: merge PR already exists"
            )
            return

        pull = self.repo.create_pull(
            title=f"Merge {source} into {branch_name}",
            base=branch_name,
            head=source,
            body="This pull request was automatically generated because "
            "an automated merge hit a merge conflict",
            options={
                "error_message": f"Error creating merge conflict pull request to merge {source} into {branch_name}"
            },
        )

        if pull is not None:
            self.logger.info(
                f"Merge conflict on branch {branch_name}: created pull request #{pull.number}"
            )
            return pull

    def _is_source_branch_direct_descendent(self, branch_name):
        """Returns True if branch is a direct descendent of the source branch"""
        source_dunder_count = self.options["source_branch"].count("__")
        return (
            branch_name.startswith(f"{self.options['source_branch']}__")
            and branch_name.count("__") == source_dunder_count + 1
        )

    def _is_future_release_branch(self, branch_name, next_release):
        return (
            self._is_release_branch(branch_name)
            and branch_name != self.options["source_branch"]
            and self._get_release_num(branch_name) > next_release
        )

    def _get_release_num(self, release_branch_name):
        """Given a release branch, returns an integer that
        corresponds to the release number for that branch"""
        return int(release_branch_name.split(self.options["branch_prefix"])[1])
