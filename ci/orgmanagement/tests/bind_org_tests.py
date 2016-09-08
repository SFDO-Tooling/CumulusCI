import unittest
import yaml
import base64
import github

from mock import patch, call, MagicMock
from orgmanagement.bind_org import BindBuildToOrgCommand, OrgBoundException, ReleaseOrgCommand, OrgManagementCommand


class TestBindBuildToOrg(unittest.TestCase):

    def setUp(self):
        self._config = {'GITHUB_ORG_NAME': 'testgithuborg',
                        'GITHUB_USERNAME': 'testuser',
                        'GITHUB_PASSWORD': 'testpassword',
                        'GITHUB_REPO_NAME': 'testrepo'}
        self._orgname = 'orgname'
        self._build_id = '12345'

    @patch('orgmanagement.bind_org.OrgManagementCommand.GitFileStorage')
    def test_bind_build_to_unbound_org(self, mock_git_file_storage):
        self._command = BindBuildToOrgCommand(self._orgname, self._build_id, self._config)
        mock_git_file_storage.return_value.get_binding.return_value = None
        self._command.execute()
        mock_git_file_storage.return_value.bind_build_to_org.assert_called_with(self._orgname, self._build_id)

    @patch('orgmanagement.bind_org.OrgManagementCommand.GitFileStorage')
    def test_bind_build_to_bound_org(self, mock_git_file_storage):
        self._command = BindBuildToOrgCommand(self._orgname, self._build_id, self._config)
        mock_git_file_storage.return_value.get_binding.return_value = 'justanotherbuild_id'
        self._command.wait = False
        self.assertRaises(OrgBoundException, self._command.execute)

    @patch('orgmanagement.bind_org.OrgManagementCommand.GitFileStorage')
    def test_bind_same_build_to_bound_org(self, mock_git_file_storage):
        self._command = BindBuildToOrgCommand(self._orgname, self._build_id, self._config)
        mock_git_file_storage.return_value.get_binding.return_value = self._build_id
        self._command.wait = False
        self.assertFalse(mock_git_file_storage.return_value.bind_build_to_org.called, 'method called')


class TestReleaseOrgCommand(unittest.TestCase):

    def setUp(self):
        self._config = {'GITHUB_ORG_NAME': 'testgithuborg',
                        'GITHUB_USERNAME': 'testuser',
                        'GITHUB_PASSWORD': 'testpassword',
                        'GITHUB_REPO_NAME': 'testrepo'}
        self._orgname = 'orgname'
        self._build_id = '12345'

    @patch('orgmanagement.bind_org.OrgManagementCommand.GitFileStorage')
    def test_release_bound_org(self, mock_git_file_storage):
        self._command = ReleaseOrgCommand(self._orgname, self._config)
        # setup in such a way the org is bound. In other words: get a correct build id from the bindings
        mock_git_file_storage.return_value.get_binding.return_value = self._build_id
        self._command.execute()
        # assert the binding is removed from the storage
        mock_git_file_storage.return_value.delete_binding.assert_called_with(self._orgname)

    @patch('orgmanagement.bind_org.OrgManagementCommand.GitFileStorage')
    def test_release_unbound_org(self, mock_git_file_storage):
        self._command = ReleaseOrgCommand(self._orgname, self._config)
        # setup in such a way the org is bound. In other words: get a correct build id from the bindings
        mock_git_file_storage.return_value.get_binding.return_value = None
        self.assertRaises(OrgBoundException, self._command.execute)

    @patch('orgmanagement.bind_org.OrgManagementCommand.GitFileStorage')
    def test_release_org_bound_to_wrong_build(self, mock_git_file_storage):
        self._command = ReleaseOrgCommand(self._orgname, self._config)
        self._command.binding = 'justanotherbuild'
        # setup in such a way the org is bound. In other words: get a correct build id from the bindings
        mock_git_file_storage.return_value.get_binding.return_value = self._build_id
        self.assertRaises(OrgBoundException, self._command.execute)


