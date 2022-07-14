import typing as T


class OrderedSet(dict):
    """Extremely minimal ordered set

    Use with care, because very few methods are implemented."""

    def add(self, item):
        self[item] = item

    def remove(self, item):
        del self[item]

    def copy(self):
        return OrderedSet(self)

    def update(self, other: T.Iterable):
        super().update(zip(other, other))


# Workaround for Python 3.8
OrderedSetType = T.Iterable
