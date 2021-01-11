import re
import yaml

from io import StringIO
from logging import getLogger
from typing import IO, Text
from yaml.error import MarkedYAMLError

from cumulusci.core.exceptions import CumulusCIException


NBSP = "\u00A0"

pattern = re.compile(r"^\s*[\u00A0]+\s*", re.MULTILINE)

logger = getLogger(__name__)


def _replace_nbsp(origdata):
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
            f"Note: {counter} lines with non-breaking space character{plural} detected in cumulusci.yml.\n"
            "Perhaps you cut and pasted from a Web page?\n"
            "Future versions of CumulusCI may disallow these characters.\n"
        )
    return data


GENERIC_ERR_MSG = "An error occurred parsing a yaml file. Error message: {}"


def cci_safe_load(f_config: IO[Text]):
    """Load a file, convert NBSP->space and parse it in YAML.
    Raises CumulusCIException if an error occurs while parsing.
    """
    data = _replace_nbsp(f_config.read())
    try:
        rc = yaml.safe_load(StringIO(data))
    except MarkedYAMLError as e:
        if hasattr(f_config, "name"):
            line_num = e.problem_mark.line
            column_num = e.problem_mark.column
            message = f"An error occurred parsing {f_config.name} at line {line_num}, column {column_num}.\nError message: {e.problem}"
        else:
            message = GENERIC_ERR_MSG.format(e)
        raise CumulusCIException(message)
    except Exception as e:
        if hasattr(f_config, "name"):
            message = f"An error occurred parsing {f_config.name}.\nError message: {e}"
        else:
            message = GENERIC_ERR_MSG.format(e)
        raise CumulusCIException(message)

    return rc
