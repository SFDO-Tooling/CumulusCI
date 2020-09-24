import http.client

from github3 import GitHubError
import github3.exceptions

from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.github.base import BaseGithubTask


class MergeBranchOld(BaseGithubTask):
    task_options = {
        "commit": {
            "description": "The commit to merge into feature branches.  Defaults to the current head commit."
        },
        "source_branch": {
            "description": "The source branch to merge from.  Defaults to project__git__default_branch."
        },
        "branch_prefix": {
            "description": "The prefix of branches that should receive the merge.  Defaults to project__git__prefix_feature"
        },
        "children_only": {
            "description": "If True, merge will only be done to child branches.  This assumes source branch is a parent feature branch.  Defaults to False"
        },
    }

    def _init_options(self, kwargs):
        super(MergeBranchOld, self)._init_options(kwargs)

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
        self.options["children_only"] = process_bool_arg(
            self.options.get("children_only", False)
        )

    def _run_task(self):
        self.repo = self.get_repo()

        self._validate_branch()
        self._get_existing_prs()
        branch_tree = self._get_branch_tree()
        self._merge_branches(branch_tree)

    def _validate_branch(self):
        try:
            self.repo.branch(self.options["source_branch"])
        except github3.exceptions.NotFoundError:
            message = f"Branch {self.options['source_branch']} not found"
            self.logger.error(message)
            raise GithubApiNotFoundError(message)

    def _get_existing_prs(self):
        # Get existing pull requests targeting a target branch
        self.existing_prs = []
        for pr in self.repo.pull_requests(state="open"):
            if (
                pr.base.ref.startswith(self.options["branch_prefix"])
                and pr.head.ref == self.options["source_branch"]
            ):
                self.existing_prs.append(pr.base.ref)

    def _get_branch_tree(self):
        branches, branches_dict = self._get_list_and_dict_of_branches()
        children, parents = self._get_parent_and_child_branches(branches)
        return self._construct_branch_tree(branches, branches_dict, children, parents)

    def _get_list_and_dict_of_branches(self):
        """Returns a list and dict of branches that match the given branch_prefix"""
        branches = []
        branches_dict = {}
        for branch in self.repo.branches():
            if branch.name == self.options["source_branch"]:
                if not self.options["children_only"]:
                    self.logger.debug(
                        f"Skipping branch {branch.name}: is source branch"
                    )
                    branches_dict[branch.name] = branch
                    continue
            if not branch.name.startswith(self.options["branch_prefix"]):
                if not self.options["children_only"]:
                    self.logger.debug(
                        f"Skipping branch {branch.name}: does not match prefix {self.options['branch_prefix']}"
                    )
                # The following line isn't included in coverage
                # due to behavior of the CPython peephole optimizer,
                # see https://bitbucket.org/ned/coveragepy/issues/198/continue-marked-as-not-covered
                continue  # pragma: no cover
            branches.append(branch)
            branches_dict[branch.name] = branch

        return branches, branches_dict

    def _get_parent_and_child_branches(self, branches):
        possible_children = []
        possible_parents = []
        for branch in branches:
            parts = branch.name.replace(self.options["branch_prefix"], "", 1).split(
                "__", 1
            )
            if len(parts) == 2:
                possible_children.append(parts)
            else:
                possible_parents.append(branch.name)

        parents = {}
        children = []
        for possible_child in possible_children:
            parent = f"{self.options['branch_prefix']}{possible_child[0]}"
            if parent in possible_parents:
                child = "__".join(possible_child)
                child = self.options["branch_prefix"] + child
                if parent not in parents:
                    parents[parent] = []
                parents[parent].append(child)
                children.append(child)

        return children, parents

    def _construct_branch_tree(self, branches, branches_dict, children, parents):
        """Build a branch tree list with parent/child branches"""
        branch_tree = []
        for branch in branches:
            if branch.name in children:
                # Skip child branches
                continue
            if (
                self.options["children_only"]
                and branch.name != self.options["source_branch"]
            ):
                # If merging to children only, skip any branches other than source
                continue
            branch_item = {"branch": branch, "children": []}
            for child in parents.get(branch.name, []):
                branch_item["children"].append(branches_dict[child])
            branch_tree.append(branch_item)

        return branch_tree

    def _merge_branches(self, branch_tree):
        # Process merge on all branches
        for branch_item in branch_tree:
            if self.options["children_only"]:
                if branch_item["children"]:
                    self.logger.info(
                        f"Performing merge from parent branch {self.options['source_branch']} to children"
                    )
                else:
                    self.logger.info(
                        f"No children found for branch {self.options['source_branch']}"
                    )
                    continue
                for child in branch_item["children"]:
                    self._merge(
                        branch=child.name,
                        source=self.options["source_branch"],
                        commit=self.options["commit"],
                        children=[],
                    )
            else:
                self._merge(
                    branch=branch_item["branch"].name,
                    source=self.options["source_branch"],
                    commit=self.options["commit"],
                    children=branch_item["children"],
                )

    def _merge(self, branch, source, commit, children=None):
        if not children:
            children = []
        branch_type = "branch"
        if children:
            branch_type = "parent branch"
        if self.options["children_only"]:
            branch_type = "child branch"

        compare = self.repo.compare_commits(branch, commit)
        if not compare or not compare.files:
            self.logger.info(f"Skipping {branch_type} {branch}: no file diffs found")
            return

        try:
            self.repo.merge(branch, commit)
            self.logger.info(
                f"Merged {compare.behind_by} commits into {branch_type} {branch}"
            )
            if children and not self.options["children_only"]:
                self.logger.info("  Skipping merge into the following child branches:")
                for child in children:
                    self.logger.info(f"    {child.name}")

        except GitHubError as e:
            if e.code != http.client.CONFLICT:
                raise

            if branch in self.existing_prs:
                self.logger.info(
                    f"Merge conflict on {branch_type} {branch}: merge PR already exists"
                )
                return

            pull = self.repo.create_pull(
                title=f"Merge {source} into {branch}",
                base=branch,
                head=source,
                body="This pull request was automatically generated because "
                "an automated merge hit a merge conflict",
            )

            self.logger.info(
                f"Merge conflict on {branch_type} {branch}: created pull request #{pull.number}"
            )


