import logging
from abc import ABC, abstractmethod
from datetime import datetime
from io import StringIO
from re import Pattern
from typing import Optional, Union


class AbstractRepo(ABC):
    """Abstract base class for repositories.
    This is the abstract base class for defining repository interfaces.

    Raises:
        NotImplementedError: Raised when a subclass does not implement the required method.
    """

    repo: object
    logger: logging.Logger
    options: dict
    repo_name: str
    repo_owner: str
    repo_url: str
    project_config: Optional[object] = None

    def __init__(self, **kwargs) -> None:
        """Initializes the AbstractRepo."""
        self.repo = kwargs.get("repo")
        self.logger = kwargs.get("logger", None)
        self.options = kwargs.get("options", {})
        self.repo_name = kwargs.get("repo_name", None)
        self.repo_owner = kwargs.get("repo_owner", None)
        self.repo_url = self.options.get("repository_url", None)

    def __eq__(self, other):
        return isinstance(other, AbstractRepo) and self.repo_url == other.repo_url

    def __hash__(self):
        return hash(self.repo_url)

    @property
    @abstractmethod
    def owner_login(self) -> str:
        """Returns the login of the repository owner."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def get_ref(self, ref_sha: str) -> "AbstractRef":
        """Returns a Reference object for the given SHA."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def get_ref_for_tag(self, tag_name: str) -> "AbstractRef":
        """Gets a Reference object for the tag with the given name.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the reference for a tag.
        The method should return an instance of a class that implements
        the AbstractRef interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def get_tag_by_ref(self, ref: object, tag_name: str = None) -> "AbstractGitTag":
        """Gets a Git Tag for with the given ref.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the tag.
        The method should return an instance of a class that implements
        the AbstractGitTag interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def create_tag(
        self,
        tag_name: str,
        message: str,
        sha: str,
        obj_type: str,
        tagger={},
        lightweight: Optional[bool] = False,
    ) -> "AbstractGitTag":
        """Create a Git Tag object for the tag with the given name.
        This method should be overridden by subclasses to provide
        the specific implementation for creating a Git Tag.
        The method should return an instance of a class that implements
        the AbstractGitTag interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def branch(self, branch_name: str) -> "AbstractBranch":
        """Gets a Reference object for the branch with the given name.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the reference for a branch.
        The method should return an instance of a class that implements
        the AbstractBranch interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def branches(self) -> list:
        """Gets a list of all branches in the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the branches.
        The method should return a list of instances of classes that implement
        the AbstractBranch interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def compare_commits(
        self, base: str, head: str, source: str
    ) -> "AbstractComparison":
        """Compares the given head with the given base.
        This method should be overridden by subclasses to provide
        the specific implementation for comparing commits.
        The method should return an instance of AbstractComparison."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def merge(
        self, base: str, head: str, source: str, message: str = ""
    ) -> "AbstractRepoCommit":
        """Merges the given base and head with the specified commit.
        This method should be overridden by subclasses to provide
        the specific implementation for merging commits.
        The method should return an instance of AbstractRepoCommit."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def pull_requests(self, **kwargs) -> list["AbstractPullRequest"]:
        """Fetches all pull requests from the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving pull requests.
        The method should return a list of instances of classes that implement
        the AbstractPullRequest interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def create_pull(
        self,
        title: str,
        base: str,
        head: str,
        body: str = None,
        maintainer_can_modify: bool = None,
        options: dict = {},
    ) -> "AbstractPullRequest":
        """Creates a pull request in the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for creating pull requests.
        The method should return an instance of a class that implements
        the AbstractPullRequest interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def get_commit(self, commit_sha: str) -> "AbstractRepoCommit":
        """Gets a commit object for the given commit SHA.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the commit.
        The method should return an instance of a class that implements
        the AbstractRepoCommit interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @property
    @abstractmethod
    def default_branch(self) -> str:
        """Gets the default branch of the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the default branch.
        The method should return the name of the default branch."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def archive(self, format: str, zip_content: Union[str, object], ref=None) -> bytes:
        """Archives the repository content as a zip file."""
        # This method should be overridden by subclasses to provide
        # the specific implementation for archiving the repository.
        # The method should return a bytes object representing the archived content.
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def full_name(self) -> str:
        """Gets the full name of the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the full name.
        The method should return a string representing the full name of the repository."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def release_from_tag(self, tag_name: str) -> "AbstractRelease":
        """Gets a Release object for the tag with the given name.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the release.
        The method should return an instance of a class that implements
        the AbstractRelease interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def create_release(
        self,
        tag_name: str,
        name: str,
        body: str = None,
        draft: bool = False,
        prerelease: bool = False,
        options: dict = {},
    ) -> "AbstractRelease":
        """Creates a release in the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for creating releases.
        The method should return an instance of a class that implements
        the AbstractRelease interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def releases(self) -> list["AbstractRelease"]:
        """Fetches all releases from the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving releases.
        The method should return a list of instances of classes that implement
        the AbstractRelease interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def latest_release(self) -> Optional["AbstractRelease"]:
        """Gets the latest release from the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the latest release.
        The method should return an instance of a class that implements
        the AbstractRelease interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def has_issues(self) -> bool:
        """Checks if the repository supports issues.
        This method should be overridden by subclasses to provide
        the specific implementation for checking if the repository supports issues.
        The method should return True if the repository supports issues, otherwise False."""
        raise NotImplementedError(
            "Subclasses should implement the has_issues method to check if the repository supports issues."
        )

    @abstractmethod
    def get_pr_issue_labels(self, pull_request: "AbstractPullRequest") -> list[str]:
        """Gets the issue labels for the given pull request.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the labels.
        The method should return a list of labels associated with the pull request."""
        raise NotImplementedError("Subclasses should implement this method.")

    @abstractmethod
    def get_latest_prerelease(self) -> Optional["AbstractRelease"]:
        """Gets the latest pre-release from the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the latest pre-release.
        The method should return an instance of a class that implements
        the AbstractRelease interface."""
        raise NotImplementedError("Subclasses should implement this method.")

    @abstractmethod
    def directory_contents(self, subfolder: str, return_as, ref: str) -> dict:
        """Gets the contents of a directory in the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the directory contents.
        The method should return the contents of the directory as a dictionary or list,
        depending on the value of return_as."""
        raise NotImplementedError("Subclasses should implement this method.")

    @abstractmethod
    def file_contents(self, file: str, ref: str) -> StringIO:
        """Gets the contents of a file in the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the file contents.
        The method should return the contents of the file as a StringIO object."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def clone_url(self) -> str:
        """Gets the https clone URL for the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the clone URL.
        The method should return a string representing the clone URL of the repository."""
        raise NotImplementedError("Subclasses should implement this method.")

    @abstractmethod
    def create_commit_status(
        self,
        commit_id: str,
        context: str,
        state: str,
        description: str,
        target_url: str,
    ) -> "AbstractRepoCommit":
        """Creates a commit status in the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for creating commit statuses.
        The method should not return anything, but it should raise an exception
        if the commit status creation fails."""
        raise NotImplementedError("Subclasses should implement this method.")


class AbstractRelease(ABC):
    """Abstract base class for releases.
    This is the abstract base class for defining git releases.

    Raises:
        NotImplementedError: Raised when a subclass does not implement the required method.
    """

    release: object

    def __init__(self, **kwargs) -> None:
        """Initializes the AbstractRelease."""
        self.release = kwargs.get("release", None)

    @property
    @abstractmethod
    def tag_name(self) -> str:
        """Gets the tag name of the release."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def body(self) -> str:
        """Gets the body of the release."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def prerelease(self) -> bool:
        """Checks if the release is a pre-release."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def name(self) -> str:
        """Gets the name of the release."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def html_url(self) -> str:
        """Gets the HTML URL of the release."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def created_at(self) -> datetime:
        """Gets the creation date of the release."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def draft(self) -> bool:
        """Checks if the release is a draft."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def tag_ref_name(self) -> str:
        """Gets the tag reference name of the release."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def updateable(self) -> bool:
        """Checks if the release is updateable."""
        return False


class AbstractRef(ABC):
    """Abstract base class for Refs.
    This is the abstract base class for defining git references.

    Raises:
        NotImplementedError: Raised when a subclass does not implement the required method.
    """

    ref: object

    def __init__(self, ref, **kwargs) -> None:
        """Initializes the AbstractRef."""
        self.ref = ref


class AbstractGitTag(ABC):

    tag: object
    _sha: str = ""

    def __init__(self, **kwargs) -> None:
        """Initializes the AbstractGitTag."""
        self.tag = kwargs.get("tag", None)

    @property
    def sha(self) -> str:
        """Gets the SHA for the git tag."""
        return self._sha

    @sha.setter
    def sha(self, value: str):
        """Sets the SHA for the git tag.

        Args:
            value (str): The SHA for the git tag.
        """
        self._sha = value

    @property
    @abstractmethod
    def message(self) -> str:
        """Gets the message of the tag."""
        raise NotImplementedError("Subclasses should implement this method.")


class AbstractBranch(ABC):
    """Abstract base class for Branch.
    This is the abstract base class for defining git branches.

    Raises:
        NotImplementedError: Raised when a subclass does not implement the required method.
    """

    repo: AbstractRepo
    branch: object
    name: str

    def __init__(self, repo: AbstractRepo, branch_name: str, **kwargs) -> None:
        """Initializes the AbstractBranch."""
        self.repo = repo
        self.name = branch_name

        self.branch = kwargs.get("branch", None)
        if not self.branch:
            self.get_branch()

    @abstractmethod
    def get_branch(self) -> None:
        """Gets the branch object for the current branch name."""
        raise NotImplementedError("Subclasses should implement this method.")

    @classmethod
    @abstractmethod
    def branches(cls, repo: AbstractRepo) -> list["AbstractBranch"]:
        """Gets a list of all branches in the repository.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the branches.
        The method should return a list of instances of classes that implement
        the AbstractBranch interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @property
    @abstractmethod
    def commit(self) -> "AbstractRepoCommit":
        """Gets the branch commit for the current branch."""
        raise NotImplementedError("Subclasses should provide their own implementation")


