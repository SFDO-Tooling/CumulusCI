import typing as T

import yaml

from yaml.composer import Composer
from yaml.constructor import SafeConstructor

from pydantic.error_wrappers import ValidationError

from cumulusci.core.exceptions import ConfigValidationError

SHARED_OBJECT = "#SHARED_OBJECT"


class LineTracker(T.NamedTuple):
    """Represents the location of an error"""

    filename: str
    line_num: int


# pyyaml internals magic
class LineNumberSafeLoader(yaml.SafeLoader):
    """Safe loader subclass that tracks linenumbers"""

    def __init__(self, filestream, filename):
        super().__init__(filestream)
        self.filename = filename
        self.line_numbers: T.Dict[int, LineTracker] = {}

    def compose_node(self, parent, index):
        # the line number where the previous token has ended (plus empty lines)
        line = self.line
        node = Composer.compose_node(self, parent, index)
        node.__line__ = line + 1
        return node

    def construct_mapping(self, node, deep=False):
        mapping = SafeConstructor.construct_mapping(self, node, deep=deep)
        mapping["__line__"] = LineTracker(self.filename, node.__line__)
        return mapping

    def construct_scalar(self, node):
        scalar = SafeConstructor.construct_scalar(self, node)
        key = id(scalar)
        if not self.line_numbers.get(key):
            self.line_numbers[key] = LineTracker(self.filename, node.__line__)
        else:
            self.line_numbers[key] = SHARED_OBJECT
        return scalar


class LineNumberAnnotator:
    """Class that can keep track of locations of parse results"""

    def safe_load(self, filestream: T.IO[str], filename: str) -> T.Union[list, dict]:
        loader = LineNumberSafeLoader(filestream, filename)

        self.annotated_data = loader.get_single_data()
        clean_data = _remove_linenums(self.annotated_data)
        self.line_numbers = loader.line_numbers
        return clean_data

    def linenum_from_pydantic_error_dict(self, error) -> T.Optional[int]:
        """Find a line number from a Pydantic error dict"""
        loc = error["loc"]
        assert isinstance(loc, tuple)
        rc = None
        __root__, *rest = loc
        pos = self.annotated_data
        while rest and isinstance(pos, (dict, list)):
            index, *rest = rest
            try:
                pos = pos[index]
                if isinstance(pos, dict):
                    rc = pos["__line__"]
            except KeyError:
                pass

        if id(pos) in self.line_numbers:
            return self.line_numbers[id(pos)].line_num

        return rc.line_num if rc else None

    def exception_with_line_numbers(self, ve: ValidationError, filename: str):
        """Generate an exception that formats itself nicely."""
        errors = ve.errors()
        for error in errors:
            linenum = self.linenum_from_pydantic_error_dict(error) or "(no linenum)"
            context_str = f"{filename}:{linenum}"
            error["loc"] = [context_str, *(e for e in error["loc"] if e != "__root__")]

        return ConfigValidationError(errors=errors)


def _remove_linenums(o):
    """Remove linenums from a parsed data structure

    Linenums are often not supported by downstream processing.
    Pydantic in partcular.
    """
    if isinstance(o, list):
        return [_remove_linenums(e) for e in o]
    elif isinstance(o, dict):
        return {k: _remove_linenums(v) for k, v in o.items() if k != "__line__"}
    else:
        return o


def safe_load_with_linenums(
    open_file: T.IO[T.Text], filename: str
) -> T.Tuple[T.Union[dict, list], LineNumberAnnotator]:
    y = LineNumberAnnotator()
    data = y.safe_load(open_file, filename)
    return data, y