class TestGitFileStorage(unittest.TestCase):

    def setUp(self):
        self._config = {'github_org_name': 'testgithuborg',
                        'github_username': 'testuser',
                        'github_password': 'testpassword',
                        'github_repo_name': 'testrepo',
                        'BUILD_STORAGE_FILE': 'test_file_name',
                        'BUILD_STORAGE_BRANCH': 'test_branch_name'}
        self.__get_branch_counter = 0

    def _get_branch_side_effect(self, branch_name):
        if branch_name == self._config['BUILD_STORAGE_BRANCH']:
            self.__get_branch_counter = self.__get_branch_counter + 1
            if self.__get_branch_counter == 1:
                raise Exception
            else:
                name_mock = MagicMock()
                name_mock.name = self._config['BUILD_STORAGE_BRANCH']
                return name_mock
        else:
            sha_mock = MagicMock()
            sha_mock.commit.sha = '12345'
            # mock_branch = MagicMock(spec=github.Branch, return_value=sha_mock)
            return sha_mock

    @patch('github.Github')
    def test_bind_build_org_no_branch_no_file(self, mock_github):
        mock_repo = mock_github.return_value.get_organization.return_value.get_repo
        mock_repo.return_value.default_branch = 'test_master'
        mock_repo.return_value.get_branch.side_effect = self._get_branch_side_effect
        mock_repo.return_value.get_file_contents.side_effect = Exception()
        storage = OrgManagementCommand.GitFileStorage(self._config)

        storage.bind_build_to_org('test_orgname', 'test_build_id')

        # have the bindings been properly set?
        self.assertEqual(storage.get_binding('test_orgname'), 'test_build_id')

        # no branch was already created so have the right methods been called to create one?
        expected_get_branch_calls = [call(self._config['BUILD_STORAGE_BRANCH']), call('test_master'), call(self._config['BUILD_STORAGE_BRANCH'])]
        self.assertEqual(mock_repo.return_value.get_branch.call_args_list, expected_get_branch_calls,
                         'different call arguments/order for get_branch')
        mock_repo.return_value.create_git_ref.assert_called_with('refs/heads/' + self._config[
            'BUILD_STORAGE_BRANCH'], '12345')

        # has the file been created properly?
        bindings = {'test_orgname': 'test_build_id'}
        yaml_string = yaml.safe_dump(bindings)
        mock_repo.return_value.create_file.assert_called_with('/' + self._config['BUILD_STORAGE_FILE'], '--skip-ci',
                                                              yaml_string, self._config['BUILD_STORAGE_BRANCH'])

    @patch('github.ContentFile')
    @patch('github.Github')
    @patch('github.Branch')
    def test_bind_build_org_existing_file(self, mock_branch, mock_github, mock_content_file):
        mock_repo = mock_github.return_value.get_organization.return_value.get_repo
        mock_repo.return_value.default_branch = 'test_master'
        mock_repo.return_value.get_branch.return_value = mock_branch
        # trick the system in thinking there is a file
        mock_repo.return_value.get_file_contents.return_value = mock_content_file
        # trick the system in thinking there are no bindings
        no_bindings = {}
        decoded_content = yaml.safe_dump(no_bindings)
        mock_content_file.content = base64.encodestring(decoded_content)
        mock_content_file.decoded_content = decoded_content

        storage = OrgManagementCommand.GitFileStorage(self._config)

        self.assertIsNone(storage.get_binding('fake_org_name'), 'Got a binding returned')

        storage.bind_build_to_org('test_org_name', 'test_build_id')

        bindings = {'test_org_name': 'test_build_id'}
        yaml_string = yaml.safe_dump(bindings)
        self.assertEqual(storage.get_binding('test_org_name'), 'test_build_id', 'Got an unknown binding back')
        mock_repo.return_value.update_file.assert_called_with('/' + self._config['BUILD_STORAGE_FILE'], '--skip-ci',
                                                              yaml_string, self._config[
                                                                  'BUILD_STORAGE_BRANCH'])

    @patch('github.ContentFile')
    @patch('github.Github')
    @patch('github.Branch')
    def test_bind_build_org_existing_binding(self, mock_branch, mock_github, mock_content_file):
        mock_repo = mock_github.return_value.get_organization.return_value.get_repo
        mock_repo.return_value.default_branch = 'test_master'
        mock_repo.return_value.get_branch.return_value = mock_branch
        # trick the system in thinking there is a file
        mock_repo.return_value.get_file_contents.return_value = mock_content_file
        # trick the system in thinking there is a binding
        bindings = {'org_name1': 'mybuild'}
        decoded_content = yaml.safe_dump(bindings)
        mock_content_file.content = base64.encodestring(decoded_content)
        mock_content_file.decoded_content = decoded_content

        storage = OrgManagementCommand.GitFileStorage(self._config)

        self.assertIsNone(storage.get_binding('fake_org_name'), 'Got a binding returned')

        storage.bind_build_to_org('test_org_name', 'test_build_id')

        self.assertEqual(storage.get_binding('test_org_name'), 'test_build_id', 'Got an unknown binding back')
        bindings = {'org_name1': 'mybuild', 'test_org_name': 'test_build_id'}
        yaml_string = yaml.safe_dump(bindings)
        mock_repo.return_value.update_file.assert_called_with('/' + self._config['BUILD_STORAGE_FILE'], '--skip-ci',
                                                              yaml_string, self._config[
                                                                  'BUILD_STORAGE_BRANCH'])

        self.assertEqual(storage.get_binding('org_name1'), 'mybuild', 'wrong build returned')


if __name__ == '__main__':
    unittest.main()
