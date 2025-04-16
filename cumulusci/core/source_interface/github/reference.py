from github3.git import Reference

from ..reference import ReferenceInterface


class ReferenceAdapter(ReferenceInterface):
    ref: Reference

    def get_refs(self):
        pass
