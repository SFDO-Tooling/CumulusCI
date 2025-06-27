from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import VcsException, VcsNotFoundError
from cumulusci.core.keychain import EncryptedFileProjectKeychain
from cumulusci.vcs import bootstrap
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.models import (
    AbstractBranch,
    AbstractGitTag,
    AbstractPullRequest,
    AbstractRelease,
    AbstractRepo,
    AbstractRepoCommit,
)
from cumulusci.vcs.tests.dummy_service import DummyRef, DummyRepo, DummyTag


class TestBootstrapFunctions:
    """Test class for VCS bootstrap functions"""

    @pytest.fixture()
    def keychain(self, project_config, key) -> EncryptedFileProjectKeychain:
        keychain = EncryptedFileProjectKeychain(project_config, key)
        assert keychain.project_config == project_config
        assert keychain.key == key
        return keychain

    @pytest.fixture()
    def mock_repo(self):
        """Create a mock repository for testing"""
        repo = Mock(spec=AbstractRepo)
        repo.default_branch = "main"
        repo.repo_url = "https://github.com/test/repo"
        repo.owner_login = "test"
        return repo

    @pytest.fixture()
    def mock_commit(self):
        """Create a mock commit for testing"""
        commit = Mock(spec=AbstractRepoCommit)
        commit.sha = "1234567890abcdef"
        commit.parents = []
        return commit

    @pytest.fixture()
    def mock_release(self):
        """Create a mock release for testing"""
        release = Mock(spec=AbstractRelease)
        release.tag_name = "release/1.0.0"
        release.prerelease = False
        return release

    @pytest.fixture()
    def mock_pull_request(self):
        """Create a mock pull request for testing"""
        pr = Mock(spec=AbstractPullRequest)
        pr.merged_at = None
        pr.number = 123
        return pr

    @pytest.fixture()
    def mock_project_config(self):
        """Create a mock project config for testing"""
        config = Mock(spec=BaseProjectConfig)
        config.repo_url = "https://github.com/test/repo"
        config.config = {}
        config.config["services"] = {
            "test_service": {
                "attributes": {"name": {"required": True}, "password": {}},
            },
        }
        config.logger = Mock()
        config.project__git__prefix_feature = "feature/"
        config.project__git__prefix_release = "release/"
        config.project__git__prefix_beta = "beta/"
        return config

    def test_get_service_with_class_path(self, keychain, service_config):
        """Test getting service with valid class path"""
        project_config = keychain.project_config
        project_config.keychain = keychain
        keychain.set_service("github", "alias", service_config)

        encrypted = keychain._get_config_bytes(service_config)
        keychain.config["services"]["github"] = {"alias": encrypted}

        keychain._save_default_service("github", "alias", project=False)
        keychain._load_default_services()

        result = bootstrap.get_service(project_config)
        assert isinstance(result, VCSService)

    @patch("cumulusci.vcs.base.VCSService.registered_services")
    def test_get_service_missing_class_path(self, mock_registered_services):
        """Test error handling when class path is missing"""
        config = MagicMock()
        config.get_project_service.return_value = ("github", None)
        config.lookup.return_value = "github"
        config.services = {"github": {}}
        config.repo_url = "https://github.com/invalid/repo"

        # Mock no registered services to force the exception
        mock_registered_services.return_value = []

        with pytest.raises(VcsException) as e:
            bootstrap.get_service(config)
        assert "Could not find a VCS service for URL" in str(e.value)

    def test_get_ref_for_tag(self):
        """Test getting reference for a tag"""
        repo = DummyRepo()
        result = bootstrap.get_ref_for_tag(repo, "v1.0")
        assert isinstance(result, DummyRef)

    def test_get_tag_by_name(self):
        """Test getting tag by name"""
        repo = DummyRepo()
        result = bootstrap.get_tag_by_name(repo, "v1.0")
        assert isinstance(result, DummyTag)

    def test_get_version_id_from_commit_success(self, mock_repo):
        """Test successfully getting version ID from commit"""
        mock_commit = Mock(spec=AbstractRepoCommit)
        mock_commit.get_statuses.return_value = "04t123456789"
        mock_repo.get_commit.return_value = mock_commit

        result = bootstrap.get_version_id_from_commit(mock_repo, "abc123", "context")
        assert result == "04t123456789"

    def test_get_version_id_from_commit_no_commit(self, mock_repo):
        """Test getting version ID when commit doesn't exist"""
        mock_repo.get_commit.return_value = None

        result = bootstrap.get_version_id_from_commit(mock_repo, "abc123", "context")
        assert result is None

    def test_get_commit(self, mock_repo, mock_commit):
        """Test getting commit by SHA"""
        mock_repo.get_commit.return_value = mock_commit

        result = bootstrap.get_commit(mock_repo, "abc123")
        assert result == mock_commit
        mock_repo.get_commit.assert_called_once_with("abc123")

    def test_get_pull_requests_with_base_branch_simple(self, mock_repo):
        """Test getting pull requests with base branch"""
        mock_prs = [Mock(), Mock()]
        mock_repo.pull_requests.return_value = mock_prs

        result = bootstrap.get_pull_requests_with_base_branch(mock_repo, "main")
        assert result == mock_prs
        mock_repo.pull_requests.assert_called_once_with(
            base="main", head=None, state=None
        )

    def test_get_pull_requests_with_base_branch_with_head(self, mock_repo):
        """Test getting pull requests with base branch and head"""
        mock_prs = [Mock(), Mock()]
        mock_repo.pull_requests.return_value = mock_prs
        mock_repo.owner_login = "test_owner"

        result = bootstrap.get_pull_requests_with_base_branch(
            mock_repo, "main", head="feature-branch", state="open"
        )
        assert result == mock_prs
        mock_repo.pull_requests.assert_called_once_with(
            base="main", head="test_owner:feature-branch", state="open"
        )

    def test_is_pull_request_merged_true(self):
        """Test pull request is merged"""
        pr = Mock(spec=AbstractPullRequest)
        pr.merged_at = "2023-01-01T00:00:00Z"

        result = bootstrap.is_pull_request_merged(pr)
        assert result is True

    def test_is_pull_request_merged_false(self):
        """Test pull request is not merged"""
        pr = Mock(spec=AbstractPullRequest)
        pr.merged_at = None

        result = bootstrap.is_pull_request_merged(pr)
        assert result is False

    def test_is_label_on_pull_request_true(self, mock_repo, mock_pull_request):
        """Test label exists on pull request"""
        mock_repo.get_pr_issue_labels.return_value = [
            "bug",
            "enhancement",
            "documentation",
        ]

        result = bootstrap.is_label_on_pull_request(mock_repo, mock_pull_request, "bug")
        assert result is True

    def test_is_label_on_pull_request_false(self, mock_repo, mock_pull_request):
        """Test label does not exist on pull request"""
        mock_repo.get_pr_issue_labels.return_value = ["bug", "enhancement"]

        result = bootstrap.is_label_on_pull_request(
            mock_repo, mock_pull_request, "documentation"
        )
        assert result is False

    @patch("cumulusci.vcs.bootstrap.get_service_for_repo_url")
    def test_get_repo_from_url_success(self, mock_get_service, mock_project_config):
        """Test successfully getting repository from URL"""
        mock_service = Mock(spec=VCSService)
        mock_repo = Mock(spec=AbstractRepo)
        mock_service.get_repository.return_value = mock_repo
        mock_get_service.return_value = mock_service

        result = bootstrap.get_repo_from_url(
            mock_project_config, "https://github.com/test/repo"
        )

        assert result == mock_repo
        mock_get_service.assert_called_once_with(
            mock_project_config, "https://github.com/test/repo", service_alias=None
        )

    @patch("cumulusci.vcs.bootstrap.get_service_for_repo_url")
    def test_get_repo_from_url_not_found(self, mock_get_service, mock_project_config):
        """Test error when repository is not found"""
        mock_service = Mock(spec=VCSService)
        mock_service.get_repository.return_value = None
        mock_get_service.return_value = mock_service

        with pytest.raises(VcsNotFoundError) as e:
            bootstrap.get_repo_from_url(
                mock_project_config, "https://github.com/test/repo"
            )

        assert "Could not find a repository at https://github.com/test/repo" in str(
            e.value
        )

    @patch("cumulusci.vcs.base.VCSService.registered_services")
    def test_get_service_for_repo_url_success(
        self, mock_registered_services, mock_project_config
    ):
        """Test successfully getting service for repo URL"""
        mock_service_class = Mock()
        mock_service_instance = Mock(spec=VCSService)
        mock_service_class.get_service_for_url.return_value = mock_service_instance
        mock_registered_services.return_value = [mock_service_class]

        result = bootstrap.get_service_for_repo_url(
            mock_project_config, "https://github.com/test/repo"
        )

        assert result == mock_service_instance
        mock_service_class.get_service_for_url.assert_called_once_with(
            mock_project_config, "https://github.com/test/repo", service_alias=None
        )

    @patch("cumulusci.vcs.base.VCSService.registered_services")
    def test_get_service_for_repo_url_not_found(
        self, mock_registered_services, mock_project_config
    ):
        """Test error when no service found for URL"""
        mock_service_class = Mock()
        mock_service_class.get_service_for_url.return_value = None
        mock_registered_services.return_value = [mock_service_class]

        with pytest.raises(VcsException) as e:
            bootstrap.get_service_for_repo_url(
                mock_project_config, "https://github.com/test/repo"
            )

        assert (
            "Could not find a VCS service for URL: https://github.com/test/repo"
            in str(e.value)
        )

    @patch("cumulusci.vcs.bootstrap.cci_safe_load")
    def test_get_remote_project_config(self, mock_cci_load, mock_repo):
        """Test getting remote project configuration"""
        mock_file_contents = StringIO("project:\n  name: test")
        mock_repo.file_contents.return_value = mock_file_contents
        mock_cci_load.return_value = {"project": {"name": "test"}}

        result = bootstrap.get_remote_project_config(mock_repo, "main")

        assert isinstance(result, BaseProjectConfig)
        mock_repo.file_contents.assert_called_once_with("cumulusci.yml", ref="main")
        mock_cci_load.assert_called_once_with(mock_file_contents)

    @patch("cumulusci.vcs.bootstrap.get_remote_project_config")
    def test_find_repo_feature_prefix_with_custom_prefix(
        self, mock_get_config, mock_repo
    ):
        """Test finding repository feature prefix with custom prefix"""
        mock_branch = Mock()
        mock_commit = Mock()
        mock_commit.sha = "abc123"
        mock_branch.commit = mock_commit
        mock_repo.branch.return_value = mock_branch

        mock_config = Mock()
        mock_config.project__git__prefix_feature = "custom-feature/"
        mock_get_config.return_value = mock_config

        result = bootstrap.find_repo_feature_prefix(mock_repo)

        assert result == "custom-feature/"
        mock_repo.branch.assert_called_once_with(mock_repo.default_branch)

    @patch("cumulusci.vcs.bootstrap.get_remote_project_config")
    def test_find_repo_feature_prefix_default(self, mock_get_config, mock_repo):
        """Test finding repository feature prefix with default"""
        mock_branch = Mock()
        mock_commit = Mock()
        mock_commit.sha = "abc123"
        mock_branch.commit = mock_commit
        mock_repo.branch.return_value = mock_branch

        mock_config = Mock()
        mock_config.project__git__prefix_feature = None
        mock_get_config.return_value = mock_config

        result = bootstrap.find_repo_feature_prefix(mock_repo)

        assert result == "feature/"

    @patch("cumulusci.vcs.bootstrap.get_remote_project_config")
    def test_get_remote_context(self, mock_get_config, mock_repo):
        """Test getting remote context"""
        mock_config = Mock()
        mock_config.lookup.return_value = "custom_context"
        mock_get_config.return_value = mock_config

        result = bootstrap.get_remote_context(
            mock_repo, "test_context", "default_context"
        )

        assert result == "custom_context"
        mock_config.lookup.assert_called_once_with("project__git__test_context")

    @patch("cumulusci.vcs.bootstrap.get_remote_project_config")
    def test_get_remote_context_default(self, mock_get_config, mock_repo):
        """Test getting remote context with default"""
        mock_config = Mock()
        mock_config.lookup.return_value = None
        mock_get_config.return_value = mock_config

        result = bootstrap.get_remote_context(
            mock_repo, "test_context", "default_context"
        )

        assert result == "default_context"

    @patch("cumulusci.vcs.bootstrap.get_latest_prerelease")
    def test_find_latest_release_beta(self, mock_get_prerelease, mock_repo):
        """Test finding latest release including beta"""
        mock_release = Mock(spec=AbstractRelease)
        mock_get_prerelease.return_value = mock_release

        result = bootstrap.find_latest_release(mock_repo, include_beta=True)

        assert result == mock_release
        mock_get_prerelease.assert_called_once_with(mock_repo)

    def test_find_latest_release_production(self, mock_repo):
        """Test finding latest production release"""
        mock_release = Mock(spec=AbstractRelease)
        mock_repo.latest_release.return_value = mock_release

        result = bootstrap.find_latest_release(mock_repo, include_beta=False)

        assert result == mock_release
        mock_repo.latest_release.assert_called_once()

    def test_find_latest_release_not_found(self, mock_repo):
        """Test finding latest release when none exists"""
        mock_repo.latest_release.side_effect = VcsNotFoundError("No releases found")

        result = bootstrap.find_latest_release(mock_repo, include_beta=False)

        assert result is None

    def test_get_latest_prerelease(self, mock_repo):
        """Test getting latest prerelease"""
        mock_release = Mock(spec=AbstractRelease)
        mock_repo.get_latest_prerelease.return_value = mock_release

        result = bootstrap.get_latest_prerelease(mock_repo)

        assert result == mock_release
        mock_repo.get_latest_prerelease.assert_called_once()

    def test_find_previous_release_with_prefix(self, mock_repo):
        """Test finding previous release with prefix filter"""
        mock_release1 = Mock(spec=AbstractRelease)
        mock_release1.tag_name = "release/2.0.0"
        mock_release1.prerelease = False

        mock_release2 = Mock(spec=AbstractRelease)
        mock_release2.tag_name = "release/1.0.0"
        mock_release2.prerelease = False

        mock_release3 = Mock(spec=AbstractRelease)
        mock_release3.tag_name = "beta/1.0.0"
        mock_release3.prerelease = True

        mock_repo.releases.return_value = [mock_release1, mock_release2, mock_release3]

        result = bootstrap.find_previous_release(mock_repo, prefix="release/")

        assert result == mock_release2

    def test_find_previous_release_without_prefix(self, mock_repo):
        """Test finding previous release without prefix filter"""
        mock_release1 = Mock(spec=AbstractRelease)
        mock_release1.tag_name = "release/2.0.0"
        mock_release1.prerelease = False

        mock_release2 = Mock(spec=AbstractRelease)
        mock_release2.tag_name = "release/1.0.0"
        mock_release2.prerelease = False

        mock_prerelease = Mock(spec=AbstractRelease)
        mock_prerelease.tag_name = "beta/1.5.0"
        mock_prerelease.prerelease = True

        mock_repo.releases.return_value = [
            mock_release1,
            mock_prerelease,
            mock_release2,
        ]

        result = bootstrap.find_previous_release(mock_repo)

        assert result == mock_release2

    @patch("cumulusci.vcs.bootstrap.get_version_id_from_commit")
    def test_locate_commit_status_package_id_found(
        self, mock_get_version_id, mock_repo
    ):
        """Test locating commit status package ID successfully"""
        mock_branch = Mock(spec=AbstractBranch)
        mock_commit = Mock(spec=AbstractRepoCommit)
        mock_commit.sha = "abc123"
        mock_commit.parents = []
        mock_branch.commit = mock_commit
        mock_get_version_id.return_value = "04t123456789"

        version_id, commit = bootstrap.locate_commit_status_package_id(
            mock_repo, mock_branch, "context_2gp"
        )

        assert version_id == "04t123456789"
        assert commit == mock_commit

    @patch("cumulusci.vcs.bootstrap.get_version_id_from_commit")
    def test_locate_commit_status_package_id_not_found(
        self, mock_get_version_id, mock_repo
    ):
        """Test locating commit status package ID when not found"""
        mock_branch = Mock(spec=AbstractBranch)
        mock_commit = Mock(spec=AbstractRepoCommit)
        mock_commit.sha = "abc123"
        mock_commit.parents = []
        mock_branch.commit = mock_commit
        mock_get_version_id.return_value = None

        version_id, commit = bootstrap.locate_commit_status_package_id(
            mock_repo, mock_branch, "context_2gp"
        )

        assert version_id is None
        assert commit is None  # When no parents, commit becomes None

    @patch("cumulusci.vcs.bootstrap.get_service")
    def test_get_repo_from_config(self, mock_get_service, mock_project_config):
        """Test getting repository from config"""
        mock_service = Mock(spec=VCSService)
        mock_repo = Mock(spec=AbstractRepo)
        mock_service.get_repository.return_value = mock_repo
        mock_get_service.return_value = mock_service

        result = bootstrap.get_repo_from_config(
            mock_project_config, {"option": "value"}
        )

        assert result == mock_repo
        mock_get_service.assert_called_once_with(
            mock_project_config, logger=mock_project_config.logger
        )
        mock_service.get_repository.assert_called_once_with(options={"option": "value"})

    def test_get_latest_tag_production(self, mock_repo):
        """Test getting latest production tag"""
        mock_release = Mock(spec=AbstractRelease)
        mock_release.tag_name = "release/1.0.0"
        mock_repo.latest_release.return_value = mock_release
        mock_repo.project_config = Mock()
        mock_repo.project_config.project__git__prefix_release = "release/"

        result = bootstrap.get_latest_tag(mock_repo, beta=False)

        assert result == "release/1.0.0"

    @patch("cumulusci.vcs.bootstrap._get_latest_tag_for_prefix")
    def test_get_latest_tag_beta(self, mock_get_latest_prefix, mock_repo):
        """Test getting latest beta tag"""
        mock_get_latest_prefix.return_value = "beta/1.0.0"
        mock_repo.project_config = Mock()
        mock_repo.project_config.project__git__prefix_beta = "beta/"

        result = bootstrap.get_latest_tag(mock_repo, beta=True)

        assert result == "beta/1.0.0"
        mock_get_latest_prefix.assert_called_once_with(mock_repo, "beta/")

    def test_get_latest_tag_exception(self, mock_repo):
        """Test getting latest tag when exception occurs"""
        mock_repo.latest_release.side_effect = Exception("Error")
        mock_repo.project_config = Mock()
        mock_repo.project_config.project__git__prefix_release = "release/"
        mock_repo.repo_url = "https://github.com/test/repo"

        with pytest.raises(VcsException) as e:
            bootstrap.get_latest_tag(mock_repo, beta=False)

        assert (
            "No release found for https://github.com/test/repo with tag prefix release/"
            in str(e.value)
        )

    def test_get_latest_tag_for_prefix_success(self, mock_repo):
        """Test getting latest tag for prefix successfully"""
        mock_release1 = Mock(spec=AbstractRelease)
        mock_release1.tag_name = "beta/2.0.0"

        mock_release2 = Mock(spec=AbstractRelease)
        mock_release2.tag_name = "release/1.0.0"

        mock_repo.releases.return_value = [mock_release1, mock_release2]

        result = bootstrap._get_latest_tag_for_prefix(mock_repo, "beta/")

        assert result == "beta/2.0.0"

    def test_get_latest_tag_for_prefix_not_found(self, mock_repo):
        """Test getting latest tag for prefix when not found"""
        mock_release = Mock(spec=AbstractRelease)
        mock_release.tag_name = "release/1.0.0"
        mock_repo.releases.return_value = [mock_release]
        mock_repo.repo_url = "https://github.com/test/repo"

        with pytest.raises(VcsException) as e:
            bootstrap._get_latest_tag_for_prefix(mock_repo, "beta/")

        assert (
            "No release found for https://github.com/test/repo with tag prefix beta/"
            in str(e.value)
        )

    @patch("cumulusci.vcs.bootstrap.get_tag_by_name")
    def test_get_version_id_from_tag_success(self, mock_get_tag, mock_repo):
        """Test getting version ID from tag successfully"""
        mock_tag = Mock(spec=AbstractGitTag)
        mock_tag.message = "Release notes\nversion_id: 04t123456789\nMore info"
        mock_get_tag.return_value = mock_tag

        result = bootstrap.get_version_id_from_tag(mock_repo, "v1.0.0")

        assert result == "04t123456789"
        mock_get_tag.assert_called_once_with(mock_repo, "v1.0.0")

    @patch("cumulusci.vcs.bootstrap.get_tag_by_name")
    def test_get_version_id_from_tag_not_found(self, mock_get_tag, mock_repo):
        """Test getting version ID from tag when not found"""
        mock_tag = Mock(spec=AbstractGitTag)
        mock_tag.message = "Release notes\nNo version id here\nMore info"
        mock_get_tag.return_value = mock_tag

        with pytest.raises(VcsException) as e:
            bootstrap.get_version_id_from_tag(mock_repo, "v1.0.0")

        assert "Could not find version_id for tag v1.0.0" in str(e.value)

    @patch("cumulusci.vcs.bootstrap.get_tag_by_name")
    def test_get_version_id_from_tag_invalid_format(self, mock_get_tag, mock_repo):
        """Test getting version ID from tag with invalid format"""
        mock_tag = Mock(spec=AbstractGitTag)
        mock_tag.message = "Release notes\nversion_id: invalid123\nMore info"
        mock_get_tag.return_value = mock_tag

        with pytest.raises(VcsException) as e:
            bootstrap.get_version_id_from_tag(mock_repo, "v1.0.0")

        assert "Could not find version_id for tag v1.0.0" in str(e.value)


