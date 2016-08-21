import unittest
import urllib
import os
import threading
import time

from mock import patch, Mock, MagicMock

from orgmanagement.bind_org import bind_org, OrgBoundException, release_org


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

    class ThreadOne(threading.Thread):

        def __init__(self, event, testcase, mock_github):
            threading.Thread.__init__(self)
            self._event = event
            self._testcase = testcase
            self._mock_github = mock_github

        def run(self):
            ret_value = [TestBindOrg.RefData(ref="refs/tags/" + urllib.quote_plus(self._testcase._org_name),
                                             url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                                             object=TestBindOrg.ObjectData(type="tag",
                                                                           sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                                                           url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac"))
                         ]
            # step 1: bind the org
            bind_org(self._testcase._org_name, self._testcase._github_config)
            self._mock_github.return_value.get_organization.return_value.get_repo.return_value.create_git_ref\
                .assert_called_with(
                '/tags/' + urllib.quote_plus(self._testcase._org_name), self._testcase._sha)
            # stub the outcome of the git_git_refs call so it looks like the org is bound
            self._mock_github.return_value.get_organization.return_value.get_repo.return_value.get_git_refs.return_value = \
                ret_value
            # let the other thread know the org is bound
            self._event.set()
            # wait for some time
            time.sleep(3)
            # make the event available for reuse (yes I know, should spin a second one but how to let the other
            # thread know)
            self._event.clear()
            # release the org
            with patch('github.Github') as self._mock_github:
                release_org(self._testcase._org_name, self._testcase._github_config)
                # stub the outcome of the get_git_refs call so it looks the org is released
                ret_value = []
                self._mock_github.return_value.get_organization.return_value.get_repo.return_value.get_git_refs.return_value = \
                    ret_value
                # and let the rest of the world know we have released it
                self._event.set()

    class ThreadTwo(threading.Thread):

        def __init__(self, event, testcase, mock_github):
            threading.Thread.__init__(self)
            self._event = event
            self._testcase = testcase
            self._mock_github = mock_github

        def run(self):
            # we start by waiting for the event
            self._event.wait()
            # as soon as we have received the event we try to bind the org and fail (hopefully)
            self._testcase.assertRaises(OrgBoundException, bind_org, self._testcase._org_name,
                                        self._testcase._github_config,
                                        False,
                                        False,
                                        10, 60)
            # waiting again
            self._event.wait()
            # bind the org and now it should work
            bind_org(self._testcase._org_name, self._testcase._github_config)
            # test if the ref is created
            self._mock_github.return_value.get_organization.return_value.get_repo.return_value.create_git_ref\
                .assert_called_with(
                '/tags/' + urllib.quote_plus(self._testcase._org_name), self._testcase._sha)

    def setUp(self):
        self._github_config = {'GITHUB_ORG_NAME': 'testgithuborg',
                                'GITHUB_USERNAME': 'testuser',
                                'GITHUB_PASSWORD': 'testpassword',
                                'GITHUB_REPO_NAME': 'testrepo'}
        self._sha = '12345'
        self._org_name = 'user@blah.com'

    @patch('github.Github')
    @patch('os.environ')
    def test_bind_not_bound_org_github_tags(self, mock_environ, mock_github):

        self._github_config['SHA'] = self._sha

        bind_org(self._org_name, self._github_config, sandbox=False, wait=True, retry_attempts=10, sleeping_time=60)

        mock_github.return_value.get_organization.return_value.get_repo.return_value.create_git_ref.assert_called_with(
            '/tags/' + urllib.quote_plus(self._org_name), self._sha)
        mock_environ.__setitem__.assert_called_with('BOUND_ORG_NAME', self._org_name)

    @patch('github.Github')
    def test_bind_bound_org_wait_false(self, mock_github):
        ret_value = [TestBindOrg.RefData(ref="refs/tags/" + urllib.quote_plus(self._org_name),
                                         url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                                         object=TestBindOrg.ObjectData(type="tag",
                                                                       sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                                                       url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac"))
                     ]
        self._github_config['SHA'] = self._sha

        mock_github.return_value.get_organization.return_value.get_repo.return_value.get_git_refs.return_value = \
            ret_value

        self.assertRaises(OrgBoundException, bind_org, self._org_name, self._github_config, False, False,
                          10, 60)

    @patch('github.Github')
    @patch('time.sleep')
    def test_bind_bound_org_wait_true(self, mock_sleep, mock_github):
        ret_value = [TestBindOrg.RefData(ref="refs/tags/" + urllib.quote_plus(self._org_name),
                                         url="https://api.github.com/repos/octocat/Hello-World/git/refs/tags/v0.0.1",
                                         object=TestBindOrg.ObjectData(type="tag",
                                                                       sha="940bd336248efae0f9ee5bc7b2d5c985887b16ac",
                                                                       url="https://api.github.com/repos/octocat/Hello-World/git/tags/940bd336248efae0f9ee5bc7b2d5c985887b16ac"))
                     ]
        self._github_config['SHA'] = self._sha

        mock_github.return_value.get_organization.return_value.get_repo.return_value.get_git_refs.return_value = \
            ret_value

        self.assertRaises(OrgBoundException, bind_org, self._org_name, self._github_config, False, True,
                          10, 60)
        mock_sleep.assert_called_with(60)
        self.assertEqual(mock_sleep.call_count, 10, 'More or less times sleep method called')

    @patch('github.Github')
    @patch('github.GitRef.GitRef')
    def test_release_bound_org(self, mock_ref, mock_github):

        mock_ref.return_value.ref.return_value = "refs/tags/" + urllib.quote_plus(self._org_name)
        mock_ref.return_value.object.return_value = MagicMock()
        mock_ref.return_value.object.return_value.type.return_value = "tag"
        ret_value = [mock_ref]
        mock_github.return_value.get_organization.return_value.get_repo.return_value.get_git_refs.return_value = \
            ret_value
        self._github_config['SHA'] = self._sha

        release_org(self._org_name, self._github_config)

        mock_ref.delete.assert_called_with()

    @patch('github.Github')
    def test_release_unbound_org(self, mock_github):
        ret_value = []
        mock_github.return_value.get_organization.return_value.get_repo.return_value.get_git_refs.return_value = \
            ret_value
        self._github_config['SHA'] = self._sha

        self.assertRaises(OrgBoundException, release_org, self._org_name, self._github_config)


    # @patch('github.Github')
    # def test_bind_org_bounded_by_other_thread(self, mock_github):
    #     self._github_config['SHA'] = self._sha
    #     event = threading.Event()
    #     t1 = TestBindOrg.ThreadOne(event=event, testcase=self, mock_github=mock_github)
    #     t2 = TestBindOrg.ThreadTwo(event=event, testcase=self, mock_github=mock_github)
    #     t1.start()
    #     t2.start()


if __name__ == '__main__':
    unittest.main()
