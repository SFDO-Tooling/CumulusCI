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
