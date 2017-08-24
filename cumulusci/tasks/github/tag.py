from datetime import datetime

from cumulusci.core.exceptions import GithubException
from cumulusci.tasks.github.base import BaseGithubTask

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
            message = 'Tag {} not found'.format(self.options['src_tag'])
            logger.error(message)
            raise GithubException(message)

        tag = repo.create_tag(
            tag = self.options['tag'],
            message = 'Cloned from {}'.format(self.options['src_tag']),
            sha = src_tag.sha,
            obj_type = 'commit',
            tagger = {
                'name': self.github_config.username,
                'email': self.github_config.email,
                'date': '{}Z'.format(datetime.utcnow().isoformat()),
            },
        )
        self.logger.info('Tag {} created by cloning {}'.format(self.options['tag'], self.options['src_tag']))

        return tag
