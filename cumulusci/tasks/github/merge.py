from github3 import GitHubError

from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.tasks.github.base import BaseGithubTask

class MergeBranch(BaseGithubTask):

    task_options = {
        'commit': {
            'description': "The commit to merge into feature branches.  Defaults to the current head commit.",
        },
        'source_branch': {
            'description': "The source branch to merge from.  Defaults to project__git__default_branch.",
        },
        'branch_prefix': {
            'description': "The prefix of branches that should receive the merge.  Defaults to project__git__prefix_feature",
        },
        'parent_child_only': {
            'description': "If True, only the parent to child branch merge is run.  Defaults to False",
        },
    }

    def _init_options(self, kwargs):
        super(MergeBranch, self)._init_options(kwargs)

        if 'commit' not in self.options:
            self.options['commit'] = self.project_config.repo_commit
        if 'branch_prefix' not in self.options:
            self.options['branch_prefix'] = self.project_config.project__git__prefix_feature
        if 'source_branch' not in self.options:
            self.options['source_branch'] = self.project_config.project__git__default_branch
        if 'parent_child_only' not in self.options:
            self.options['parent_child_only'] = False
        elif self.options['parent_child_only'] in [True, 'True']:
            self.options['parent_child_only'] = True

    def _run_task(self):
        self.repo = self.get_repo()

        commit = self.options['commit']
        branch_prefix = self.options['branch_prefix']
        source_branch = self.options['source_branch']
        parent_child_only = self.options['parent_child_only']

        head_branch = self.repo.branch(source_branch)
        if not head_branch:
            message = 'Branch {} not found'.format(source_branch)
            self.logger.error(message)
            raise GithubApiNotFoundError(message)

        # Get existing pull requests targeting a target branch
        self.existing_prs = []
        for pr in self.repo.iter_pulls(state='open'):
            if pr.base.ref.startswith(branch_prefix):
                self.existing_prs.append(pr.base.ref)
       
        # Create list and dict of all target branches 
        branches = []
        branches_dict = {}
        for branch in self.repo.iter_branches():
            if branch.name == source_branch:
                self.logger.debug('Skipping branch {}: is source branch'.format(branch.name))
                branches_dict[branch.name] = branch
                continue
            if not branch.name.startswith(branch_prefix):
                self.logger.info('Skipping branch {}: does not match prefix {}'.format(branch.name, branch_prefix))
                continue
            branches.append(branch)
            branches_dict[branch.name] = branch

        # Identify parent/child branches
        possible_children = []
        possible_parents = []
        parents = {}
        children = []
        for branch in branches:
            parts = branch.name.replace(branch_prefix, '', 1).split('__', 1)
            if len(parts) == 2:
                possible_children.append(parts)
            else:
                possible_parents.append(branch.name)

        for possible_child in possible_children:
            parent = '{}{}'.format(branch_prefix, possible_child[0])
            if parent in possible_parents:
                child = '__'.join(possible_child)
                child = branch_prefix + child
                if parent not in parents:
                    parents[parent] = []
                parents[parent].append(child)
                children.append(child)

        # Build a branch tree list with parent/child branches
        branch_tree = []
        for branch in branches:
            if branch.name in children:
                continue
            branch_item = {
                'branch': branch,
                'children': [],
            }
            for child in parents.get(branch.name,[]):
                branch_item['children'].append(branches_dict[child])
            
            branch_tree.append(branch_item)

        # Process merge on all branches
        for branch_item in branch_tree:
            branch = branch_item['branch']
            self._merge_recursive(
                branch_item['branch'],
                branches_dict[source_branch],
                branch_item['children'],
            )
                
  
    def _merge_recursive(self, branch, source, children=None, indent=None): 
        if not indent:
            indent = ''
        if not children:
            children = []
        branch_type = 'branch'
        if children:
            branch_type = 'parent branch'

        compare = self.repo.compare_commits(branch.commit.sha, source.commit.sha)
        if not compare.files:
            self.logger.info(
                'Skipping {} {}: no file diffs found'.format(
                    branch_type,
                    branch.name,
                )
            )
            return

        try: 
            result = self.repo.merge(branch.name, source.name)
            self.logger.info('{}Merged {} commits into {} {}'.format(
                indent,
                compare.behind_by,
                branch_type,
                branch.name,
            ))
            if children:
                self.logger.info('  Merging into child branches:')
                for child in children:
                    self._merge_recursive(
                        child,
                        branch,
                        indent = '    '
                    )

        except GitHubError as e:
            if e.code != 409:
                raise

            if branch.name in self.existing_prs:
                self.logger.info(
                    'Merge conflict on {} {}: merge PR already exists'.format(
                        branch_type,
                        branch.name,
                    )
                )
                return

            pull = self.repo.create_pull(
                title = 'Merge {} into {}'.format(source, branch.name),
                base = branch.name,
                head = source.name,
                body = 'This pull request was automatically generated because '
                       'an automated merge hit a merge conflict',
            )

            self.logger.info(
                'Merge conflict on {} {}: created pull request #{}'.format(
                    branch_type,
                    branch.name,
                    pull.number,
                )
            )
