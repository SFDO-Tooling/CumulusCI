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

    def _get_expected_issue(self, issue_number):
        response_body = {
            'title': 'Found a bug',
            'number': issue_number,
            'body': "I'm having a problem with this.",
        }
        return response_body

    def _get_expected_issue_comment(self, body):
        return {
            'body': body,
        }

    def _get_expected_tag_ref(self, tag, sha):
        return {
            'ref': 'refs/tags/{}'.format(tag),
            'object': {
                'type': 'tags',
                'sha': sha,
            }
        }

    def _get_expected_tag(self, tag, tag_sha, commit_sha, tag_date=None):
        if not tag_date:
            tag_date = datetime.now()

        tag_date = datetime.strftime(tag_date, date_format)
        return {
            'tag': tag,
            'sha': tag_sha,
            'tagger': {
                'date': tag_date,
            },
            'object': {
                'sha': commit_sha,
            },
        }

    def _random_sha(self):
        hash = random.getrandbits(128)
        return "%032x" % hash

    def _get_expected_pull_request(self, pull_id, issue_number, body, merged_date=None):
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
            'number': issue_number,
            'state': state,
            'title': 'Pull Request #{}'.format(issue_number),
            'body': body,
            'merged_at': merged_date,
            'head': {
                'ref': 'new-topic',
                'sha': commit_sha,
            },
            'base': {
                'ref': master_branch,
                'sha': commit_sha,
            },
            'merge_commit_sha': merge_sha,
            'merged': merged_date != None,
            'mergeable': True,
        }

    def _get_expected_release(self, body, draft, prerelease):
        return {
            'body': body,
            'draft': draft,
            'prerelease': prerelease,
        }

    def _get_expected_not_found(self):
        return {
            'message': 'Not Found',
            'documentation_url': 'https://developer.github.com/v3',
        }
