import httplib

import responses


class MockUtil(object):
    BASE_HTML_URL = 'https://github.com'
    BASE_API_URL = 'https://api.github.com'

    def __init__(self, owner, repo):
        self.owner = owner
        self.repo = repo

    @property
    def html_url(self):
        return '{}/{}/{}'.format(self.BASE_HTML_URL, self.owner, self.repo)

    @property
    def repo_url(self):
        return '{}/repos/{}/{}'.format(self.BASE_API_URL, self.owner, self.repo)

    def mock_edit_release(self, body=None, draft=True, prerelease=False):
        if body == None:
            body = 'Test release body'
        responses.add(
            method=responses.PATCH,
            url='{}/releases/1'.format(self.repo_url),
            json={
                'url': '{}/releases/1'.format(self.repo_url),
                'body': body,
                'draft': draft,
                'prerelease': prerelease,
            },
            status=httplib.OK,
        )

    def mock_get_repo(self):
        responses.add(
            method=responses.GET,
            url=self.repo_url,
            json={
                'url': self.repo_url,
            },
            status=httplib.OK,
        )

    def mock_list_pulls(self):
        responses.add(
            method=responses.GET,
            url='{}/pulls'.format(self.repo_url),
            json=[
                {
                    'id': 1,
                    'number': 1,
                },
            ],
            status=httplib.OK,
        )

    def mock_list_releases(self, tag=None, body=None):
        if tag == None:
            tag = 'v1.0'
        if body == None:
            body = 'Test release body'
        responses.add(
            method=responses.GET,
            url='{}/releases'.format(self.repo_url),
            json=[
                {
                    'tag_name': tag,
                    'url': '{}/releases/1'.format(self.repo_url),
                    'body': body,
                },
            ],
            status=httplib.OK,
        )

    def mock_post_comment(self, issue_number):
        responses.add(
            method=responses.POST,
            url='{}/issues/{}/comments'.format(self.repo_url, issue_number),
            status=httplib.OK,
        )

    def mock_pull_request(self, pr_number, body, title=None):
        if title == None:
            title = 'Test Pull Request Title'
        responses.add(
            method=responses.GET,
            url='{}/pulls/{}'.format(self.repo_url, pr_number),
            json={
                'base': {
                    'ref': 'master',
                },
                'body': body,
                'head': {
                    'ref': 'new-topic',
                },
                'html_url': '{}/pulls/{}'.format(self.html_url, pr_number),
                'issue_url': '{}/issues/{}'.format(self.repo_url, pr_number),
                'number': pr_number,
                'title': title,
            },
            status=httplib.OK,
        )
