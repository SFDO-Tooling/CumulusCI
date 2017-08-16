import ast
import httplib
import os
import shutil
import tempfile
import unittest

import requests
import responses

from datetime import datetime
from datetime import timedelta
from testfixtures import LogCapture

from cumulusci.tests.util import create_project_config
from cumulusci.tests.util import DummyOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig

from cumulusci.tasks.github import MergeBranch
from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin


class TestMergeBranch(unittest.TestCase, GithubApiTestMixin):

    def setUp(self):

        # Set up the mock values
        self.repo_name = 'TestRepo'
        self.repo_owner = 'TestOwner'
        self.repo_api_url = 'https://api.github.com/repos/{}/{}'.format(
            self.repo_owner,
            self.repo_name,
        )
        self.branch = 'master'

        # Create the project config
        self.project_config = create_project_config(
            self.repo_name,
            self.repo_owner,
        )
        self.project_config.keychain.set_service(
            'github',
            ServiceConfig({ 
                'username': 'TestUser',
                'password': 'TestPass',
                'email': 'testuser@testdomain.com',
            })
        )
        
        #self.current_tag_sha = self._random_sha()
        #self.current_tag_commit_sha = self._random_sha()
        #self.current_tag_commit_date = datetime.utcnow()
        #self.last_tag_sha = self._random_sha()
        #self.last_tag_commit_sha = self._random_sha()
        #self.last_tag_commit_date = datetime.utcnow() - timedelta(days=1)

    def _create_task(self, task_config=None):
        if not task_config:
            
            task_config = {}
        task = MergeBranch(
            project_config = self.project_config,
            task_config = TaskConfig(task_config),
            org_config = DummyOrgConfig(),
        )
        return task

    def _mock_repo(self):
        api_url = self.repo_api_url
        
        expected_response = self._get_expected_repo(
            owner = self.repo_owner,
            name = self.repo_name,
        )
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
        )
        return expected_response

    def _mock_branch(self, branch, expected_response=None):
        api_url = '{}/branches/{}'.format(self.repo_api_url, branch)
        if not expected_response:
            expected_response = self._get_expected_branch(branch)
        responses.add(
            method = responses.GET,
            url = api_url,
            json = expected_response,
        )

    def _mock_branches(self, branches=None):
        api_url = '{}/branches'.format(self.repo_api_url)
        expected_response = self._get_expected_branches(branches=branches)
        
        responses.add(
            method = responses.GET,
            url = api_url,
            json = expected_response,
        )

    def _mock_branch_does_not_exist(self, branch):
        api_url = '{}/branches/{}'.format(self.repo_api_url, branch)
        expected_response = self._get_expected_not_found()
        responses.add(
            method = responses.GET,
            url = api_url,
            status = 404,
            json = expected_response,
        )

    def _mock_pulls(self, pulls=None):
        api_url = '{}/pulls'.format(self.repo_api_url)
        expected_response = self._get_expected_pulls(pulls=pulls)
        
        responses.add(
            method = responses.GET,
            url = api_url,
            json = expected_response,
        )

    @responses.activate
    def test_branch_does_not_exist(self):
        self._mock_repo()
        self._mock_branch_does_not_exist(self.branch)

        task = self._create_task()
        with self.assertRaises(GithubApiNotFoundError):
            task()

    @responses.activate
    def test_no_feature_branch(self):
        self._mock_repo()
        self._mock_branch(self.branch)
        self._mock_pulls()
        self._mock_branches()
        with LogCapture() as l:
            task = self._create_task()
            task()
            log_lines = []
            for event in l.records:
                if event.name != 'cumulusci.core.tasks':
                    continue
                log_lines.append((event.levelname, event.getMessage()))
                    
            expected = [
                ('INFO', 'Beginning task: MergeBranch'),
                ('INFO', ''),
            ]
            self.assertEquals(log_lines, expected)
