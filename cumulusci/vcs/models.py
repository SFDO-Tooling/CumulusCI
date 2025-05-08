import logging
from abc import ABC, abstractmethod
from re import Pattern
from typing import Optional


class AbstractRepo(ABC):
    """Abstract base class for repositories.
    This is the abstract base class for defining repository interfaces.

    Raises:
        NotImplementedError: Raised when a subclass does not implement the required method.
    """

    repo: object
    logger: logging.Logger
    options: dict

    def __init__(self, **kwargs) -> None:
        """Initializes the AbstractRepo."""
        self.repo = kwargs.get("repo", None)
        self.logger = kwargs.get("logger", None)
        self.options = kwargs.get("options", {})

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
        self, tag_name: str, message: str, sha: str, obj_type: str, tagger={}
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
    def compare_commits(self, base: str, head: str) -> "AbstractComparison":
        """Compares the given head with the given base.
        This method should be overridden by subclasses to provide
        the specific implementation for comparing commits.
        The method should return an instance of AbstractComparison."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def merge(self, base: str, head: str, message: str = "") -> "AbstractRepoCommit":
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

    def __init__(self, tag, **kwargs) -> None:
        """Initializes the AbstractGitTag."""
        self.tag = tag

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

    @abstractmethod
    def get_commit(self, commit_sha: str) -> "AbstractRepoCommit":
        """Gets a commit object for the given commit SHA.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the commit.
        The method should return an instance of a class that implements
        the AbstractRepoCommit interface."""
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


class AbstractPullRequest(ABC):
    """Abstract base class for pull requests.
    This is the abstract base class for defining git pull requests.

    Raises:
        NotImplementedError: Raised when a subclass does not implement the required method.
    """

    repo: AbstractRepo
    pull_request: object

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
    def base_ref(self) -> str:
        """Gets the base reference of the pull request."""
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def head_ref(self) -> str:
        """Gets the head reference of the pull request."""
        raise NotImplementedError("Subclasses should implement this method.")
