from abc import ABC, abstractmethod


class SourceControlProvider(ABC):
    @abstractmethod
    def get_repository(self) -> None:
        """Subclasses should override to provide their implementation"""
        raise NotImplementedError("Subclasses should provide their own implementation")
