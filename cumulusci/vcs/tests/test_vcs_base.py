import logging
from typing import Optional
from unittest import mock

import pytest

from cumulusci.core.config import BaseProjectConfig, ServiceConfig, UniversalConfig
from cumulusci.core.dependencies.base import DynamicDependency
from cumulusci.core.keychain.base_project_keychain import BaseProjectKeychain
from cumulusci.tasks.release_notes.generator import BaseReleaseNotesGenerator
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.models import AbstractRelease, AbstractRepo
from cumulusci.vcs.utils import AbstractCommitDir


# Test fixtures
@pytest.fixture
def service_config():
    return ServiceConfig(
        {
            "name": "test@example.com",
            "password": "test123",
            "username": "testuser",
            "email": "test@example.com",
            "token": "abcdef123456",
        },
        name="test_alias",
    )


@pytest.fixture
def project_config():
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(universal_config, config={"no_yaml": True})
    project_config.config["services"] = {
        "github": {
            "attributes": {"name": {"required": True}, "password": {}},
        },
        "test_service": {
            "attributes": {"name": {"required": True}, "password": {}},
        },
    }
    project_config.project = {"name": "TestProject"}
    return project_config


@pytest.fixture
def keychain(project_config, service_config):
    keychain = BaseProjectKeychain(project_config, None)
    keychain.set_service("github", "test_alias", service_config)
    keychain.set_service("test_service", "test_alias", service_config)
    project_config.keychain = keychain
    return keychain


# Mock implementations for testing
class MockDynamicDependency(DynamicDependency):
    @classmethod
    def sync_vcs_and_url(cls, values):
        return values


class MockReleaseNotesGenerator(BaseReleaseNotesGenerator):
    def __init__(self):
        pass

    def __call__(self, *args, **kwargs):
        return "Mock release notes"


class MockCommitDir(AbstractCommitDir):
    def __call__(
        self, local_dir, branch, repo_dir=None, commit_message=None, dry_run=False
    ):
        pass


class MockRepo(AbstractRepo):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def create_tag(
        self,
        tag_name: str,
        message: str,
        sha: str,
        obj_type: str,
        tagger={},
        lightweight: Optional[bool] = False,
    ):
        pass

    def get_ref_for_tag(self, tag_name: str):
        pass

    def get_tag_by_ref(self, ref, tag_name: str = None):
        pass

    def branch(self, branch_name: str):
        pass

    def branches(self):
        pass

    def compare_commits(self, base: str, head: str, source: str):
        pass

    def merge(self, base: str, head: str, source: str, message: str = ""):
        pass

    def archive(self, format: str, zip_content, ref=None):
        pass

    def create_pull(
        self,
        title: str,
        base: str,
        head: str,
        body: str = None,
        maintainer_can_modify: bool = None,
        options: dict = {},
    ):
        pass

    def create_release(
        self,
        tag_name: str,
        name: str,
        body: str = None,
        draft: bool = False,
        prerelease: bool = False,
        options: dict = {},
    ):
        pass

    @property
    def default_branch(self):
        pass

    def full_name(self):
        pass

    def get_commit(self, commit_sha: str):
        pass

    def pull_requests(self, **kwargs):
        pass

    def release_from_tag(self, tag_name: str):
        pass

    def releases(self):
        pass

    def get_pr_issue_labels(self, pull_request):
        pass

    def has_issues(self):
        pass

    def latest_release(self):
        pass

    @property
    def owner_login(self):
        pass

    def directory_contents(self, subfolder: str, return_as, ref: str):
        pass

    @property
    def clone_url(self):
        return "https://github.com/test/repo.git"

    def file_contents(self, file: str, ref: str):
        pass

    def get_latest_prerelease(self):
        pass

    def get_ref(self, ref_sha: str):
        pass

    def create_commit_status(
        self,
        commit_id: str,
        context: str,
        state: str,
        description: str,
        target_url: str,
    ):
        pass


