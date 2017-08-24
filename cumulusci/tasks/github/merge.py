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
    }

    def _run_task(self):
        repo = self.get_repo()

        commit = self.options.get('commit', self.project_config.repo_commit)
        branch_prefix = self.options.get('branch_prefix', self.project_config.project__git__prefix_feature)
        source_branch = self.options.get('source_branch', self.project_config.project__git__default_branch)

        head_branch = repo.branch(source_branch)
        if not head_branch:
            message = 'Branch {} not found'.format(source_branch)
            self.logger.error(message)
            raise GithubApiNotFoundError(message)

        # Get existing pull requests targeting a target branch
        existing_prs = []
        for pr in repo.iter_pulls(state='open'):
            if pr.base.ref.startswith(branch_prefix):
                existing_prs.append(pr.base.ref)
        
        targets = []
        for branch in repo.iter_branches():
            if not branch.name.startswith(branch_prefix):
                self.logger.info('Skipping branch {}: does not match prefix {}'.format(branch.name, branch_prefix))
                continue
            if branch.name == source_branch:
                self.logger.info('Skipping branch {}: is source branch'.format(branch.name))
                continue
               
            compare = repo.compare_commits(branch.commit.sha, commit)
            if not compare.files:
                self.logger.info('Skipping branch {}: no file diffs found'.format(branch.name))
                continue
   
            try: 
                result = repo.merge(branch.name, source_branch)
                self.logger.info('Merged {} commits into {}'.format(compare.behind_by, branch.name))
            except GitHubError as e:
                if e.code != 409:
                    raise

                if branch.name in existing_prs:
                    self.logger.info('Merge conflict on branch {}: merge PR already exists'.format(branch.name))
                    continue 

                pull = repo.create_pull(
                    title = 'Merge {} into {}'.format(source_branch, branch.name),
                    base = branch.name,
                    head = source_branch,
                    body = 'This pull request was automatically generated because an automated merge hit a merge conflict',
                )

                self.logger.info('Merge conflict on branch {}: created pull request #{}'.format(branch.name, pull.number))
