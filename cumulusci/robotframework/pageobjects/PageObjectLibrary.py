import inspect


class _PageObjectLibrary(object):
    """
    This uses robot's hybrid library API to create a keyword library
    from any object. All of the methods in the object will be exposed
    as keywords, except for a method named 'get_keyword_names'

    For example, the following code will create an instance of this class
    with the _obj parameter set to the instance of SomeKeywordClass():

        keywords = SomeKeywordClass()
        BuiltIn().import_library("PageObjectLibrary", keywords)

    This isn't designed to be called from test suites. It's for internal
    use only.
    """

    ROBOT_LIBRARY_SCOPE = "TEST SUITE"

    def __init__(self, obj, libname=None):
        self._obj = obj
        self._libname = libname if libname is not None else obj.__class__.__name__

        self._keyword_names = sorted(
            [
                member[0]
                for member in inspect.getmembers(obj, inspect.isroutine)
                if (not member[0].startswith("_")) and member[0] != "get_keyword_names"
            ]
        )

    def get_keyword_names(self):
        return self._keyword_names

    def __repr__(self):
        return "<{} obj={}>".format(
            self.__class__.__name__, self._obj.__class__.__name__
        )

    def __getattr__(self, item):
        if hasattr(self._obj, item):
            return getattr(self._obj, item)
        raise AttributeError(item)
