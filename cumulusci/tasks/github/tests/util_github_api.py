import random

from datetime import datetime
from datetime import timedelta

import responses

from cumulusci.tests.util import random_sha

date_format = "%Y-%m-%dT%H:%M:%SZ"


class GithubApiTestMixin(object):
    """ Mixin that provide common values and mocked http responses for tests of code that talks to the Github API """

    def init_github(self):
        self.repo_api_url = "https://api.github.com/repos/TestOwner/TestRepo"

    def _get_expected_repo(self, owner, name):
        html_url = "https://github.com/{}/{}".format(owner, name)
        url = "https://api.github.com/repos/{}/{}".format(owner, name)
        owner_url = "https://api.github.com/users/{}".format(owner)
        now = datetime.now().isoformat()
        response_body = {
            "id": 1234567890,
            "name": name,
            "description": "",
            "archived": False,
            "created_at": now,
            "default_branch": "master",
            "fork": False,
            "forks_count": 1,
            "full_name": "{}/{}".format(owner, name),
            "git_url": "git://github.com/{}/{}.git".format(owner, name),
            "has_downloads": False,
            "has_issues": False,
            "has_pages": False,
            "has_projects": False,
            "has_wiki": False,
            "homepage": "",
            "language": "Python",
            "mirror_url": None,
            "network_count": 0,
            "open_issues_count": 0,
            "owner": {
                "id": 1234567891,
                "login": owner,
                "url": owner_url,
                "type": "Organization",
                "site_admin": False,
                "avatar_url": "https://avatars2.githubusercontent.com/u/42554011?v=4",
                "gravatar_id": "",
                "html_url": "https://github.com/{}".format(owner),
                "followers_url": owner_url + "/followers",
                "following_url": owner_url + "/following{/other_user}",
                "gists_url": owner_url + "/gists{/gist_id}",
                "starred_url": owner_url + "/starred{/owner}{/repo}",
                "subscriptions_url": owner_url + "/subscriptions",
                "organizations_url": owner_url + "/orgs",
                "repos_url": owner_url + "/repos",
                "events_url": owner_url + "/events{/privacy}",
                "received_events_url": owner_url + "/received_events",
            },
            "pushed_at": now,
            "private": False,
            "size": 1,
            "ssh_url": "git@github.com:{}/{}.git".format(owner, name),
            "stargazers_count": 0,
            "subscribers_count": 0,
            "svn_url": html_url,
            "updated_at": now,
            "watchers_count": 0,
            "archive_url": url + "/{archive_format}{/ref}",
            "assignees_url": url + "/assignees{/user}",
            "blobs_url": url + "/git/blobs{/sha}",
            "branches_url": url + "/branches{/branch}",
            "clone_url": html_url + ".git",
            "collaborators_url": url + "/collaborators{/collaborator}",
            "comments_url": url + "/comments{/number}",
            "commits_url": url + "/commits{/sha}",
            "compare_url": url + "/compare/{base}...{head}",
            "contents_url": url + "/contents/{+path}",
            "contributors_url": url + "/CumulusCI/contributors",
            "deployments_url": url + "/CumulusCI/deployments",
            "downloads_url": url + "/downloads",
            "events_url": url + "/events",
            "forks_url": url + "/forks",
            "git_commits_url": url + "/git/commits{/sha}",
            "git_refs_url": url + "/git/refs{/sha}",
            "git_tags_url": url + "/git/tags{/sha}",
            "hooks_url": url + "/hooks",
            "html_url": html_url,
            "issue_comment_url": url + "/issues/comments{/number}",
            "issue_events_url": url + "/issues/events{/number}",
            "issues_url": url + "/issues{/number}",
            "keys_url": url + "/keys{/key_id}",
            "labels_url": url + "/labels{/name}",
            "languages_url": url + "/languages",
            "merges_url": url + "/merges",
            "milestones_url": url + "/milestones{/number}",
            "notifications_url": url + "/notifications{?since,all,participating}",
            "pulls_url": url + "/pulls{/number}",
            "releases_url": url + "/releases{/id}",
            "stargazers_url": url + "/stargazers",
            "statuses_url": url + "/statuses/{sha}",
            "subscribers_url": url + "/subscribers",
            "subscription_url": url + "/subscription",
            "tags_url": url + "/tags",
            "teams_url": url + "/teams",
            "trees_url": url + "/git/trees{/sha}",
            "url": url,
        }
        return response_body

    def _get_expected_branch(self, branch, commit=None):
        if not commit:
            commit = self._random_sha()
        response_body = {
            "id": 1234567890,
            "name": branch,
            "commit": {
                "sha": commit,
                "url": "",
                "author": None,
                "comments_url": "",
                "commit": {
                    "url": "",
                    "author": {},
                    "committer": {},
                    "message": "",
                    "tree": {"sha": "", "url": ""},
                },
                "committer": {},
                "html_url": "",
                "parents": [],
            },
            "_links": {},
            "protected": False,
            "protection": {},
            "protection_url": "",
        }
        return response_body

    def _get_expected_pulls(self, pulls=None):
        if not pulls:
            pulls = []
        return pulls

    def _get_expected_branches(self, branches=None):
        if not branches:
            branches = []

        response_body = []
        for branch in branches:
            response_body.append(self._get_expected_branch(**branch))
        return response_body

    def _get_expected_compare(self, base, head, files=None):
        if not files:
            files = []

        response_body = {
            "base_commit": {
                "url": "{}/commits/{}".format(self.repo_api_url, base),
                "sha": base,
                "author": None,
                "comments_url": "",
                "commit": {
                    "sha": "",
                    "url": "",
                    "author": {},
                    "committer": {},
                    "message": "",
                    "tree": {"sha": "", "url": ""},
                },
                "committer": {},
                "html_url": "",
                "parents": [],
            },
            "merge_base_commit": {
                "url": "{}/commits/{}".format(self.repo_api_url, head),
                "sha": head,
                "author": None,
                "comments_url": "",
                "commit": {
                    "sha": "",
                    "url": "",
                    "author": {},
                    "committer": {},
                    "message": "",
                    "tree": {"sha": "", "url": ""},
                },
                "committer": {},
                "html_url": "",
                "parents": [],
            },
            "ahead_by": 0,
            "behind_by": len(files),
            "commits": [],
            "diff_url": "",
            "files": files,
            "html_url": "",
            "patch_url": "",
            "permalink_url": "",
            "status": "",
            "total_commits": 0,
            "url": "",
        }
        return response_body

    def _get_expected_merge(self, conflict=None):
        if conflict:
            return {"message": "Merge Conflict"}

        new_commit = self._random_sha()
        response_body = {
            "sha": new_commit,
            "merged": True,
            "message": "Merged",
            "url": "",
            "author": None,
            "comments_url": "",
            "commit": {
                "sha": "",
                "url": "",
                "author": {},
                "committer": {},
                "message": "",
                "tree": {"sha": "", "url": ""},
            },
            "committer": {},
            "html_url": "",
            "parents": [],
        }
        return response_body

    def _get_expected_pull_request(self, pull_id, issue_number, merged_date=None):
        if merged_date:
            state = "closed"
            merged_date = datetime.strftime(merged_date, date_format)
        else:
            state = "open"

        commit_sha = self._random_sha()
        merge_sha = None
        if merged_date:
            merge_sha = self._random_sha()

        master_branch = self.project_config.project__git__default_branch
        return {
            "assignee": None,
            "assignees": [],
            "base": {"ref": master_branch, "sha": commit_sha, "label": ""},
            "body": "testing",
            "body_html": "testing",
            "body_text": "testing",
            "closed_at": merged_date,
            "comments_url": "",
            "commits_url": "",
            "created_at": merged_date,
            "diff_url": "",
            "head": {"ref": "some-other-branch", "sha": commit_sha, "label": ""},
            "html_url": "http://example.com/pulls/{}".format(issue_number),
            "id": pull_id,
            "issue_url": "{}/issues/{}".format(self.repo_api_url, issue_number),
            "_links": {},
            "merge_commit_sha": merge_sha,
            "mergeable": not merged_date,
            "merged_at": merged_date,
            "merged": merged_date != None,
            "number": issue_number,
            "patch_url": "",
            "review_comment_url": "",
            "review_comments_url": "",
            "state": state,
            "statuses_url": "",
            "title": "Pull Request #{}".format(issue_number),
            "updated_at": merged_date,
            "url": "http://example.com/pulls/{}".format(issue_number),
        }

    def _random_sha(self):
        return random_sha()

    def _get_expected_not_found(self):
        return {
            "message": "Not Found",
            "documentation_url": "https://developer.github.com/v3",
        }