class MergeBranch(BaseGithubTask):
    task_options = {
        "commit": {
            "description": "The commit to merge into feature branches.  Defaults to the current head commit."
        },
        "source_branch": {
            "description": "The source branch to merge from.  Defaults to project__git__default_branch."
        },
        "branch_prefix": {
            "description": "A list of prefixes of branches that should receive the merge.  Defaults to project__git__prefix_feature"
        },
        "update_future_releases": {
            "description": "If source_branch is a release branch, then merge all future release branches that exist. Defaults to False."
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
        self.options["update_future_releases"] = process_bool_arg(
            self.options.get("update_future_releases", False)
        )

    def _run_task(self):
        self.repo = self.get_repo()
        self.source_branch_is_default = (
            self.options["source_branch"]
            == self.project_config.project__git__default_branch
        )
        self._validate_source_branch()
        self._get_existing_prs()

        branches_to_merge = self._get_branches_to_merge()

        for branch in branches_to_merge:
            self._merge(
                branch.name,
                self.options["source_branch"],
                self.options["commit"],
            )

    def _validate_source_branch(self):
        """Validates that the source branch exists in the repository"""
        try:
            self.repo.branch(self.options["source_branch"])
        except github3.exceptions.NotFoundError:
            message = f"Branch {self.options['source_branch']} not found"
            raise GithubApiNotFoundError(message)

    def _get_existing_prs(self):
        """Get existing pull requests from the source branch
        to other branches that are candidates for merging."""
        self.existing_prs = []
        for pr in self.repo.pull_requests(state="open"):
            if (
                pr.base.ref.startswith(self.options["branch_prefix"])
                and pr.head.ref == self.options["source_branch"]
            ):
                self.existing_prs.append(pr.base.ref)

    def _get_branches_to_merge(self):
        """
        If source_branch is the default branch, we
        gather all branches with branch_prefix that are not child branches.

        If source_branch is not the default branch, we gather
        all branches with branch_prefix that are direct descendents of source_branch.

        If update_future_releases is True, and source_branch is a release branch
        then we also collect all future release branches.
        """
        child_branches = []
        main_descendents = []
        release_branches = []
        for branch in self.repo.branches():
            if (
                self._is_release_branch(self.options["source_branch"])
                and self.options["update_future_releases"]
                and self._is_future_release_branch(branch.name)
            ):
                release_branches.append(branch)
                continue
            if branch.name == self.options["source_branch"]:
                self.logger.debug(f"Skipping branch {branch.name}: is source branch")
                continue
            elif not branch.name.startswith(self.options["branch_prefix"]):
                self.logger.debug(
                    f"Skipping branch {branch.name}: does not match prefix '{self.options['branch_prefix']}'"
                )
                continue
            elif self.source_branch_is_default and "__" not in branch.name:
                main_descendents.append(branch)
            elif self._is_source_branch_direct_descendent(branch):
                child_branches.append(branch)
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
        elif not self.source_branch_is_default:
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
                f"Found descendents of main to update: {[branch.name for branch in main_descendents]}"
            )
            to_merge = to_merge + main_descendents

        return to_merge

    def _merge(self, branch_name, source, commit):
        """Attempt to merge a commit from source to branch with branch_name"""
        compare = self.repo.compare_commits(branch_name, commit)
        if not compare or not compare.files:
            self.logger.info(f"Skipping branch {branch_name}: no file diffs found")
            return

        try:
            self.repo.merge(branch_name, commit)
            self.logger.info(
                f"Merged {compare.behind_by} commits into branch: {branch_name}"
            )

        except GitHubError as e:
            if e.code != http.client.CONFLICT:
                raise

            if branch_name in self.existing_prs:
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
            )

            self.logger.info(
                f"Merge conflict on branch {branch_name}: created pull request #{pull.number}"
            )

    def _is_source_branch_direct_descendent(self, branch):
        """Returns True if branch is a direct descendent of the source branch"""
        source_dunder_count = self.options["source_branch"].count("__")
        return (
            branch.name.startswith(f"{self.options['source_branch']}__")
            and branch.name.count("__") == source_dunder_count + 1
        )

    def _is_future_release_branch(self, branch_name):
        return (
            self._is_release_branch(branch_name)
            and branch_name != self.options["source_branch"]
            and self._get_release_num(branch_name)
            > self._get_release_num(self.options["source_branch"])
        )

    def _is_release_branch(self, branch_name):
        """A release branch begins with the given prefix"""
        prefix = self.options["branch_prefix"]
        if not branch_name.startswith(prefix):
            return False
        parts = branch_name[len(prefix) :].split("__")
        return len(parts) == 1 and parts[0].isdigit()

    def _get_release_num(self, release_branch_name):
        """Given a release branch, returns an integer that
        corresponds to the release number for that branch"""
        return int(release_branch_name.split(self.options["branch_prefix"])[1])
