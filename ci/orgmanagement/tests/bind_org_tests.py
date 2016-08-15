import unittest
from mock import patch

from orgmanagement.bind_org import bind_org, OrgBoundException, SLEEP_PERIOD_IN_SECONDS


class TestBindOrg(unittest.TestCase):

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

    @patch('orgmanagement.bind_org.set_tag')
    @patch('orgmanagement.bind_org.get_tags')
    @patch('os.environ')
    def test_bind_not_bound_org(self, mock_environ, mock_get_tags, mock_set_tag):
        mock_get_tags.return_value = []
        orgname = 'testorg'
        sha = '12345'
        github_organization = 'testgithuborg'
        github_user = 'testuser'
        github_password = 'testpassword'
        github_repository = 'testrepo'

        bind_org(orgname, sha, github_organization, github_user, github_password,
                          github_repository)

        mock_get_tags.assert_called_with(github_organization, github_repository, github_user, github_password, orgname)
        mock_set_tag.assert_called_with(github_organization, github_repository, github_user, github_password, orgname,
                                        sha)
        mock_environ.__setitem__.assert_called_with('BOUND_ORG_NAME', orgname)



    @patch('orgmanagement.bind_org.get_tags')
    def test_bind_bound_org_wait_false(self, mock_get_tags):
        ret_value = [TestBindOrg.RefData(ref="refs/tags/v0.0.1",
                                         url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                                         object=TestBindOrg.ObjectData(type="tag",
                                                                       sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                                                       url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac"))
                     ]
        mock_get_tags.return_value = ret_value
        orgname = 'testorg'
        sha = '12345'
        github_organization = 'testgithuborg'
        github_user = 'testuser'
        github_password = 'testpassword'
        github_repository = 'testrepo'

        self.assertRaises(OrgBoundException, bind_org, orgname, sha, github_organization, github_user, github_password,
                 github_repository, wait=False)

    @patch('orgmanagement.bind_org.get_tags')
    @patch('time.sleep')
    def test_bind_bound_org_wait_false(self, mock_sleep, mock_get_tags):
        ret_value = [TestBindOrg.RefData(ref="refs/tags/v0.0.1",
                                         url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                                         object=TestBindOrg.ObjectData(type="tag",
                                                                       sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                                                       url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac"))
                     ]
        mock_get_tags.return_value = ret_value
        orgname = 'testorg'
        sha = '12345'
        github_organization = 'testgithuborg'
        github_user = 'testuser'
        github_password = 'testpassword'
        github_repository = 'testrepo'
        sleep_time = 60
        retry_attempts = 5

        self.assertRaises(OrgBoundException, bind_org, orgname, sha, github_organization, github_user, github_password,
                          github_repository, True, False, retry_attempts, sleep_time)
        mock_sleep.assert_called_with(sleep_time)
        self.assertEqual(mock_sleep.call_count, retry_attempts, 'More or less times sleep method called')


if __name__ == '__main__':
    unittest.main()
