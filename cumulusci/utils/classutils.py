def get_all_subclasses(cls):
    """Return all subclasses of the given class"""
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in get_all_subclasses(c)]
    )


def namedtuple_as_simple_dict(self):
    def simplify(x):
        if hasattr(x, "simplify"):
            return x.simplify()
        else:
            return x

    return {
        name: simplify(getattr(self, name, None)) for name in self.__class__._fields
    }
