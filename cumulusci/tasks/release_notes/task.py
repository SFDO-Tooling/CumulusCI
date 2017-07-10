from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.github import BaseGithubTask
from generator import GithubReleaseNotesGenerator
from generator import PublishingGithubReleaseNotesGenerator


class GithubReleaseNotes(BaseGithubTask):

    task_options = {
        'tag': {
            'description': ('The tag to generate release notes for.' +
                ' Ex: release/1.2'),
            'required': True,
        },
        'publish': {
            'description': ('If True, publishes to the release matching the' +
                ' tag release notes were generated for.'),
        },
        'last_tag': {
            'description': ('Override the last release tag. This is useful' +
                ' to generate release notes if you skipped one or more' +
                ' releases.'),
        },
        'link_pr': {
            'description': ('If True, insert link to source pull request at' +
                ' end of each line.'),
        },
    }

    def _run_task(self):
        github_info = {
            'github_owner': self.project_config.repo_owner,
            'github_repo': self.project_config.repo_name,
            'github_username': self.github_config.username,
            'github_password': self.github_config.password,
            'master_branch': self.project_config.project__git__default_branch,
            'prefix_beta': self.project_config.project__git__prefix_beta,
            'prefix_prod': self.project_config.project__git__prefix_release,
        }

        if process_bool_arg(self.options.get('publish', False)):
            generator_class = PublishingGithubReleaseNotesGenerator
        else:
            generator_class = GithubReleaseNotesGenerator

        generator = generator_class(
            github_info,
            self.options['tag'],
            self.options.get('last_tag'),
            process_bool_arg(self.options.get('link_pr', False)),
            self.get_repo().has_issues,
        )

        release_notes = generator()
        self.logger.info('\n' + release_notes)