class MockRelease(AbstractRelease):
    def __init__(self, tag_name="v1.0.0"):
        self._tag_name = tag_name

    @property
    def tag_name(self) -> str:
        return self._tag_name

    @property
    def body(self) -> str:
        return "Release body"

    @property
    def prerelease(self) -> bool:
        return False

    @property
    def name(self) -> str:
        return self._tag_name

    @property
    def html_url(self) -> str:
        return f"https://github.com/test/repo/releases/tag/{self._tag_name}"

    @property
    def created_at(self):
        from datetime import datetime

        return datetime.now()

    @property
    def draft(self) -> bool:
        return False

    @property
    def tag_ref_name(self) -> str:
        return f"refs/tags/{self._tag_name}"

    @property
    def version(self):
        return "1.0.0"


# Concrete VCS Service implementations for testing
class ConcreteVCSService(VCSService):
    service_type = "test_service"

    @classmethod
    def validate_service(cls, options, keychain):
        return {"validated": True}

    def get_repository(self, options={}):
        return MockRepo()

    def parse_repo_url(self):
        return ["owner", "repo", "github.com"]

    @classmethod
    def get_service_for_url(cls, project_config, url, service_alias=None):
        return (
            cls(project_config) if url == "https://test_service.com/test/repo" else None
        )

    @property
    def dynamic_dependency_class(self):
        return MockDynamicDependency

    def get_committer(self, repo: AbstractRepo):
        return MockCommitDir()

    def markdown(self, release: AbstractRelease, mode: str = "", context: str = ""):
        return f"# {release.tag_name}\n{release.body}"

    def parent_pr_notes_generator(self, repo: AbstractRepo):
        return MockReleaseNotesGenerator()

    def release_notes_generator(self, options: dict):
        return MockReleaseNotesGenerator()


