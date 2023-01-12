import http.client

import responses

from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin


class MockUtilBase(GithubApiTestMixin):
    BASE_HTML_URL = "https://github.com"
    BASE_API_URL = "https://api.github.com"

    @property
    def html_url(self):
        return "{}/{}/{}".format(self.BASE_HTML_URL, self.owner, self.repo)

    @property
    def repo_url(self):
        return "{}/repos/{}/{}".format(self.BASE_API_URL, self.owner, self.repo)

    def mock_edit_release(self, body=None, draft=True, prerelease=False):
        if body is None:
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

    def mock_get_release(self, tag, body):
        responses.add(
            method=responses.GET,
            url="{}/releases/tags/{}".format(self.repo_url, tag),
            json=self._get_expected_release(
                tag, url="{}/releases/1".format(self.repo_url), body=body
            ),
            status=http.client.OK,
        )

    def mock_post_comment(self, issue_number):
        responses.add(
            method=responses.POST,
            url="{}/issues/{}/comments".format(self.repo_url, issue_number),
            status=http.client.OK,
        )

    def mock_pull_request(self, pr_number, body, title=None):
        if title is None:
            title = "Test Pull Request Title"
        responses.add(
            method=responses.GET,
            url="{}/pulls/{}".format(self.repo_url, pr_number),
            json=self._get_expected_pull_request(pr_number, pr_number, body=body),
            status=http.client.OK,
        )

    def mock_pulls(
        self, method=responses.GET, pulls=None, head=None, base=None, state=None
    ):
        # Default url params added by github3
        # see github3.repos.repo.py _Repository.pull_requests()
        params = ["sort=created", "direction=desc", "per_page=100"]
        default_num_params = len(params)
        params_added = False

        if head:
            params.append("head={}".format(head))
        if base:
            params.append("base={}".format(base))
        if state:
            params.append("state={}".format(state))

        if len(params) > default_num_params:
            params_added = True
            param_str = "?{}".format("&".join(params))

        api_url = "{}/pulls{}".format(self.repo_url, param_str if params_added else "")
        responses.add(method=method, url=api_url, json=pulls or [])

    def mock_issue(self, issue_num, labels=None, owner=None, repo=None):
        """Args:
        issue_num: int representing number of the issue
        labels: list(str) of labels to associate with the issue
        owner: str ownerof the repo
        repo: str name of the repo"""
        if not labels:
            labels = []

        self.add_issue_response(
            self._get_expected_issue(issue_num, owner=owner, repo=repo, labels=labels)
        )

    def add_issue_response(self, issue_json):
        responses.add(
            method=responses.GET,
            url="{}/issues/{}".format(self.repo_url, issue_json["number"]),
            json=issue_json,
            status=http.client.OK,
        )

    def mock_issue_labels(self, issue_num, method=responses.GET, labels=None):
        if not labels:
            labels = []
        responses.add(
            method=method,
            url="{}/issues/{}/labels".format(self.repo_url, issue_num),
            json=self._get_expected_labels(labels),
            status=http.client.OK,
        )

    def mock_add_labels_to_issue(self, issue_num, labels=None):
        if not labels:
            labels = []

        responses.add(
            method=responses.POST,
            url="{}/issues/{}/labels".format(self.repo_url, issue_num),
            json=self._get_expected_labels(labels),
            status=http.client.OK,
        )

    def mock_pull_request_by_commit_sha(self, commit_sha):
        responses.add(
            method=responses.GET,
            url="{}/commits/{}/pulls".format(self.repo_url, commit_sha),
            json=[self._get_expected_pull_request(1, 1)],
            status=http.client.OK,
        )


class MockUtil(MockUtilBase):
    def __init__(self, owner, repo):
        self.owner = owner
        self.repo = repo
        self.init_github()
