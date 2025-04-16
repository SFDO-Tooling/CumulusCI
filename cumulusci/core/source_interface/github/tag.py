from github3.git import Tag

from ..tag import TagInterface


class TagAdapter(TagInterface):
    tag: Tag

    def get_tag(self):
        pass
