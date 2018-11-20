from future import standard_library

standard_library.install_aliases()
import http.client
import responses

from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin


class MockUtil(GithubApiTestMixin):
    BASE_HTML_URL = "https://github.com"
    BASE_API_URL = "https://api.github.com"

    def __init__(self, owner, repo):
        self.owner = owner
        self.repo = repo
        self.init_github()

    @property
    def html_url(self):
        return "{}/{}/{}".format(self.BASE_HTML_URL, self.owner, self.repo)

    @property
    def repo_url(self):
        return "{}/repos/{}/{}".format(self.BASE_API_URL, self.owner, self.repo)

    def mock_edit_release(self, body=None, draft=True, prerelease=False):
        if body == None:
            body = "Test release body"
        responses.add(
            method=responses.PATCH,
            url="{}/releases/1".format(self.repo_url),
            json=self._get_expected_release(
                "1", body=body, draft=draft, prerelease=prerelease
            ),
            status=http.client.OK,
        )

    def mock_get_repo(self):
        responses.add(
            method=responses.GET,
            url=self.repo_url,
            json=self._get_expected_repo(self.owner, self.repo),
            status=http.client.OK,
        )

    def mock_list_pulls(self):
        responses.add(
            method=responses.GET,
            url="{}/pulls".format(self.repo_url),
            json=[{"id": 1, "number": 1}],
            status=http.client.OK,
        )

    def mock_list_releases(self, tag=None, body=None):
        if tag == None:
            tag = "v1.0"
        if body == None:
            body = "Test release body"
        responses.add(
            method=responses.GET,
            url="{}/releases".format(self.repo_url),
            json=[
                self._get_expected_release(
                    tag, url="{}/releases/1".format(self.repo_url), body=body
                )
            ],
            status=http.client.OK,
        )

    def mock_post_comment(self, issue_number):
        responses.add(
            method=responses.POST,
            url="{}/issues/{}/comments".format(self.repo_url, issue_number),
            status=http.client.OK,
        )

    def mock_pull_request(self, pr_number, body, title=None):
        if title == None:
            title = "Test Pull Request Title"
        responses.add(
            method=responses.GET,
            url="{}/pulls/{}".format(self.repo_url, pr_number),
            json=self._get_expected_pull_request(pr_number, pr_number, body=body),
            status=http.client.OK,
        )
