from typing import IO, Text
from re import compile, MULTILINE
from logging import getLogger
from io import StringIO

import yaml

NBSP = "\u00A0"

pattern = compile(r"^\s*[\u00A0]+\s*", MULTILINE)

logger = getLogger("CumulusCI.yml")


def _replacer_func(matchobj):
    string = matchobj.group(0)
    rc = string.replace(NBSP, " ")
    if rc != string:  # this is fast for identical strings
        logger.warn(
            "Note: Non-breaking space character was detected in Cumulusci.yml.\n"
            "Perhaps you cut and pasted it from a Web page.\n"
            "Future versions of CumulusCI may disallow these characters.\n"
        )
    return rc


def _replace_nbsp(data):
    return pattern.sub(_replacer_func, data)


def cci_safe_load(f_config: IO[Text]):
    data = _replace_nbsp(f_config.read())
    rc = yaml.safe_load(StringIO(data))
    return rc
