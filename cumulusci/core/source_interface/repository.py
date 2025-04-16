from abc import ABC, abstractmethod


class RepositoryInterface(ABC):
    @abstractmethod
    def get_repo(self):
        pass

    @abstractmethod
    def get_ref_for_tag(self):
        pass

    @abstractmethod
    def get_tag_by_name(self):
        pass

    @abstractmethod
    def create_tag(self):
        pass
