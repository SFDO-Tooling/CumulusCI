import unittest
import json

from mock import patch
from github_commands.get_tags import get_github_organization, get_tags_from_repo


class TestGetTags(unittest.TestCase):

    class RefData(object):

        def __init__(self, ref, url, object):
            self.ref = ref
            self.url = url
            self.object = object


    class ObjectData(object):

        def __init__(self, type, sha, url):
            self.type = type
            self.sha = sha
            self.url = url

    @patch('github.Github')
    def test_get_github_organization_by_user(self, mock_github):
        mock_github.get_organization.side_effect = Exception('I dont care')
        user_result = {'name': 'org'}
        mock_github.get_user.return_value = user_result
        result = get_github_organization(mock_github, 'some_name')
        self.assertEqual(result, user_result, 'unexpected result')

    @patch('github.Github')
    def test_get_github_organization_by_org(self, mock_github):
        org_result = {'name': 'org'}
        mock_github.get_organization.return_value = org_result
        result = get_github_organization(mock_github, 'some_name')
        self.assertEqual(result, org_result, 'unexpected result')

    @patch('github.Repository')
    def test_get_tags_from_repo(self, mock_repo):

        ref_result = [TestGetTags.RefData(ref="refs/heads/master",
                              url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/master",
                              object=TestGetTags.ObjectData(type="commit",
                                                sha="aa218f56b14c9653891f9e74264a383fa43fefbd",
                                                url="https://api.github.com/repos/octocat/Hello-World/git/commits/aa218f56b14c9653891f9e74264a383fa43fefbd")),
                      TestGetTags.RefData(ref="refs/heads/gh-pages",
                              url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/gh-pages",
                              object=TestGetTags.ObjectData(type="commit",
                                                sha="612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac",
                                                url="https://api.github.com/repos/octocat/Hello-World/git/commits/612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac")),
                      TestGetTags.RefData(ref="refs/tags/v0.0.1",
                              url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                              object=TestGetTags.ObjectData(type="tag",
                                                sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                                url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac"))
                      ]
        mock_repo.get_git_refs.return_value = ref_result
        tags = get_tags_from_repo(mock_repo)
        self.assertEqual(len(tags), 1, 'more or less tags returned')
        self.assertEqual(tags[0].ref, "refs/tags/v0.0.1", 'different ref returned')
        self.assertEqual(tags[0].object.type, "tag", 'not a tag')

    @patch('github.Repository')
    def test_get_tags_from_repo_with_start_label_tag_present(self, mock_repo):

        start_label = "mystartlabel/"

        ref_result = [TestGetTags.RefData(ref="refs/heads/master",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/master",
                                          object=TestGetTags.ObjectData(type="commit",
                                                                        sha="aa218f56b14c9653891f9e74264a383fa43fefbd",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/commits/aa218f56b14c9653891f9e74264a383fa43fefbd")),
                      TestGetTags.RefData(ref="refs/heads/gh-pages",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/gh-pages",
                                          object=TestGetTags.ObjectData(type="commit",
                                                                        sha="612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/commits/612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac")),
                      TestGetTags.RefData(ref="refs/tags/v0.0.1",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                                          object=TestGetTags.ObjectData(type="tag",
                                                                        sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac")),
                      TestGetTags.RefData(ref="refs/tags/" + start_label + "v0.0.1",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                                          object=TestGetTags.ObjectData(type="tag",
                                                                        sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac"))
                      ]
        mock_repo.get_git_refs.return_value = ref_result
        tags = get_tags_from_repo(mock_repo, start_label)
        self.assertEqual(len(tags), 1, 'more or less tags returned')
        self.assertEqual(tags[0].ref, "refs/tags/" + start_label + "v0.0.1", 'different ref returned')
        self.assertEqual(tags[0].object.type, "tag", 'not a tag')

    @patch('github.Repository')
    def test_get_tags_from_repo_with_no_start_label_tag_present(self, mock_repo):

        start_label = "mystartlabel/"

        ref_result = [TestGetTags.RefData(ref="refs/heads/master",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/master",
                                          object=TestGetTags.ObjectData(type="commit",
                                                                        sha="aa218f56b14c9653891f9e74264a383fa43fefbd",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/commits/aa218f56b14c9653891f9e74264a383fa43fefbd")),
                      TestGetTags.RefData(ref="refs/heads/gh-pages",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/gh-pages",
                                          object=TestGetTags.ObjectData(type="commit",
                                                                        sha="612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/commits/612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac")),
                      TestGetTags.RefData(ref="refs/tags/v0.0.1",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                                          object=TestGetTags.ObjectData(type="tag",
                                                                        sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac"))
                      ]
        mock_repo.get_git_refs.return_value = ref_result
        tags = get_tags_from_repo(mock_repo, start_label)
        self.assertEqual(len(tags), 0, 'more or less tags returned')





if __name__ == '__main__':
    unittest.main()
