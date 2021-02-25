import re

from io import StringIO
from logging import getLogger
import typing as T
from pathlib import Path

from yaml.error import MarkedYAMLError

from cumulusci.core.exceptions import YAMLParseException
from cumulusci.utils.fileutils import load_from_source, FSResource
from cumulusci.utils.yaml.line_number_annotator import safe_load_with_linenums


NBSP = "\u00A0"

pattern = re.compile(r"^\s*[\u00A0]+\s*", re.MULTILINE)

default_logger = getLogger(__name__)


def _replace_nbsp(origdata, filename, logger=default_logger):
    "Replace nbsp characters in leading whitespace in a YAML file."
    counter = 0

    def _replacer_func(matchobj):
        nonlocal counter
        counter += 1
        string = matchobj.group(0)
        rc = string.replace(NBSP, " ")
        return rc

    data = pattern.sub(_replacer_func, origdata)

    if counter:
        plural = "s were" if counter > 1 else " was"
        logger.warning(
            f"Note: {counter} lines with non-breaking space character{plural} detected in {filename}.\n"
            "Perhaps you cut and pasted from a Web page?\n"
            "Future versions of CumulusCI may disallow these characters.\n"
        )
    return data


def load_yaml_data(
    source: T.Union[str, T.IO[T.Text], Path, FSResource], context: str = None
) -> T.Tuple[T.Union[T.Dict, T.List]]:
    """Load a file, convert NBSP->space and parse it in YAML.

    Raises YAMLParseException with a nicely formatted error message
    if an error occurs while parsing.

    Returns a pair of data, line_number_manager

    If you use this method directly (or, heaven forbid, yaml.safe_load)
    consider making a CCIModel subclass instead.
    """
    with load_from_source(source) as (f_config, filename):
        if filename == "<stream>":
            filename = "a yaml file"
        context = context or filename
        data = _replace_nbsp(f_config.read(), context)
        try:
            data, linenums = safe_load_with_linenums(StringIO(data), filename)
        except MarkedYAMLError as e:
            line_num = e.problem_mark.line + 1
            column_num = e.problem_mark.column
            message = (
                f"An error occurred parsing yaml file at line {line_num}, column {column_num}.\n"
                + f"{filename}:{line_num}:{column_num}\n"
                + f"Error message: {e.problem}."
            )
            raise YAMLParseException(message)
        except Exception as e:
            message = f"An error occurred parsing {filename}.\nError message: {e}"
            raise YAMLParseException(message)

        return data, linenums
