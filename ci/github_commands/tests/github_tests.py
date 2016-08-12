import unittest
import urllib

from mock import patch
from github_commands.get_tags import get_github_organization, get_tags_from_repo
from github_commands.set_tag import set_tag_in_repo

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

class TestGetTags(unittest.TestCase):


    

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

        ref_result = [RefData(ref="refs/heads/master",
                              url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/master",
                              object=ObjectData(type="commit",
                                                sha="aa218f56b14c9653891f9e74264a383fa43fefbd",
                                                url="https://api.github.com/repos/octocat/Hello-World/git/commits/aa218f56b14c9653891f9e74264a383fa43fefbd")),
                      RefData(ref="refs/heads/gh-pages",
                              url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/gh-pages",
                              object=ObjectData(type="commit",
                                                sha="612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac",
                                                url="https://api.github.com/repos/octocat/Hello-World/git/commits/612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac")),
                      RefData(ref="refs/tags/v0.0.1",
                              url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                              object=ObjectData(type="tag",
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

        ref_result = [RefData(ref="refs/heads/master",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/master",
                                          object=ObjectData(type="commit",
                                                                        sha="aa218f56b14c9653891f9e74264a383fa43fefbd",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/commits/aa218f56b14c9653891f9e74264a383fa43fefbd")),
                      RefData(ref="refs/heads/gh-pages",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/gh-pages",
                                          object=ObjectData(type="commit",
                                                                        sha="612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/commits/612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac")),
                      RefData(ref="refs/tags/v0.0.1",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                                          object=ObjectData(type="tag",
                                                                        sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac")),
                      RefData(ref="refs/tags/" + start_label + "v0.0.1",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                                          object=ObjectData(type="tag",
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

        ref_result = [RefData(ref="refs/heads/master",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/master",
                                          object=ObjectData(type="commit",
                                                                        sha="aa218f56b14c9653891f9e74264a383fa43fefbd",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/commits/aa218f56b14c9653891f9e74264a383fa43fefbd")),
                      RefData(ref="refs/heads/gh-pages",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/heads/gh-pages",
                                          object=ObjectData(type="commit",
                                                                        sha="612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/commits/612077ae6dffb4d2fbd8ce0cccaa58893b07b5ac")),
                      RefData(ref="refs/tags/v0.0.1",
                                          url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                                          object=ObjectData(type="tag",
                                                                        sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                                                        url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac"))
                      ]
        mock_repo.get_git_refs.return_value = ref_result
        tags = get_tags_from_repo(mock_repo, start_label)
        self.assertEqual(len(tags), 0, 'more or less tags returned')


class TestSetTag(unittest.TestCase):

    @patch('github.Repository')
    def test_set_tag_in_repo(self, mock_repo):
        tagname = 'testtag'
        ret_value = RefData(ref="refs/tags/" + tagname,
                            url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/" + tagname,
                            object=ObjectData(type="tag",
                                              sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                              url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac"))
        mock_repo.create_git_ref.return_value = ret_value
        sha = '167383'

        tag = set_tag_in_repo(mock_repo, tagname, sha)

        mock_repo.create_git_ref.assert_called_with('/tags/' + tagname, sha)
        self.assertEqual(tag, ret_value)

    @patch('github.Repository')
    def test_set_tag_in_repo_with_encoding_issue(self, mock_repo):
        tagname = 'testtag<>'
        ret_value = RefData(ref="refs/tags/" + urllib.quote_plus(tagname),
                            url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/" + urllib.quote_plus(tagname),
                            object=ObjectData(type="tag",
                                              sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                              url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac"))
        mock_repo.create_git_ref.return_value = ret_value
        sha = '167383'

        tag = set_tag_in_repo(mock_repo, tagname, sha)

        mock_repo.create_git_ref.assert_called_with('/tags/' + urllib.quote_plus(tagname), sha)
        self.assertEqual(tag, ret_value)







if __name__ == '__main__':
    unittest.main()
