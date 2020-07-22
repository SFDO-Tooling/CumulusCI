from random import randint, choice
from string import digits, ascii_lowercase
from datetime import datetime
from cumulusci.tests.util import random_sha

date_format = "%Y-%m-%dT%H:%M:%SZ"


class GithubApiTestMixin(object):
    """ Mixin that provide common values and mocked http responses for tests of code that talks to the Github API """

    def init_github(self):
        self.repo_api_url = "https://api.github.com/repos/TestOwner/TestRepo"
        self.github_info = {
            "github_owner": "TestOwner",
            "github_repo": "TestRepo",
            "github_username": "TestUser",
            "github_password": "TestPass",
            "prefix_beta": "beta/",
            "prefix_prod": "release/",
            "default_branch": "main",
        }

    def _get_expected_user(self, name):
        user_url = "https://api.github.com/users/{}".format(name)
        return {
            "id": 1234567892,
            "login": name,
            "url": user_url,
            "type": "User",
            "site_admin": False,
            "avatar_url": "https://avatars2.githubusercontent.com/u/42554011?v=4",
            "gravatar_id": "",
            "html_url": "https://github.com/{}".format(name),
            "followers_url": user_url + "/followers",
            "following_url": user_url + "/following{/other_user}",
            "gists_url": user_url + "/gists{/gist_id}",
            "starred_url": user_url + "/starred{/owner}{/repo}",
            "subscriptions_url": user_url + "/subscriptions",
            "organizations_url": user_url + "/orgs",
            "repos_url": user_url + "/repos",
            "events_url": user_url + "/events{/privacy}",
            "received_events_url": user_url + "/received_events",
        }

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
            "default_branch": "main",
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

    def _get_expected_tag(self, name, commit_sha, tag_sha=None, tag_date=None):
        if tag_sha is None:
            tag_sha = self._random_sha()
        if not tag_date:
            tag_date = datetime.utcnow()
        tag_date = datetime.strftime(tag_date, date_format)
        return {
            "sha": tag_sha,
            "url": "",
            "message": "",
            "object": {"url": "", "sha": commit_sha, "type": "commit"},
            "tag": name,
            "tagger": {"date": tag_date},
        }

    def _get_expected_tag_ref(self, tag, sha):
        return {
            "ref": "refs/tags/{}".format(tag),
            "object": {"type": "tag", "sha": sha, "url": ""},
            "name": tag,
            "url": "",
        }

    def _get_expected_ref(self, ref, sha, type="commit"):
        return {
            "ref": f"refs/{ref}",
            "object": {"type": "commit", "sha": sha, "url": ""},
            "name": ref,
            "url": "",
        }

    def _get_expected_repo_tag(self, tag, sha):
        return {
            "name": tag,
            "commit": {"sha": sha, "url": ""},
            "tarball_url": "",
            "zipball_url": "",
        }

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

    def _get_expected_pull_request(
        self, pull_id, issue_number, body=None, merged_date=None, **kw
    ):
        if merged_date:
            state = "closed"
            merged_date = datetime.strftime(merged_date, date_format)
        else:
            state = "open"

        commit_sha = self._random_sha()
        merge_sha = None
        if merged_date:
            merge_sha = self._random_sha()

        base_repo = self._get_expected_repo("TestOwner", "TestRepo")
        if hasattr(self, "project_config"):
            default_branch = self.project_config.project__git__default_branch
        else:
            default_branch = "main"
        pr = {
            "additions": [],
            "assignee": None,
            "assignees": [],
            "base": {
                "ref": default_branch,
                "sha": commit_sha,
                "label": "",
                "repo": base_repo,
            },
            "body": body or "testing",
            "body_html": "testing",
            "body_text": "testing",
            "closed_at": merged_date,
            "comments": [],
            "comments_url": "",
            "commits": [],
            "commits_url": "",
            "created_at": merged_date,
            "deletions": [],
            "diff_url": "",
            "head": {"ref": "some-other-branch", "sha": commit_sha, "label": ""},
            "html_url": "https://github.com/TestOwner/TestRepo/pulls/{}".format(
                issue_number
            ),
            "id": pull_id,
            "issue_url": "{}/issues/{}".format(self.repo_api_url, issue_number),
            "_links": {},
            "merge_commit_sha": merge_sha,
            "mergeable": not merged_date,
            "mergeable_state": "clean",
            "merged_at": merged_date,
            "merged": merged_date is not None,
            "merged_by": None,
            "number": issue_number,
            "patch_url": "",
            "review_comment_url": "",
            "review_comments": [],
            "review_comments_url": "",
            "state": state,
            "statuses_url": "",
            "title": "Pull Request #{}".format(issue_number),
            "updated_at": merged_date,
            "url": "https://github.com/TestOwner/TestRepo/pulls/{}".format(
                issue_number
            ),
            "user": base_repo["owner"],
        }
        pr.update(kw)
        return pr

    def _get_expected_pull_requests(self, num_pull_requests):
        return [self._get_expected_pull_request(i, i) for i in range(num_pull_requests)]

    def _get_expected_issue(self, issue_number, owner=None, repo=None, labels=None):
        if owner is None:
            owner = "TestOwner"
        if repo is None:
            repo = "TestRepo"
        now = datetime.now().isoformat()
        response_body = {
            "assignee": None,
            "assignees": [],
            "body": "I'm having a problem with this.",
            "body_html": "",
            "body_text": "",
            "closed_at": None,
            "closed_by": None,
            "comments": [],
            "comments_url": "",
            "created_at": now,
            "events_url": "",
            "html_url": "https://github.com/{}/{}/issues/{}".format(
                owner, repo, issue_number
            ),
            "id": issue_number,
            "labels": labels or [],
            "labels_url": "",
            "locked": False,
            "milestone": None,
            "number": issue_number,
            "state": "open",
            "title": "Found a bug",
            "updated_at": now,
            "url": "https://api.github.com/repos/{}/{}/issues/{}".format(
                owner, repo, issue_number
            ),
            "user": self._get_expected_user("user"),
        }
        return response_body

    def _get_expected_issue_comment(self, body):
        now = datetime.now().isoformat()
        return {
            "author_association": "",
            "body": body,
            "body_html": "",
            "body_text": "",
            "created_at": now,
            "url": "",
            "html_url": "",
            "id": 0,
            "issue_url": "",
            "updated_at": now,
            "user": self._get_expected_user("user"),
        }

    def _get_expected_release(self, tag_name, **kw):
        now = datetime.now().isoformat()
        release = {
            "url": "https://release",
            "assets": [],
            "assets_url": "",
            "author": self._get_expected_user("author"),
            "body": "",
            "created_at": now,
            "draft": False,
            "html_url": "",
            "id": 1,
            "name": "release",
            "prerelease": False,
            "published_at": now,
            "tag_name": tag_name,
            "tarball_url": "",
            "target_commitish": "",
            "upload_url": "",
            "zipball_url": "",
        }
        release.update(kw)
        return release

    def _random_sha(self):
        return random_sha()

    def _get_expected_not_found(self):
        return {
            "message": "Not Found",
            "documentation_url": "https://developer.github.com/v3",
        }

    def _get_expected_label(self, name=None, desc=None):
        return {
            "id": randint(100000000, 999999999),
            "node_id": "MDU6TGFiZWwyMDgwNDU5NDY=",
            "url": "https://api.github.com/repos/octocat/Hello-World/labels/bug",
            "name": name or "Test Label",
            "description": desc or "Test label description.",
            "color": "f29513",
            "default": False,
        }

    def _get_expected_labels(self, labels):
        return [self._get_expected_label(name=label) for label in labels]

    def _get_expected_gist(self, description, files, public=False):
        """Gist creationg returns 201 on success"""
        gh_id = self.create_id(20)

        gist_files = {}
        for filename, content in files.items():
            gist_files[filename] = {
                "filename": filename,
                "type": "text/plain",
                "language": "text",
                "raw_url": f"https://gist.githubusercontent.com/octocat/{gh_id}/raw/99c1bf3a345505c2e6195198d5f8c36267de570b/hello_world.py",
                "size": 199,
                "truncated": False,
                "content": content,
            }

        expected_gist = {
            "url": f"https://api.github.com/gists/{gh_id}",
            "forks_url": f"https://api.github.com/gists/{gh_id}/forks",
            "commits_url": f"https://api.github.com/gists/{gh_id}/commits",
            "id": gh_id,
            "node_id": "MDQ6R2lzdGFhNWEzMTVkNjFhZTk0MzhiMThk",
            "git_pull_url": f"https://gist.github.com/{gh_id}.git",
            "git_push_url": f"https://gist.github.com/{gh_id}.git",
            "html_url": f"https://gist.github.com/{gh_id}",
            "files": gist_files,
            "public": public,
            "created_at": "2010-04-14T02:15:15Z",
            "updated_at": "2011-06-20T11:34:15Z",
            "description": "Hello World Examples",
            "comments": 0,
            "user": None,
            "comments_url": f"https://api.github.com/gists/{gh_id}/comments/",
            "owner": {
                "login": "octocat",
                "id": 1,
                "node_id": "MDQ6VXNlcjE=",
                "avatar_url": "https://github.com/images/error/octocat_happy.gif",
                "gravatar_id": "",
                "url": "https://api.github.com/users/octocat",
                "html_url": "https://github.com/octocat",
                "followers_url": "https://api.github.com/users/octocat/followers",
                "following_url": "https://api.github.com/users/octocat/following{/other_user}",
                "gists_url": "https://api.github.com/users/octocat/gists{/gist_id}",
                "starred_url": "https://api.github.com/users/octocat/starred{/owner}{/repo}",
                "subscriptions_url": "https://api.github.com/users/octocat/subscriptions",
                "organizations_url": "https://api.github.com/users/octocat/orgs",
                "repos_url": "https://api.github.com/users/octocat/repos",
                "events_url": "https://api.github.com/users/octocat/events{/privacy}",
                "received_events_url": "https://api.github.com/users/octocat/received_events",
                "type": "User",
                "site_admin": False,
            },
            "truncated": False,
            "forks": [],
            "history": [
                {
                    "url": "https://api.github.com/gists/aa5a315d61ae9438b18d/57a7f021a713b1c5a6a199b54cc514735d2d462f",
                    "version": "57a7f021a713b1c5a6a199b54cc514735d2d462f",
                    "user": {
                        "login": "octocat",
                        "id": 1,
                        "node_id": "MDQ6VXNlcjE=",
                        "avatar_url": "https://github.com/images/error/octocat_happy.gif",
                        "gravatar_id": "",
                        "url": "https://api.github.com/users/octocat",
                        "html_url": "https://github.com/octocat",
                        "followers_url": "https://api.github.com/users/octocat/followers",
                        "following_url": "https://api.github.com/users/octocat/following{/other_user}",
                        "gists_url": "https://api.github.com/users/octocat/gists{/gist_id}",
                        "starred_url": "https://api.github.com/users/octocat/starred{/owner}{/repo}",
                        "subscriptions_url": "https://api.github.com/users/octocat/subscriptions",
                        "organizations_url": "https://api.github.com/users/octocat/orgs",
                        "repos_url": "https://api.github.com/users/octocat/repos",
                        "events_url": "https://api.github.com/users/octocat/events{/privacy}",
                        "received_events_url": "https://api.github.com/users/octocat/received_events",
                        "type": "User",
                        "site_admin": False,
                    },
                    "change_status": {"deletions": 0, "additions": 180, "total": 180},
                    "committed_at": "2010-04-14T02:15:15Z",
                }
            ],
        }
        return expected_gist

    def create_id(self, length):
        characters = [*digits, *ascii_lowercase]
        return "".join([choice(characters) for i in range(length)])
