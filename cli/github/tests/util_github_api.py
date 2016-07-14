import random

from datetime import datetime
from datetime import timedelta

import responses

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
            'id': 1,
            'url': 'https://api.github.com/repos/TestOwner/TestRepo/issues/{}'.format(issue_number),
            'repository_url': 'https://api.github.com/repos/TestOwner/TestRepo',
            'labels_url': 'https://api.github.com/repos/TestOwner/TestRepo/issues/{}/labels'.format(issue_number),
            'comments_url': 'https://api.github.com/repos/TestOwner/TestRepo/issues/{}/comments'.format(issue_number),
            'events_url': 'https://api.github.com/repos/TestOwner/TestRepo/issues/{}/events'.format(issue_number),
            'html_url': 'https://github.com/TestOwner/TestRepo/issues/{}'.format(issue_number),
            'number': issue_number,
            'state': 'open',
            'title': 'Found a bug',
            'body': "I'm having a problem with this.",
            'user': {
                'login': 'TestOwner',
                'id': 1,
                'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                'gravatar_id': '',
                'url': 'https://api.github.com/users/TestOwner',
                'html_url': 'https://github.com/TestOwner',
                'followers_url': 'https://api.github.com/users/TestOwner/followers',
                'following_url': 'https://api.github.com/users/TestOwner/following',
                'gists_url': 'https://api.github.com/users/TestOwner/gists{/gist_id}',
                'starred_url': 'https://api.github.com/users/TestOwner/starred',
                'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                'repos_url': 'https://api.github.com/users/TestOwner/repos',
                'events_url': 'https://api.github.com/users/TestOwner/events',
                'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                'type': 'User',
                'site_admin': False,
            },
            'labels': [
                {
                    'url': 'https://api.github.com/repos/TestOwner/TestRepo/labels/bug',
                    'name': 'bug',
                    'color': 'f29513',
                }
            ],
            'assignee': {
                'login': 'TestOwner',
                'id': 1,
                'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                'gravatar_id': '',
                'url': 'https://api.github.com/users/TestOwner',
                'html_url': 'https://github.com/TestOwner',
                'followers_url': 'https://api.github.com/users/TestOwner/followers',
                'following_url': 'https://api.github.com/users/TestOwner/following',
                'gists_url': 'https://api.github.com/users/TestOwner/gists',
                'starred_url': 'https://api.github.com/users/TestOwner/starred',
                'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                'repos_url': 'https://api.github.com/users/TestOwner/repos',
                'events_url': 'https://api.github.com/users/TestOwner/events',
                'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                'type': 'User',
                'site_admin': False,
            },
            'milestone': {
                'url': 'https://api.github.com/repos/TestOwner/TestRepo/milestones/1',
                'html_url': 'https://github.com/TestOwner/TestRepo/milestones/v1.0',
                'labels_url': 'https://api.github.com/repos/TestOwner/TestRepo/milestones/1/labels',
                'id': 1002604,
                'number': 1,
                'state': 'open',
                'title': 'v1.0',
                'description': 'Tracking milestone for version 1.0',
                'creator': {
                    'login': 'TestOwner',
                    'id': 1,
                    'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                    'gravatar_id': '',
                    'url': 'https://api.github.com/users/TestOwner',
                    'html_url': 'https://github.com/TestOwner',
                    'followers_url': 'https://api.github.com/users/TestOwner/followers',
                    'following_url': 'https://api.github.com/users/TestOwner/following',
                    'gists_url': 'https://api.github.com/users/TestOwner/gists',
                    'starred_url': 'https://api.github.com/users/TestOwner/starred',
                    'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                    'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                    'repos_url': 'https://api.github.com/users/TestOwner/repos',
                    'events_url': 'https://api.github.com/users/TestOwner/events',
                    'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                    'type': 'User',
                    'site_admin': False,
                },
                'open_issues': 4,
                'closed_issues': 8,
                'created_at': '2011-04-10T20:09:31Z',
                'updated_at': '2014-03-03T18:58:10Z',
                'closed_at': '2013-02-12T13:22:01Z',
                'due_on': '2012-10-09T23:39:01Z',
            },
            'locked': False,
            'comments': 0,
            'pull_request': {
                'url': 'https://api.github.com/repos/TestOwner/TestRepo/pulls/{}'.format(issue_number),
                'html_url': 'https://github.com/TestOwner/TestRepo/pull/{}'.format(issue_number),
                'diff_url': 'https://github.com/TestOwner/TestRepo/pull/{}.diff'.format(issue_number),
                'patch_url': 'https://github.com/TestOwner/TestRepo/pull/{}.patch'.format(issue_number),
            },
            'closed_at': None,
            'created_at': '2011-04-22T13:33:48Z',
            'updated_at': '2011-04-22T13:33:48Z',
            'closed_by': {
                'login': 'TestOwner',
                'id': 1,
                'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                'gravatar_id': '',
                'url': 'https://api.github.com/users/TestOwner',
                'html_url': 'https://github.com/TestOwner',
                'followers_url': 'https://api.github.com/users/TestOwner/followers',
                'following_url': 'https://api.github.com/users/TestOwner/following',
                'gists_url': 'https://api.github.com/users/TestOwner/gists',
                'starred_url': 'https://api.github.com/users/TestOwner/starred',
                'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                'repos_url': 'https://api.github.com/users/TestOwner/repos',
                'events_url': 'https://api.github.com/users/TestOwner/events',
                'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                'type': 'User',
                'site_admin': False,
            },
        }
        return response_body

    def _get_expected_tag_ref(self, tag, sha):
        return {
            'ref': 'refs/tags/{}'.format(tag),
            'url': 'https://api.github.com/repos/TestOwner/TestRepo/git/refs/tags/{}'.format(tag),
            'object': {
                'type': 'tags',
                'sha': sha,
                'url': 'https://api.github.com/repos/TestOwner/TestRepo/git/tags/{}'.format(sha),
            }
        }

    def _get_expected_tag(self, tag, sha, tag_date=None):
        if not tag_date:
            tag_date = datetime.now()
        
        tag_date = datetime.strftime(tag_date, "%Y-%m-%dT%H:%M:%SZ")

        return {
            'tag': tag,
            'sha': sha,
            'url': 'https://api.github.com/repos/TestOwner/TestRepo/git/tags/{}'.format(sha),
            'message': 'message',
            'tagger': {
                'name': 'Test User',
                'email': 'testuser@mailinator.com',
                'date': tag_date,
            },
            'object': {
                'type': 'commit',
                'sha': sha,
                'url': 'https://api.github.com/repos/TestOwner/TestRepo/git/commits/{}'.format(sha),
            },
        }

    def _random_sha(self):
        hash = random.getrandbits(128)
        return "%032x" % hash

    def _get_expected_pull_request(self, pull_id, issue_number, body, merged_date=None):
        if merged_date:
            state = 'closed'
            merged_date = datetime.strftime(merged_date, "%Y-%m-%dT%H:%M:%SZ")
        else:
            state = 'open'

        commit_sha = self._random_sha()
        merge_sha = None
        if merged_date:
            merge_sha = self._random_sha()

        master_branch = self.github_info.get('master_branch','master')

        return {
            'id': pull_id,
            'url': 'https://api.github.com/repos/TestOwner/TestRepo/pulls/{}'.format(issue_number),
            'html_url': 'https://github.com/TestOwner/TestRepo/pull/{}'.format(issue_number),
            'diff_url': 'https://github.com/TestOwner/TestRepo/pull/{}.diff'.format(issue_number),
            'patch_url': 'https://github.com/TestOwner/TestRepo/pull/{}.patch'.format(issue_number),
            'issue_url': 'https://api.github.com/repos/TestOwner/TestRepo/issues/{}'.format(issue_number),
            'commits_url': 'https://api.github.com/repos/TestOwner/TestRepo/pulls/{}/commits'.format(issue_number),
            'review_comments_url': 'https://api.github.com/repos/TestOwner/TestRepo/pulls/{}/comments'.format(issue_number),
            'review_comment_url': 'https://api.github.com/repos/TestOwner/TestRepo/pulls/comments/{number}',
            'comments_url': 'https://api.github.com/repos/TestOwner/TestRepo/issues/{}/comments'.format(issue_number),
            'statuses_url': 'https://api.github.com/repos/TestOwner/TestRepo/statuses/{}'.format(commit_sha),
            'number': issue_number,
            'state': state,
            'title': 'Pull Request #{}'.format(issue_number),
            'body': body,
            'assignee': {
                'login': 'TestOwner',
                'id': 1,
                'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                'gravatar_id': '',
                'url': 'https://api.github.com/users/TestOwner',
                'html_url': 'https://github.com/TestOwner',
                'followers_url': 'https://api.github.com/users/TestOwner/followers',
                'following_url': 'https://api.github.com/users/TestOwner/following{/other_user}',
                'gists_url': 'https://api.github.com/users/TestOwner/gists{/gist_id}',
                'starred_url': 'https://api.github.com/users/TestOwner/starred{/owner}{/repo}',
                'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                'repos_url': 'https://api.github.com/users/TestOwner/repos',
                'events_url': 'https://api.github.com/users/TestOwner/events{/privacy}',
                'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                'type': 'User',
                'site_admin': False
            },
            'milestone': {
                'url': 'https://api.github.com/repos/TestOwner/TestRepo/milestones/1',
                'html_url': 'https://github.com/TestOwner/TestRepo/milestones/v1.0',
                'labels_url': 'https://api.github.com/repos/TestOwner/TestRepo/milestones/1/labels',
                'id': 1002604,
                'number': 1,
                'state': 'open',
                'title': 'v1.0',
                'description': 'Tracking milestone for version 1.0',
                'creator': {
                    'login': 'TestOwner',
                    'id': 1,
                    'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                    'gravatar_id': '',
                    'url': 'https://api.github.com/users/TestOwner',
                    'html_url': 'https://github.com/TestOwner',
                    'followers_url': 'https://api.github.com/users/TestOwner/followers',
                    'following_url': 'https://api.github.com/users/TestOwner/following{/other_user}',
                    'gists_url': 'https://api.github.com/users/TestOwner/gists{/gist_id}',
                    'starred_url': 'https://api.github.com/users/TestOwner/starred{/owner}{/repo}',
                    'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                    'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                    'repos_url': 'https://api.github.com/users/TestOwner/repos',
                    'events_url': 'https://api.github.com/users/TestOwner/events{/privacy}',
                    'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                    'type': 'User',
                    'site_admin': False
                },
                'open_issues': 4,
                'closed_issues': 8,
                'created_at': '2011-04-10T20:09:31Z',
                'updated_at': '2014-03-03T18:58:10Z',
                'closed_at': '2013-02-12T13:22:01Z',
                'due_on': '2012-10-09T23:39:01Z'
            },
            'locked': False,
            'created_at': '2011-01-26T19:01:12Z',
            'updated_at': '2011-01-26T19:01:12Z',
            'closed_at': '2011-01-26T19:01:12Z',
            'merged_at': merged_date,
            'head': {
                'label': 'new-topic',
                'ref': 'new-topic',
                'sha': commit_sha,
                'user': {
                    'login': 'TestOwner',
                    'id': 1,
                    'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                    'gravatar_id': '',
                    'url': 'https://api.github.com/users/TestOwner',
                    'html_url': 'https://github.com/TestOwner',
                    'followers_url': 'https://api.github.com/users/TestOwner/followers',
                    'following_url': 'https://api.github.com/users/TestOwner/following{/other_user}',
                    'gists_url': 'https://api.github.com/users/TestOwner/gists{/gist_id}',
                    'starred_url': 'https://api.github.com/users/TestOwner/starred{/owner}{/repo}',
                    'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                    'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                    'repos_url': 'https://api.github.com/users/TestOwner/repos',
                    'events_url': 'https://api.github.com/users/TestOwner/events{/privacy}',
                    'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                    'type': 'User',
                    'site_admin': False
                },
                'repo': {
                    'id': 1296269,
                    'owner': {
                        'login': 'TestOwner',
                        'id': 1,
                        'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                        'gravatar_id': '',
                        'url': 'https://api.github.com/users/TestOwner',
                        'html_url': 'https://github.com/TestOwner',
                        'followers_url': 'https://api.github.com/users/TestOwner/followers',
                        'following_url': 'https://api.github.com/users/TestOwner/following{/other_user}',
                        'gists_url': 'https://api.github.com/users/TestOwner/gists{/gist_id}',
                        'starred_url': 'https://api.github.com/users/TestOwner/starred{/owner}{/repo}',
                        'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                        'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                        'repos_url': 'https://api.github.com/users/TestOwner/repos',
                        'events_url': 'https://api.github.com/users/TestOwner/events{/privacy}',
                        'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                        'type': 'User',
                        'site_admin': False
                    },
                    'name': 'TestRepo',
                    'full_name': 'TestOwner/TestRepo',
                    'description': 'This your first repo!',
                    'private': False,
                    'fork': True,
                    'url': 'https://api.github.com/repos/TestOwner/TestRepo',
                    'html_url': 'https://github.com/TestOwner/TestRepo',
                    'archive_url': 'http://api.github.com/repos/TestOwner/TestRepo/{archive_format}{/ref}',
                    'assignees_url': 'http://api.github.com/repos/TestOwner/TestRepo/assignees{/user}',
                    'blobs_url': 'http://api.github.com/repos/TestOwner/TestRepo/git/blobs{/sha}',
                    'branches_url': 'http://api.github.com/repos/TestOwner/TestRepo/branches{/branch}',
                    'clone_url': 'https://github.com/TestOwner/TestRepo.git',
                    'collaborators_url': 'http://api.github.com/repos/TestOwner/TestRepo/collaborators{/collaborator}',
                    'comments_url': 'http://api.github.com/repos/TestOwner/TestRepo/comments{/number}',
                    'commits_url': 'http://api.github.com/repos/TestOwner/TestRepo/commits{/sha}',
                    'compare_url': 'http://api.github.com/repos/TestOwner/TestRepo/compare/{base}...{head}',
                    'contents_url': 'http://api.github.com/repos/TestOwner/TestRepo/contents/{+path}',
                    'contributors_url': 'http://api.github.com/repos/TestOwner/TestRepo/contributors',
                    'deployments_url': 'http://api.github.com/repos/TestOwner/TestRepo/deployments',
                    'downloads_url': 'http://api.github.com/repos/TestOwner/TestRepo/downloads',
                    'events_url': 'http://api.github.com/repos/TestOwner/TestRepo/events',
                    'forks_url': 'http://api.github.com/repos/TestOwner/TestRepo/forks',
                    'git_commits_url': 'http://api.github.com/repos/TestOwner/TestRepo/git/commits{/sha}',
                    'git_refs_url': 'http://api.github.com/repos/TestOwner/TestRepo/git/refs{/sha}',
                    'git_tags_url': 'http://api.github.com/repos/TestOwner/TestRepo/git/tags{/sha}',
                    'git_url': 'git:github.com/TestOwner/TestRepo.git',
                    'hooks_url': 'http://api.github.com/repos/TestOwner/TestRepo/hooks',
                    'issue_comment_url': 'http://api.github.com/repos/TestOwner/TestRepo/issues/comments{/number}',
                    'issue_events_url': 'http://api.github.com/repos/TestOwner/TestRepo/issues/events{/number}',
                    'issues_url': 'http://api.github.com/repos/TestOwner/TestRepo/issues{/number}',
                    'keys_url': 'http://api.github.com/repos/TestOwner/TestRepo/keys{/key_id}',
                    'labels_url': 'http://api.github.com/repos/TestOwner/TestRepo/labels{/name}',
                    'languages_url': 'http://api.github.com/repos/TestOwner/TestRepo/languages',
                    'merges_url': 'http://api.github.com/repos/TestOwner/TestRepo/merges',
                    'milestones_url': 'http://api.github.com/repos/TestOwner/TestRepo/milestones{/number}',
                    'mirror_url': 'git:git.example.com/TestOwner/TestRepo',
                    'notifications_url': 'http://api.github.com/repos/TestOwner/TestRepo/notifications{?since, all, participating}',
                    'pulls_url': 'http://api.github.com/repos/TestOwner/TestRepo/pulls{/number}',
                    'releases_url': 'http://api.github.com/repos/TestOwner/TestRepo/releases{/id}',
                    'ssh_url': 'git@github.com:TestOwner/TestRepo.git',
                    'stargazers_url': 'http://api.github.com/repos/TestOwner/TestRepo/stargazers',
                    'statuses_url': 'http://api.github.com/repos/TestOwner/TestRepo/statuses/{sha}',
                    'subscribers_url': 'http://api.github.com/repos/TestOwner/TestRepo/subscribers',
                    'subscription_url': 'http://api.github.com/repos/TestOwner/TestRepo/subscription',
                    'svn_url': 'https://svn.github.com/TestOwner/TestRepo',
                    'tags_url': 'http://api.github.com/repos/TestOwner/TestRepo/tags',
                    'teams_url': 'http://api.github.com/repos/TestOwner/TestRepo/teams',
                    'trees_url': 'http://api.github.com/repos/TestOwner/TestRepo/git/trees{/sha}',
                    'homepage': 'https://github.com',
                    'language': None,
                    'forks_count': 9,
                    'stargazers_count': 80,
                    'watchers_count': 80,
                    'size': 108,
                    'default_branch': master_branch,
                    'open_issues_count': 0,
                    'has_issues': True,
                    'has_wiki': True,
                    'has_pages': False,
                    'has_downloads': True,
                    'pushed_at': '2011-01-26T19:06:43Z',
                    'created_at': '2011-01-26T19:01:12Z',
                    'updated_at': '2011-01-26T19:14:43Z',
                    'permissions': {
                        'admin': False,
                        'push': False,
                        'pull': True
                    }
                }
            },
            'base': {
                'label': master_branch,
                'ref': master_branch,
                'sha': commit_sha,
                'user': {
                    'login': 'TestOwner',
                    'id': 1,
                    'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                    'gravatar_id': '',
                    'url': 'https://api.github.com/users/TestOwner',
                    'html_url': 'https://github.com/TestOwner',
                    'followers_url': 'https://api.github.com/users/TestOwner/followers',
                    'following_url': 'https://api.github.com/users/TestOwner/following{/other_user}',
                    'gists_url': 'https://api.github.com/users/TestOwner/gists{/gist_id}',
                    'starred_url': 'https://api.github.com/users/TestOwner/starred{/owner}{/repo}',
                    'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                    'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                    'repos_url': 'https://api.github.com/users/TestOwner/repos',
                    'events_url': 'https://api.github.com/users/TestOwner/events{/privacy}',
                    'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                    'type': 'User',
                    'site_admin': False
                },
                'repo': {
                    'id': 1296269,
                    'owner': {
                        'login': 'TestOwner',
                        'id': 1,
                        'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                        'gravatar_id': '',
                        'url': 'https://api.github.com/users/TestOwner',
                        'html_url': 'https://github.com/TestOwner',
                        'followers_url': 'https://api.github.com/users/TestOwner/followers',
                        'following_url': 'https://api.github.com/users/TestOwner/following{/other_user}',
                        'gists_url': 'https://api.github.com/users/TestOwner/gists{/gist_id}',
                        'starred_url': 'https://api.github.com/users/TestOwner/starred{/owner}{/repo}',
                        'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                        'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                        'repos_url': 'https://api.github.com/users/TestOwner/repos',
                        'events_url': 'https://api.github.com/users/TestOwner/events{/privacy}',
                        'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                        'type': 'User',
                        'site_admin': False
                    },
                    'name': 'TestRepo',
                    'full_name': 'TestOwner/TestRepo',
                    'description': 'This your first repo!',
                    'private': False,
                    'fork': True,
                    'url': 'https://api.github.com/repos/TestOwner/TestRepo',
                    'html_url': 'https://github.com/TestOwner/TestRepo',
                    'archive_url': 'http://api.github.com/repos/TestOwner/TestRepo/{archive_format}{/ref}',
                    'assignees_url': 'http://api.github.com/repos/TestOwner/TestRepo/assignees{/user}',
                    'blobs_url': 'http://api.github.com/repos/TestOwner/TestRepo/git/blobs{/sha}',
                    'branches_url': 'http://api.github.com/repos/TestOwner/TestRepo/branches{/branch}',
                    'clone_url': 'https://github.com/TestOwner/TestRepo.git',
                    'collaborators_url': 'http://api.github.com/repos/TestOwner/TestRepo/collaborators{/collaborator}',
                    'comments_url': 'http://api.github.com/repos/TestOwner/TestRepo/comments{/number}',
                    'commits_url': 'http://api.github.com/repos/TestOwner/TestRepo/commits{/sha}',
                    'compare_url': 'http://api.github.com/repos/TestOwner/TestRepo/compare/{base}...{head}',
                    'contents_url': 'http://api.github.com/repos/TestOwner/TestRepo/contents/{+path}',
                    'contributors_url': 'http://api.github.com/repos/TestOwner/TestRepo/contributors',
                    'deployments_url': 'http://api.github.com/repos/TestOwner/TestRepo/deployments',
                    'downloads_url': 'http://api.github.com/repos/TestOwner/TestRepo/downloads',
                    'events_url': 'http://api.github.com/repos/TestOwner/TestRepo/events',
                    'forks_url': 'http://api.github.com/repos/TestOwner/TestRepo/forks',
                    'git_commits_url': 'http://api.github.com/repos/TestOwner/TestRepo/git/commits{/sha}',
                    'git_refs_url': 'http://api.github.com/repos/TestOwner/TestRepo/git/refs{/sha}',
                    'git_tags_url': 'http://api.github.com/repos/TestOwner/TestRepo/git/tags{/sha}',
                    'git_url': 'git:github.com/TestOwner/TestRepo.git',
                    'hooks_url': 'http://api.github.com/repos/TestOwner/TestRepo/hooks',
                    'issue_comment_url': 'http://api.github.com/repos/TestOwner/TestRepo/issues/comments{/number}',
                    'issue_events_url': 'http://api.github.com/repos/TestOwner/TestRepo/issues/events{/number}',
                    'issues_url': 'http://api.github.com/repos/TestOwner/TestRepo/issues{/number}',
                    'keys_url': 'http://api.github.com/repos/TestOwner/TestRepo/keys{/key_id}',
                    'labels_url': 'http://api.github.com/repos/TestOwner/TestRepo/labels{/name}',
                    'languages_url': 'http://api.github.com/repos/TestOwner/TestRepo/languages',
                    'merges_url': 'http://api.github.com/repos/TestOwner/TestRepo/merges',
                    'milestones_url': 'http://api.github.com/repos/TestOwner/TestRepo/milestones{/number}',
                    'mirror_url': 'git:git.example.com/TestOwner/TestRepo',
                    'notifications_url': 'http://api.github.com/repos/TestOwner/TestRepo/notifications{?since, all, participating}',
                    'pulls_url': 'http://api.github.com/repos/TestOwner/TestRepo/pulls{/number}',
                    'releases_url': 'http://api.github.com/repos/TestOwner/TestRepo/releases{/id}',
                    'ssh_url': 'git@github.com:TestOwner/TestRepo.git',
                    'stargazers_url': 'http://api.github.com/repos/TestOwner/TestRepo/stargazers',
                    'statuses_url': 'http://api.github.com/repos/TestOwner/TestRepo/statuses/{sha}',
                    'subscribers_url': 'http://api.github.com/repos/TestOwner/TestRepo/subscribers',
                    'subscription_url': 'http://api.github.com/repos/TestOwner/TestRepo/subscription',
                    'svn_url': 'https://svn.github.com/TestOwner/TestRepo',
                    'tags_url': 'http://api.github.com/repos/TestOwner/TestRepo/tags',
                    'teams_url': 'http://api.github.com/repos/TestOwner/TestRepo/teams',
                    'trees_url': 'http://api.github.com/repos/TestOwner/TestRepo/git/trees{/sha}',
                    'homepage': 'https://github.com',
                    'language': None,
                    'forks_count': 9,
                    'stargazers_count': 80,
                    'watchers_count': 80,
                    'size': 108,
                    'default_branch': master_branch,
                    'open_issues_count': 0,
                    'has_issues': True,
                    'has_wiki': True,
                    'has_pages': False,
                    'has_downloads': True,
                    'pushed_at': '2011-01-26T19:06:43Z',
                    'created_at': '2011-01-26T19:01:12Z',
                    'updated_at': '2011-01-26T19:14:43Z',
                    'permissions': {
                        'admin': False,
                        'push': False,
                        'pull': True
                    }
                }
            },
            '_links': {
                'self': {
                    'href': 'https://api.github.com/repos/TestOwner/TestRepo/pulls/{}'.format(issue_number)
                },
                'html': {
                    'href': 'https://github.com/TestOwner/TestRepo/pull/{}'.format(issue_number)
                },
                'issue': {
                    'href': 'https://api.github.com/repos/TestOwner/TestRepo/issues/{}'.format(issue_number)
                },
                'comments': {
                    'href': 'https://api.github.com/repos/TestOwner/TestRepo/issues/{}/comments'.format(issue_number)
                },
                'review_comments': {
                    'href': 'https://api.github.com/repos/TestOwner/TestRepo/pulls/{}/comments'.format(issue_number)
                },
                'review_comment': {
                    'href': 'https://api.github.com/repos/TestOwner/TestRepo/pulls/comments/{number}'
                },
                'commits': {
                    'href': 'https://api.github.com/repos/TestOwner/TestRepo/pulls/{}/commits'.format(issue_number)
                },
                'statuses': {
                    'href': 'https://api.github.com/repos/TestOwner/TestRepo/statuses/{}'.format(commit_sha)
                }
            },
            'user': {
                'login': 'TestOwner',
                'id': 1,
                'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                'gravatar_id': '',
                'url': 'https://api.github.com/users/TestOwner',
                'html_url': 'https://github.com/TestOwner',
                'followers_url': 'https://api.github.com/users/TestOwner/followers',
                'following_url': 'https://api.github.com/users/TestOwner/following{/other_user}',
                'gists_url': 'https://api.github.com/users/TestOwner/gists{/gist_id}',
                'starred_url': 'https://api.github.com/users/TestOwner/starred{/owner}{/repo}',
                'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                'repos_url': 'https://api.github.com/users/TestOwner/repos',
                'events_url': 'https://api.github.com/users/TestOwner/events{/privacy}',
                'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                'type': 'User',
                'site_admin': False
            },
            'merge_commit_sha': merge_sha,
            'merged': False,
            'mergeable': True,
            'merged_by': {
                'login': 'TestOwner',
                'id': 1,
                'avatar_url': 'https://github.com/images/error/TestOwner_happy.gif',
                'gravatar_id': '',
                'url': 'https://api.github.com/users/TestOwner',
                'html_url': 'https://github.com/TestOwner',
                'followers_url': 'https://api.github.com/users/TestOwner/followers',
                'following_url': 'https://api.github.com/users/TestOwner/following{/other_user}',
                'gists_url': 'https://api.github.com/users/TestOwner/gists{/gist_id}',
                'starred_url': 'https://api.github.com/users/TestOwner/starred{/owner}{/repo}',
                'subscriptions_url': 'https://api.github.com/users/TestOwner/subscriptions',
                'organizations_url': 'https://api.github.com/users/TestOwner/orgs',
                'repos_url': 'https://api.github.com/users/TestOwner/repos',
                'events_url': 'https://api.github.com/users/TestOwner/events{/privacy}',
                'received_events_url': 'https://api.github.com/users/TestOwner/received_events',
                'type': 'User',
                'site_admin': False
            },
            'comments': 10,
            'commits': 3,
            'additions': 100,
            'deletions': 3,
            'changed_files': 5
        }

