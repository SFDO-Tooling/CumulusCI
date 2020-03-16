class classproperty(object):
    """Similar to @property, but allows class-level properties.

    That is, a property whose getter is like a classmethod."""

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)
