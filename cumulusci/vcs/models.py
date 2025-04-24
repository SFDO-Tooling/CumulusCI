from abc import ABC, abstractmethod


class AbstractRepo(ABC):
    """Abstract base class for repositories.
    This is the abstract base class for defining repository interfaces.

    Raises:
        NotImplementedError: Raised when a subclass does not implement the required method.
    """

    repo: object

    @abstractmethod
    def get_ref_for_tag(self, tag_name: str) -> "AbstractRef":
        """Gets a Reference object for the tag with the given name.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the reference for a tag.
        The method should return an instance of a class that implements
        the AbstractRef interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def get_tag_by_ref(self, ref: str, tag_name: str = None) -> "AbstractGitTag":
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
    _sha: str

    def __init__(self, tag, **kwargs) -> None:
        """Initializes the AbstractGitTag."""
        self.tag = tag
        self.sha = None

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
