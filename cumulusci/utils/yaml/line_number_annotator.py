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


class LineNumberAnnotator:
    """Class that can keep track of locations of parse results"""

    def safe_load(self, filestream: T.IO[str], filename: str) -> T.Union[list, dict]:
        loader = yaml.SafeLoader(filestream)

        # map IDs to line numbers for non-dict objects
        line_numbers: T.Dict[int, LineTracker] = {}

        # pyyaml internals magic
        def compose_node(parent, index):
            # the line number where the previous token has ended (plus empty lines)
            line = loader.line
            node = Composer.compose_node(loader, parent, index)
            node.__line__ = line + 1
            return node

        def construct_mapping(node, deep=False):
            mapping = SafeConstructor.construct_mapping(loader, node, deep=deep)
            mapping["__line__"] = LineTracker(filename, node.__line__)
            return mapping

        def construct_scalar(node):
            scalar = SafeConstructor.construct_scalar(loader, node)
            key = id(scalar)
            if not line_numbers.get(key):
                line_numbers[key] = LineTracker(filename, node.__line__)
            else:
                line_numbers[key] = SHARED_OBJECT
            return scalar

        loader.compose_node = compose_node  # type: ignore
        loader.construct_mapping = construct_mapping  # type: ignore
        loader.construct_scalar = construct_scalar  # type: ignore
        self.annotated_data = loader.get_single_data()
        clean_data = _remove_linenums(self.annotated_data)
        self.line_numbers = line_numbers
        return clean_data

    def linenum_from_pydantic_error_dict(self, error) -> T.Optional[int]:
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

    def enhance_locations(self, ve: ValidationError, filename: str):
        errors = ve.errors()
        for error in errors:
            linenum = self.linenum_from_pydantic_error_dict(error) or "(no linenum)"
            context_str = f"{filename}:{linenum}"
            error["loc"] = [context_str, *(e for e in error["loc"] if e != "__root__")]

        return ConfigValidationError(errors=errors)


def _remove_linenums(o):
    if isinstance(o, list):
        return [_remove_linenums(e) for e in o]
    elif isinstance(o, dict):
        return {k: _remove_linenums(v) for k, v in o.items() if k != "__line__"}
    else:
        return o


def safe_load_with_linenums(open_file: T.IO[T.Text], filename: str):
    y = LineNumberAnnotator()
    data = y.safe_load(open_file, filename)
    return data, y


if __name__ == "__main__":
    from cumulusci.utils.yaml.cumulusci_yml import validate_data
    import sys

    with open(sys.argv[1]) as f:
        y = LineNumberAnnotator()
        data = y.safe_load(f, f.name)

        errors = []
        validate_data(data, f.name, on_error=errors.append)

        for error in errors:
            print(f"{error['loc'][0]}:{y.linenum_from_pydantic_error(error)}")
