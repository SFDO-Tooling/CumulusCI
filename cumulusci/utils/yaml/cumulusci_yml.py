from typing import IO, Text
import re
from logging import getLogger
from io import StringIO

import yaml

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


def cci_safe_load(f_config: IO[Text]):
    "Load a file, convert NBSP->space and parse it in YAML."
    data = _replace_nbsp(f_config.read())
    rc = yaml.safe_load(StringIO(data))
    return rc
