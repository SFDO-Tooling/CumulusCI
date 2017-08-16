import random

from datetime import datetime
from datetime import timedelta

import responses

date_format = '%Y-%m-%dT%H:%M:%SZ'

class GithubApiTestMixin(object):
    """ Mixin that provide common values and mocked http responses for tests of code that talks to the Github API """

    def init_github(self):
        self.repo_api_url = 'https://api.github.com/repos/TestOwner/TestRepo'
        self.github_info = {
            'github_owner': 'TestOwner',
            'github_repo': 'TestRepo',
            'github_username': 'TestUser',
            'github_password': 'TestPass',
        }

    def _get_expected_repo(self, owner, name):
        response_body = {
            "id": 1234567890,
            "name": name,
            "full_name": '{}/{}'.format(owner, name),
            "url": 'https://api.github.com/repos/{}/{}'.format(owner, name),
        }
        return response_body

    def _get_expected_branch(self, branch):
        response_body = {
            "id": 1234567890,
            "name": branch,
        }
        return response_body

    def _get_expected_pulls(self, pulls=None):
        if not pulls:
            pulls = []

        response_body = []
        for pull in pulls:
            response_body.append(self._get_expected_pull_request(**pull))
        return response_body

    def _get_expected_branches(self, branches=None):
        if not branches:
            branches = []

        response_body = []
        for branch in branches:
            response_body.append(self._get_expected_branch(**branch))
        return response_body

    def _get_expected_pull_request(self, pull_id, issue_number, merged_date=None):
        if merged_date:
            state = 'closed'
            merged_date = datetime.strftime(merged_date, date_format)
        else:
            state = 'open'

        commit_sha = self._random_sha()
        merge_sha = None
        if merged_date:
            merge_sha = self._random_sha()

        master_branch = self.github_info.get('master_branch', 'master')

        return {
            'id': pull_id,
            'html_url': 'http://example.com/pulls/{}'.format(issue_number),
            'number': issue_number,
            'state': state,
            'title': 'Pull Request #{}'.format(issue_number),
            'merged_at': merged_date,
            'head': {
                'ref': 'some-other-branch',
                'sha': commit_sha,
            },
            'base': {
                'ref': master_branch,
                'sha': commit_sha,
            },
            'merge_commit_sha': merge_sha,
            'merged': merged_date != None,
            'mergeable': not merged_date,
        }


    def _get_expected_not_found(self):
        return {
            'message': 'Not Found',
            'documentation_url': 'https://developer.github.com/v3',
        }