class TestBootstrapIntegration:
    """Integration tests for bootstrap functions"""

    @pytest.fixture()
    def dummy_repo_with_config(self):
        """Create a dummy repo with project config"""
        repo = DummyRepo()
        repo.project_config = Mock()
        repo.project_config.project__git__prefix_release = "release/"
        repo.project_config.project__git__prefix_beta = "beta/"
        repo.repo_url = "https://github.com/test/repo"
        return repo

    def test_get_ref_and_tag_integration(self):
        """Test integration between get_ref_for_tag and get_tag_by_name"""
        repo = DummyRepo()
        tag_name = "v1.0.0"

        # Test the full flow
        ref = bootstrap.get_ref_for_tag(repo, tag_name)
        tag = bootstrap.get_tag_by_name(repo, tag_name)

        assert isinstance(ref, DummyRef)
        assert isinstance(tag, DummyTag)

    @patch("cumulusci.vcs.bootstrap.get_version_id_from_commit")
    def test_locate_commit_status_integration(self, mock_get_version_id):
        """Test integration of commit status location with multiple commits"""
        # Setup commits with parent chain
        commit1 = Mock(spec=AbstractRepoCommit)
        commit1.sha = "abc123"
        commit1.parents = [Mock(sha="def456")]

        commit2 = Mock(spec=AbstractRepoCommit)
        commit2.sha = "def456"
        commit2.parents = []

        mock_branch = Mock(spec=AbstractBranch)
        mock_branch.commit = commit1

        mock_repo = Mock(spec=AbstractRepo)
        mock_repo.get_commit.return_value = commit2

        # First call returns None, second call returns version_id
        mock_get_version_id.side_effect = [None, "04t123456789"]

        version_id, commit = bootstrap.locate_commit_status_package_id(
            mock_repo, mock_branch, "context_2gp"
        )

        assert version_id == "04t123456789"
        assert commit == commit2
        assert mock_get_version_id.call_count == 2


