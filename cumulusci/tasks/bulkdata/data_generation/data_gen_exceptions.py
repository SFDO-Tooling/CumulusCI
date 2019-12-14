class DataGenError(Exception):
    def __init__(self, message, filename, line_num):
        self.message = message
        self.filename = filename
        self.line_num = line_num
        assert isinstance(filename, (str, type(None)))
        assert isinstance(line_num, (int, type(None)))
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message}\n near {self.filename}:{self.line_num}"


class DataGenSyntaxError(DataGenError):
    pass


class DataGenNameError(DataGenError):
    pass


class DataGenValueError(DataGenError):
    pass


def fix_exception(message, parentobj, e):
    """Add filename and linenumber to an exception if needed"""
    filename, line_num = parentobj.filename, parentobj.line_num
    if isinstance(e, DataGenError):
        if not e.filename:
            e.filename = filename
        if not e.line_num:
            e.line_num = line_num
        raise e
    else:
        raise DataGenError(message, filename, line_num) from e