class AbstractComparison(ABC):
    """Abstract base class for comparisons.
    This is the abstract base class for defining git comparisons.

    Raises:
        NotImplementedError: Raised when a subclass does not implement the required method.
    """

    comparison: object

    def __init__(self, repo: AbstractRepo, base: str, head: str, **kwargs) -> None:
        """Initializes the AbstractComparison."""
        self.repo = repo
        self.base = base
        self.head = head
        self.comparison = kwargs.get("comparison", None)

    @classmethod
    @abstractmethod
    def compare(cls, repo: AbstractRepo, base: str, head: str) -> "AbstractComparison":
        """Compares the given base and head with the specified commit.
        This method should be overridden by subclasses to provide
        the specific implementation for comparing commits.
        The method should return an instance of AbstractComparison."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def get_comparison(self) -> None:
        """Gets the comparison object for the current base and head."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def files(self) -> list:
        """Gets the files changed in the comparison."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def behind_by(self) -> int:
        """Gets the number of commits the head is behind the base."""
        raise NotImplementedError("Subclasses should implement this method.")


class AbstractRepoCommit(ABC):
    """Abstract base class for commits.
    This is the abstract base class for defining git commits.

    Raises:
        NotImplementedError: Raised when a subclass does not implement the required method.
    """

    commit: object

    def __init__(self, **kwargs) -> None:
        """Initializes the AbstractRepoCommit."""
        self.commit = kwargs.get("commit", None)

    @abstractmethod
    def get_statuses(self, context: str, regex_match: Pattern[str]) -> Optional[str]:
        """Gets the statuses for the commit.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the statuses.
        The method should return a string if a match is found, otherwise None."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def parents(self) -> list["AbstractRepoCommit"]:
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def sha(self) -> str:
        """Gets the SHA of the commit."""
        raise NotImplementedError("Subclasses should implement this method.")


