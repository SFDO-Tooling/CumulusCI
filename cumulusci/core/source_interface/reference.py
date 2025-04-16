from abc import ABC, abstractmethod


class ReferenceInterface(ABC):
    def __init__(self, ref):
        self.ref = ref

    def __getattr__(self, attr):
        return getattr(self.ref, attr)

    @abstractmethod
    def get_refs(self):
        pass
