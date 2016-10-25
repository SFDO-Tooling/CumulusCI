from datetime import datetime
from github3 import login
from cumulusci.core.tasks import BaseTask

class BaseGithubTask(BaseTask):

    def _init_task(self):
        self.github_config = self.project_config.keychain.get_github()
        self.github = login(
            username=self.github_config.username,
            password=self.github_config.password,
        )

    def get_repo(self):
        return self.github.repository(
            self.project_config.repo_owner,
            self.project_config.repo_name,
        )

class PullRequests(BaseGithubTask):
    
    def _run_task(self):
        repo = self.get_repo()
        for pr in repo.iter_pulls(state='open'):
            self.logger.info('#{}: {}'.format(pr.number, pr.title))

class CloneTag(BaseGithubTask):

    task_options = {
        'src_tag': {
            'description': 'The source tag to clone.  Ex: beta/1.0-Beta_2',
            'required': True,
        },
        'tag': {
            'description': 'The new tag to create by cloning the src tag.  Ex: release/1.0',
            'required': True,
        },
    }
    
    def _run_task(self):
        repo = self.get_repo()
        ref = repo.ref('tags/{}'.format(self.options['src_tag']))
        src_tag = repo.tag(ref.object.sha)
        if not src_tag:
            logger.error('Tag {} not found'.format(self.options['src_tag']))
            return

        tag = repo.create_tag(
            tag = self.options['tag'],
            message = 'Cloned from {}'.format(self.options['src_tag']),
            sha = src_tag.sha,
            obj_type = 'commit',
            tagger = {
                'name': self.github_config.username,
                'email': self.github_config.email,
                'date': '{}Z'.format(datetime.now().isoformat()),
            },
        )
        self.logger.info('Tag {} created by cloning {}'.format(self.options['tag'], self.options['src_tag']))

        return tag
