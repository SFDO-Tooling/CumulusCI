import unittest

from cumulusci.core.github import get_github_api


class TestGithub(unittest.TestCase):

    def test_github_api_retries(self):
        gh = get_github_api('TestUser', 'TestPass')
        adapter = gh._session.get_adapter('http://')

        self.assertEqual(0.3, adapter.max_retries.backoff_factor)
        self.assertIn(502, adapter.max_retries.status_forcelist)