class TestBootstrapRegex:
    """Test regex patterns used in bootstrap"""

    def test_version_id_regex_match(self):
        """Test VERSION_ID_RE regex matching"""
        test_string = "Build status: success\nversion_id: 04t123456789ABC\nMore info"
        match = bootstrap.VERSION_ID_RE.search(test_string)

        assert match is not None
        assert match.group(1) == "04t123456789ABC"

    def test_version_id_regex_no_match(self):
        """Test VERSION_ID_RE regex not matching"""
        test_string = "Build status: success\nNo version id here\nMore info"
        match = bootstrap.VERSION_ID_RE.search(test_string)

        assert match is None


class TestBootstrapEdgeCases:
    """Test edge cases and error conditions"""

    def test_get_pull_requests_empty_list(self):
        """Test getting pull requests when none exist"""
        repo = Mock(spec=AbstractRepo)
        repo.pull_requests.return_value = []

        result = bootstrap.get_pull_requests_with_base_branch(repo, "main")

        assert result == []

    def test_is_label_on_pull_request_empty_labels(self):
        """Test checking label when no labels exist"""
        repo = Mock(spec=AbstractRepo)
        pr = Mock(spec=AbstractPullRequest)
        repo.get_pr_issue_labels.return_value = []

        result = bootstrap.is_label_on_pull_request(repo, pr, "bug")

        assert result is False

    def test_find_previous_release_single_release(self):
        """Test finding previous release when only one exists"""
        repo = Mock(spec=AbstractRepo)
        mock_release = Mock(spec=AbstractRelease)
        mock_release.tag_name = "release/1.0.0"
        mock_release.prerelease = False
        repo.releases.return_value = [mock_release]

        result = bootstrap.find_previous_release(repo)

        assert result is None

    def test_locate_commit_status_no_parents(self):
        """Test locating commit status when commit has no parents"""
        repo = Mock(spec=AbstractRepo)
        branch = Mock(spec=AbstractBranch)
        commit = Mock(spec=AbstractRepoCommit)
        commit.sha = "abc123"
        commit.parents = []
        branch.commit = commit

        with patch(
            "cumulusci.vcs.bootstrap.get_version_id_from_commit", return_value=None
        ):
            version_id, returned_commit = bootstrap.locate_commit_status_package_id(
                repo, branch, "context"
            )

        assert version_id is None
        assert returned_commit is None  # When no parents, commit becomes None
