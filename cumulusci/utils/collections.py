import typing as T


class OrderedSet(dict):
    """Extremely minimal ordered set

    Use with care, because very few methods are implemented."""

    def __init__(self, other: T.Optional[T.Iterable] = None):
        if other is not None:
            self.update(other)

    def add(self, item):
        self[item] = item

    def remove(self, item):
        del self[item]

    def copy(self):
        return OrderedSet(self)

    def update(self, other: T.Iterable):
        super().update((x, x) for x in other)

    def union(self, other: T.Iterable):
        new = OrderedSet(self)
        new.update(other)
        return new


# Workaround for Python 3.8
OrderedSetType = T.Iterable