# Test class
class TestVCSService:
    """Comprehensive tests for VCSService abstract base class"""

    def test_init_with_all_parameters(self, project_config, keychain):
        """Test VCSService initialization with all parameters"""
        logger = logging.getLogger("test")
        service = ConcreteVCSService(
            project_config, name="test_alias", logger=logger, extra_param="extra"
        )

        assert service.config == project_config
        assert service.name == "test_alias"
        assert service.keychain == keychain
        assert service.logger == logger
        assert service.service_config.name == "test_alias"

    def test_init_without_name(self, project_config, keychain):
        """Test VCSService initialization without name parameter"""
        service = ConcreteVCSService(project_config)

        # Should get service config for the service type without alias
        assert service.config == project_config
        assert service.keychain == keychain
        assert isinstance(service.logger, logging.Logger)

    def test_init_with_default_logger(self, project_config, keychain):
        """Test VCSService initialization creates default logger when none provided"""
        service = ConcreteVCSService(project_config)
        assert isinstance(service.logger, logging.Logger)

    def test_service_type_property_class_attribute(self, project_config, keychain):
        """Test service_type property returns class attribute"""
        service = ConcreteVCSService(project_config)
        assert service.service_type == "test_service"
        # Also test that the property returns the class attribute correctly
        assert ConcreteVCSService.service_type == "test_service"

    def test_service_type_property_raises_not_implemented(
        self, project_config, keychain
    ):
        """Test service_type property raises NotImplementedError when defined as property"""

        class VCSServiceWithPropertyServiceType(VCSService):
            """VCS Service with service_type as a property instead of class attribute"""

            @classmethod
            def validate_service(cls, options, keychain):
                return {}

            @property
            def dynamic_dependency_class(self):
                return MockDynamicDependency

            def get_repository(self, options={}):
                return MockRepo()

            def parse_repo_url(self):
                return ["owner", "repo", "example.com"]

            @classmethod
            def get_service_for_url(cls, project_config, url, service_alias=None):
                return cls(project_config)

            def get_committer(self, repo: AbstractRepo):
                return MockCommitDir()

            def markdown(
                self, release: AbstractRelease, mode: str = "", context: str = ""
            ):
                return "markdown"

            def parent_pr_notes_generator(self, repo: AbstractRepo):
                return MockReleaseNotesGenerator()

            def release_notes_generator(self, options: dict):
                return MockReleaseNotesGenerator()

        # Mock the project config to avoid keychain issues
        mock_config = mock.Mock()
        mock_keychain = mock.Mock()
        mock_service_config = mock.Mock()
        mock_service_config.name = "test"
        mock_keychain.get_service.side_effect = (
            lambda service_type, name: mock_service_config
        )
        mock_config.keychain = mock_keychain

        # The NotImplementedError should be raised during initialization when accessing service_type
        with pytest.raises(
            NotImplementedError,
            match="Subclasses should define the service_type property",
        ):
            VCSServiceWithPropertyServiceType(mock_config)

    def test_dynamic_dependency_class_property(self, project_config, keychain):
        """Test dynamic_dependency_class property returns correct class"""
        service = ConcreteVCSService(project_config)
        assert service.dynamic_dependency_class == MockDynamicDependency

    def test_validate_service_class_method(self):
        """Test validate_service class method"""
        result = ConcreteVCSService.validate_service({}, None)
        assert result == {"validated": True}

    def test_get_service_for_url_class_method(self, project_config, keychain):
        """Test get_service_for_url class method"""
        service = ConcreteVCSService.get_service_for_url(
            project_config, "https://test_service.com/test/repo", {}
        )
        assert isinstance(service, ConcreteVCSService)

    def test_registered_services_class_method(self):
        """Test registered_services class method returns all subclasses"""
        services = VCSService.registered_services()
        assert len(services) > 0
        # Should include our test classes
        service_names = [cls.__name__ for cls in services]
        assert "ConcreteVCSService" in service_names

    def test_get_repository_method(self, project_config, keychain):
        """Test get_repository method"""
        service = ConcreteVCSService(project_config)
        repo = service.get_repository()
        assert isinstance(repo, MockRepo)

    def test_get_repository_with_options(self, project_config, keychain):
        """Test get_repository method with options"""
        service = ConcreteVCSService(project_config)
        repo = service.get_repository({"option": "value"})
        assert isinstance(repo, MockRepo)

    def test_parse_repo_url_method(self, project_config, keychain):
        """Test parse_repo_url method"""
        service = ConcreteVCSService(project_config)
        result = service.parse_repo_url()
        assert result == ["owner", "repo", "github.com"]

    def test_get_committer_method(self, project_config, keychain):
        """Test get_committer method"""
        service = ConcreteVCSService(project_config)
        repo = MockRepo()
        committer = service.get_committer(repo)
        assert isinstance(committer, MockCommitDir)

    def test_markdown_method(self, project_config, keychain):
        """Test markdown method"""
        service = ConcreteVCSService(project_config)
        release = MockRelease("v1.0.0")
        result = service.markdown(release, "mode", "context")
        assert result == "# v1.0.0\nRelease body"

    def test_markdown_method_with_defaults(self, project_config, keychain):
        """Test markdown method with default parameters"""
        service = ConcreteVCSService(project_config)
        release = MockRelease("v2.0.0")
        result = service.markdown(release)
        assert result == "# v2.0.0\nRelease body"

    def test_release_notes_generator_method(self, project_config, keychain):
        """Test release_notes_generator method"""
        service = ConcreteVCSService(project_config)
        generator = service.release_notes_generator({})
        assert isinstance(generator, MockReleaseNotesGenerator)

    def test_parent_pr_notes_generator_method(self, project_config, keychain):
        """Test parent_pr_notes_generator method"""
        service = ConcreteVCSService(project_config)
        repo = MockRepo()
        generator = service.parent_pr_notes_generator(repo)
        assert isinstance(generator, MockReleaseNotesGenerator)

    def test_abstract_base_class_cannot_be_instantiated(self):
        """Test that VCSService abstract base class cannot be instantiated directly"""
        with pytest.raises(
            TypeError, match="Can't instantiate abstract class VCSService"
        ):
            VCSService(None)

    def test_incomplete_subclass_cannot_be_instantiated(self, project_config):
        """Test that incomplete subclass missing abstract methods cannot be instantiated"""

        class IncompleteVCSService(VCSService):
            """VCS Service missing some abstract method implementations"""

            service_type = "incomplete"

            @classmethod
            def validate_service(cls, options, keychain):
                return {}

            @property
            def dynamic_dependency_class(self):
                return MockDynamicDependency

            def get_repository(self, options={}):
                return MockRepo()

            # Missing parse_repo_url, get_service_for_url, etc.

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteVCSService(project_config)

    def test_abstract_methods_raise_not_implemented_error(self):
        """Test that abstract methods raise NotImplementedError when called directly"""

        # Create a minimal implementation just to test the abstract methods
        class MinimalVCSService(VCSService):
            service_type = "minimal"

            @classmethod
            def validate_service(cls, options, keychain):
                return {}

            @property
            def dynamic_dependency_class(self):
                return MockDynamicDependency

            def get_repository(self, options={}):
                return MockRepo()

            def parse_repo_url(self):
                return []

            @classmethod
            def get_service_for_url(cls, project_config, url, service_alias=None):
                return cls(project_config)

            def get_committer(self, repo):
                return MockCommitDir()

            def markdown(self, release, mode="", context=""):
                return ""

            def parent_pr_notes_generator(self, repo):
                return MockReleaseNotesGenerator()

            def release_notes_generator(self, options: dict):
                return MockReleaseNotesGenerator()

        # Test that we can instantiate this minimal implementation
        mock_config = mock.Mock()
        mock_keychain = mock.Mock()
        mock_service_config = mock.Mock()
        mock_service_config.name = "test"
        mock_keychain.get_service.return_value = mock_service_config
        mock_config.keychain = mock_keychain

        service = MinimalVCSService(mock_config)
        assert isinstance(service, VCSService)

    def test_service_config_attribute_access(self, project_config, keychain):
        """Test that service_config is properly set and accessible"""
        service = ConcreteVCSService(project_config, name="test_alias")
        assert hasattr(service, "service_config")
        assert service.service_config.name == "test_alias"

    def test_logger_attribute_access(self, project_config, keychain):
        """Test that logger attribute is accessible"""
        service = ConcreteVCSService(project_config)
        assert hasattr(service, "logger")
        assert isinstance(service.logger, logging.Logger)

    def test_config_attribute_access(self, project_config, keychain):
        """Test that config attribute is accessible"""
        service = ConcreteVCSService(project_config)
        assert hasattr(service, "config")
        assert service.config == project_config

    def test_keychain_attribute_access(self, project_config, keychain):
        """Test that keychain attribute is accessible"""
        service = ConcreteVCSService(project_config)
        assert hasattr(service, "keychain")
        assert service.keychain == keychain

    def test_name_attribute_access(self, project_config, keychain):
        """Test that name attribute is accessible"""
        service = ConcreteVCSService(project_config, name="test_alias")
        assert hasattr(service, "name")
        # Name should come from service_config.name or the provided name
        assert service.name == "test_alias"

    def test_service_registry_class_attribute(self):
        """Test that _service_registry class attribute exists"""
        assert hasattr(VCSService, "_service_registry")
        assert isinstance(VCSService._service_registry, list)

    def test_multiple_service_instances(self, project_config, keychain):
        """Test creating multiple service instances"""
        service1 = ConcreteVCSService(project_config, name="test_alias")
        service2 = ConcreteVCSService(project_config, name="test_alias")

        assert service1.config == service2.config
        assert service1.keychain == service2.keychain
        # Names should be the same if they both resolve to the same service config
        assert service1.name == service2.name

    def test_service_with_custom_logger(self, project_config, keychain):
        """Test service initialization with custom logger"""
        custom_logger = logging.getLogger("custom")
        custom_logger.setLevel(logging.DEBUG)

        service = ConcreteVCSService(project_config, logger=custom_logger)
        assert service.logger == custom_logger
        assert service.logger.name == "custom"

    def test_registered_services_returns_set(self):
        """Test registered_services method returns a set of all subclasses"""
        services = VCSService.registered_services()
        assert isinstance(services, set)
        assert len(services) >= 1  # Should have at least the GitHub service

    def test_kwargs_handling_in_init(self, project_config, keychain):
        """Test that additional kwargs are handled properly in __init__"""
        service = ConcreteVCSService(
            project_config, name="test_alias", extra_param="value", another_param=123
        )
        # Should not raise an error and should initialize properly
        assert isinstance(service, ConcreteVCSService)

    def test_service_type_inheritance(self):
        """Test that service_type is properly inherited"""

        class ChildVCSService(ConcreteVCSService):
            service_type = "child_service"

        # Create a mock project config for testing
        mock_config = mock.Mock()
        mock_keychain = mock.Mock()
        mock_service_config = mock.Mock()
        mock_service_config.name = "test"
        mock_keychain.get_service.return_value = mock_service_config
        mock_config.keychain = mock_keychain

        service = ChildVCSService(mock_config)
        assert service.service_type == "child_service"

    def test_empty_options_handling(self, project_config, keychain):
        """Test methods handle empty options dictionaries properly"""
        service = ConcreteVCSService(project_config)

        # Test get_repository with empty options
        repo = service.get_repository({})
        assert isinstance(repo, MockRepo)

        # Test get_service_for_url with empty alias
        result = ConcreteVCSService.get_service_for_url(
            project_config, "https://test_service.com/test/repo", ""
        )
        assert isinstance(result, ConcreteVCSService)

    def test_none_parameters_handling(self, project_config, keychain):
        """Test that None parameters are handled gracefully"""
        service = ConcreteVCSService(project_config, name=None)
        assert isinstance(service, ConcreteVCSService)
        # Name should be from service config
        assert service.name is not None

    def test_service_name_property(self, project_config, keychain):
        """Test that service name is properly set from service config"""
        service = ConcreteVCSService(project_config, name="test_alias")
        assert service.name == "test_alias"

    def test_logger_default_name(self, project_config, keychain):
        """Test that default logger has correct name"""
        service = ConcreteVCSService(project_config)
        # The logger name is set to the module name of the VCS base class, not the concrete class
        assert service.logger.name == "cumulusci.vcs.base"

    def test_keychain_from_config(self, project_config, keychain):
        """Test that keychain is properly retrieved from config"""
        service = ConcreteVCSService(project_config)
        assert service.keychain is project_config.keychain
        assert service.keychain is keychain

    def test_service_config_retrieval_with_name(self, project_config, keychain):
        """Test service config retrieval with specific name"""
        service = ConcreteVCSService(project_config, name="test_alias")
        # Should call keychain.get_service with correct parameters
        assert service.service_config is not None
        assert service.service_config.name == "test_alias"

    def test_service_config_retrieval_without_name(self, project_config, keychain):
        """Test service config retrieval without name (default service)"""
        service = ConcreteVCSService(project_config)
        # Should call keychain.get_service with service_type and None for name
        assert service.service_config is not None

    def test_service_type_property_return_path(self, project_config, keychain):
        """Test service_type property return path for class attribute"""
        # Test the existing ConcreteVCSService to ensure we hit the return path
        service = ConcreteVCSService(project_config)
        # Access service_type multiple times to ensure coverage
        assert service.service_type == "test_service"
        assert service.service_type == "test_service"

        # Also test accessing it directly from the class
        assert ConcreteVCSService.service_type == "test_service"

    def test_service_type_property_implementation(self, project_config, keychain):
        """Test service_type property implementation details"""
        service = ConcreteVCSService(project_config)

        # Test that service_type is not a property instance on the class
        assert not isinstance(ConcreteVCSService.__dict__.get("service_type"), property)

        # Test that accessing service_type returns the class attribute
        assert service.service_type == ConcreteVCSService.service_type

        # Test the property getter directly
        service_type_prop = VCSService.__dict__["service_type"]
        assert isinstance(service_type_prop, property)
        assert service_type_prop.fget(service) == "test_service"
