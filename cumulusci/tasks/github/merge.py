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
            "description": "A list of prefixes of branches that should receive the merge.  Defaults to project__git__prefix_feature"
        },
        "children_only": {
            "description": "If True, merge will only be done to child branches.  This assumes source branch is a parent feature branch.  Defaults to False"
        },
    }

    def _init_options(self, kwargs):
        super(MergeBranch, self)._init_options(kwargs)

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

        self._validate_source_branch()
        self._get_existing_prs()
        branch_tree = self._get_branch_tree()
        self._merge_branches(branch_tree)

    def _validate_source_branch(self):
        try:
            self.repo.branch(self.options["source_branch"])
        except github3.exceptions.NotFoundError:
            message = f"Branch {self.options['source_branch']} not found"
            self.logger.error(message)
            raise GithubApiNotFoundError(message)

    def _get_existing_prs(self):
        """Get existing pull requests targeting the source branch"""
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
        double_underscores_in_source_branch = len(
            self.options["source_branch"].split("__")
        )
        for branch in branches:
            no_prefix = branch.name.replace(self.options["branch_prefix"], "", 1)
            parts = no_prefix.split("__")
            if len(parts) == double_underscores_in_source_branch + 1:
                possible_children.append(parts)
            else:
                possible_parents.append(branch.name)

        parents = {}
        children = []
        for possible_child in possible_children:
            name = "__".join(
                [part for part in possible_child[:double_underscores_in_source_branch]]
            )
            parent = f"{self.options['branch_prefix']}{name}"
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
        """Process merge on all branches in the tree"""
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
    }

    def _init_options(self, kwargs):
        super(MergeBranch, self)._init_options(kwargs)

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

    def _run_task(self):
        self.repo = self.get_repo()
        self.source_branch_is_default = (
            self.options["source_branch"]
            == self.project_config.project__git__default_branch
        )
        self._validate_source_branch()
        self._get_existing_prs()

        branches_to_merge = self._get_direct_descendent_branches()
        self._merge_branches(branches_to_merge)

    def _get_direct_descendent_branches(self):
        """
        If source_branch is the default branch, we
        gather all branches with branch_prefix that are not child branches.

        If is not the default branch, we gather
        all branches that are direct decendents of source_branch.
        """
        descendents = []
        for branch in self.repo.branches():
            if branch.name == self.options["source_branch"]:
                self.logger.debug(f"Skipping branch {branch.name}: is source branch")
                continue
            elif self.source_branch_is_default:
                if branch.name.startswith(self.options["branch_prefix"]):
                    if branch.name.count("__") == 0:
                        descendents.append(branch)
                    else:
                        self.logger.debug(
                            f"Skipping branch {branch.name}: is not a direct descendent of {self.options['source_branch']}"
                        )
                else:
                    self.logger.debug(
                        f"Skipping branch {branch.name}: does not match prefix {self.options['branch_prefix']}"
                    )

            elif self._is_source_branch_direct_descendent(branch):
                descendents.append(branch)

        return descendents

    def _is_default_direct_descendent(self, branch):
        return (
            branch.name.startswith(self.options["branch_prefix"])
            and "__" not in branch.name
        )

    def _is_source_branch_direct_descendent(self, branch):
        dunder_count = self.options["source_branch"].count("__")
        return (
            branch.name.startswith(f"{self.options['source_branch']}__")
            and branch.name.count("__") == dunder_count + 1
        )

    def _validate_source_branch(self):
        try:
            self.repo.branch(self.options["source_branch"])
        except github3.exceptions.NotFoundError:
            message = f"Branch {self.options['source_branch']} not found"
            self.logger.error(message)
            raise GithubApiNotFoundError(message)

    def _get_existing_prs(self):
        """Get existing pull requests targeting the source branch"""
        self.existing_prs = []
        for pr in self.repo.pull_requests(state="open"):
            if (
                pr.base.ref.startswith(self.options["branch_prefix"])
                and pr.head.ref == self.options["source_branch"]
            ):
                self.existing_prs.append(pr.base.ref)

    def _merge_branches(self, branches_to_merge):
        if not self.source_branch_is_default:
            if branches_to_merge:
                self.logger.info(
                    f"Performing merge from parent branch {self.options['source_branch']} to children"
                )
            else:
                self.logger.info(
                    f"No children found for branch {self.options['source_branch']}"
                )
                return

        for branch in branches_to_merge:
            self._merge(
                branch.name,
                self.options["source_branch"],
                self.options["commit"],
            )

    def _merge(self, branch_name, source, commit, children=None):
        branch_type = "child branch" if not self.source_branch_is_default else "branch"

        compare = self.repo.compare_commits(branch_name, commit)
        if not compare or not compare.files:
            self.logger.info(
                f"Skipping {branch_type} {branch_name}: no file diffs found"
            )
            return

        try:
            self.repo.merge(branch_name, commit)
            self.logger.info(
                f"Merged {compare.behind_by} commits into {branch_type} {branch_name}"
            )

        except GitHubError as e:
            if e.code != http.client.CONFLICT:
                raise

            if branch_name in self.existing_prs:
                self.logger.info(
                    f"Merge conflict on {branch_type} {branch_name}: merge PR already exists"
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
                f"Merge conflict on {branch_type} {branch_name}: created pull request #{pull.number}"
            )
