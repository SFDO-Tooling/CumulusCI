from abc import ABC, abstractmethod


class TagInterface(ABC):
    tag: object

    def __init__(self, tag):
        self.tag = tag

    def __getattr__(self, attr):
        return getattr(self.tag, attr)

    @abstractmethod
    def get_tag(self):
        pass
