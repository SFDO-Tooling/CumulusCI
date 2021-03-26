def get_all_subclasses(cls):
    """Return all subclasses of the given class"""
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in get_all_subclasses(c)]
    )
