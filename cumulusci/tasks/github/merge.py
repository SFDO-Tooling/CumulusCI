from future import standard_library

standard_library.install_aliases()
import http.client

from github3 import GitHubError
import github3.exceptions

from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.github.base import BaseGithubTask


class MergeBranch(BaseGithubTask):

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

        self._validate_branch()
        self._get_existing_prs()
        branch_tree = self._get_branch_tree()
        self._merge_branches(branch_tree)

    def _validate_branch(self):
        try:
            self.repo.branch(self.options["source_branch"])
        except github3.exceptions.NotFoundError:
            message = "Branch {} not found".format(self.options["source_branch"])
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
        # Create list and dict of all target branches
        branches = []
        branches_dict = {}
        for branch in self.repo.branches():
            if branch.name == self.options["source_branch"]:
                if not self.options["children_only"]:
                    self.logger.debug(
                        "Skipping branch {}: is source branch".format(branch.name)
                    )
                    branches_dict[branch.name] = branch
                    continue
            if not branch.name.startswith(self.options["branch_prefix"]):
                if not self.options["children_only"]:
                    self.logger.debug(
                        "Skipping branch {}: does not match prefix {}".format(
                            branch.name, self.options["branch_prefix"]
                        )
                    )
                # The following line isn't included in coverage
                # due to behavior of the CPython peephole optimizer,
                # see https://bitbucket.org/ned/coveragepy/issues/198/continue-marked-as-not-covered
                continue  # pragma: nocover
            branches.append(branch)
            branches_dict[branch.name] = branch

        # Identify parent/child branches
        possible_children = []
        possible_parents = []
        parents = {}
        children = []
        for branch in branches:
            parts = branch.name.replace(self.options["branch_prefix"], "", 1).split(
                "__", 1
            )
            if len(parts) == 2:
                possible_children.append(parts)
            else:
                possible_parents.append(branch.name)

        for possible_child in possible_children:
            parent = "{}{}".format(self.options["branch_prefix"], possible_child[0])
            if parent in possible_parents:
                child = "__".join(possible_child)
                child = self.options["branch_prefix"] + child
                if parent not in parents:
                    parents[parent] = []
                parents[parent].append(child)
                children.append(child)

        # Build a branch tree list with parent/child branches
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
                        "Performing merge from parent branch {} to children".format(
                            self.options["source_branch"]
                        )
                    )
                else:
                    self.logger.info(
                        "No children found for branch {}".format(
                            self.options["source_branch"]
                        )
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
            self.logger.info(
                "Skipping {} {}: no file diffs found".format(branch_type, branch)
            )
            return

        try:
            result = self.repo.merge(branch, commit)
            self.logger.info(
                "Merged {} commits into {} {}".format(
                    compare.behind_by, branch_type, branch
                )
            )
            if children and not self.options["children_only"]:
                self.logger.info("  Skipping merge into the following child branches:")
                for child in children:
                    self.logger.info("    {}".format(child.name))

        except GitHubError as e:
            if e.code != http.client.CONFLICT:
                raise

            if branch in self.existing_prs:
                self.logger.info(
                    "Merge conflict on {} {}: merge PR already exists".format(
                        branch_type, branch
                    )
                )
                return

            pull = self.repo.create_pull(
                title="Merge {} into {}".format(source, branch),
                base=branch,
                head=source,
                body="This pull request was automatically generated because "
                "an automated merge hit a merge conflict",
            )

            self.logger.info(
                "Merge conflict on {} {}: created pull request #{}".format(
                    branch_type, branch, pull.number
                )
            )
