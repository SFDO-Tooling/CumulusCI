""" Classes for interacting with the SFDO apextestsdb web app """

import httplib
import json

import requests

from cumulusci.core.exceptions import ApextestsdbError
from cumulusci.core.tasks import BaseTask


class BaseApextestsdbTask(BaseTask):
    """ base class for apextestsdb """

    def _init_task(self):
        self.apextestsdb_config = self.project_config.keychain.get_service(
            'apextestsdb'
        )
        self.execution_base_url = (
            self.apextestsdb_config.base_url + '/executions'
        )


class ApextestsdbUpload(BaseApextestsdbTask):
    """ upload test results to apextestsdb """

    task_options = {
        'branch_name': {
            'description': 'Name of branch where tests were run',
        },
        'commit_sha': {
            'description': 'Commit SHA from where tests were run',
        },
        'environment_name': {
            'description': 'Name of test environment',
            'required': True,
        },
        'execution_name': {
            'description': 'Name of test execution',
            'required': True,
        },
        'execution_url': {
            'description': 'URL of test execution',
            'required': True,
        },
        'results_file_url': {
            'description': 'URL of test results file',
            'required': True,
        },
    }

    def _init_task(self):
        super(ApextestsdbUpload, self)._init_task()
        self.upload_url = (
            self.apextestsdb_config.base_url + '/upload_test_result'
        )
        self.execution_base_url = (
            self.apextestsdb_config.base_url + '/executions'
        )

    def _init_options(self, kwargs):
        super(ApextestsdbUpload, self)._init_options(kwargs)
        if 'branch_name' not in self.options:
            self.options['branch_name'] = self.project_config.repo_branch
        if 'commit_sha' not in self.options:
            self.options['commit_sha'] = self.project_config.repo_commit

    def _run_task(self):
        payload = {
            'branch_name': self.options['branch_name'],
            'commit_sha': self.options['commit_sha'],
            'environment_name': self.options['environment_name'],
            'execution_name': self.options['execution_name'],
            'execution_url': self.options['execution_url'],
            'package': self.project_config.project__package__name,
            'repository_url': self.project_config.repo_url,
            'results_file_url': self.options['results_file_url'],
            'token': self.apextestsdb_config.token,
            'user': self.apextestsdb_config.user_id,
        }
        response = requests.post(self.upload_url, data=payload)
        if response.status_code >= httplib.BAD_REQUEST:
            raise ApextestsdbError('{}: {}'.format(
                response.status_code,
                response.content,
            ))
        data = json.loads(response.content)
        self.execution_id = data['execution_id']
        self.execution_url = '{}/{}'.format(
            self.execution_base_url,
            self.execution_id,
        )
        self.logger.info('Execution URL: %s', self.execution_url)