class AbstractPullRequest(ABC):
    """Abstract base class for pull requests.
    This is the abstract base class for defining git pull requests.

    Raises:
        NotImplementedError: Raised when a subclass does not implement the required method.
    """

    repo: Union[AbstractRepo, None]
    pull_request: Union[object, None]

    def __init__(self, **kwargs) -> None:
        """Initializes the AbstractPullRequest."""
        self.repo = kwargs.get("repo", None)
        self.pull_request = kwargs.get("pull_request", None)

    @classmethod
    @abstractmethod
    def pull_requests(cls, *args, **kwargs) -> list["AbstractPullRequest"]:
        """Fetches all pull requests from the repository."""
        raise NotImplementedError("Subclasses should implement this method.")

    @classmethod
    @abstractmethod
    def create_pull(cls, *args, **kwargs) -> "AbstractPullRequest":
        """Creates a pull request on the repository."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def number(self) -> int:
        """Gets the pull request number."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def title(self) -> str:
        """Gets the pull title."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def base_ref(self) -> str:
        """Gets the base reference of the pull request."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def head_ref(self) -> str:
        """Gets the head reference of the pull request."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    @abstractmethod
    def merged_at(self) -> datetime:
        """Gets the date when the pull request was merged."""
        raise NotImplementedError("Subclasses should implement this method.")
