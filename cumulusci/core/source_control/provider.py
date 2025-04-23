from abc import ABC, abstractmethod


class SourceControlProvider(ABC):
    @property
    def service_type(self):
        return self._service_type

    @service_type.setter
    @abstractmethod
    def service_type(self, val):
        self._service_type = val

    @classmethod
    @abstractmethod
    def validate_service(options: dict, keychain):
        # This is a placeholder for the actual validation logic
        # that should be implemented in the subclasses.
        # For now, we just raise NotImplementedError to indicate
        # that this method should be overridden.
        raise NotImplementedError("Subclasses should provide their own implementation")

    # @abstractmethod
    def get_repository(self) -> None:
        """Subclasses should override to provide their implementation"""
        raise NotImplementedError("Subclasses should provide their own implementation")
