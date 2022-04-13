"""
A Template like this:

template.tpl:

<?xml ...><foo xmls=...><id>{id}</id><status>{status:Closed}</status></foo>

can be referred to by name like this:

include_file: template.tpl
vars:
    id: 001A2431AF3

Note that the status can be elided because it defaults to Closed.
"""


import re
import typing as T
from pathlib import Path

MATCHER_REGEXP = re.compile("{(?P<name>[^:}]+)(:(?P<default>.*))?}")


class Pattern(T.NamedTuple):
    """Template pattern that can be referred to in to save space"""

    filename: str  # where to find the template
    orig_pattern: str  # the contents of the file
    regexp: re.Pattern  # contents converted to Python compatible regexp
    replacement_template: str  # contents converted to Python format-string
    default_values: T.Dict[str, str]  # defaulted values to save space further

    @staticmethod
    def parse(filename, pat) -> "Pattern":
        """Parse the contents of a pattern file into a Pattern obj"""
        replaceables = list(MATCHER_REGEXP.findall(pat))
        assert replaceables
        escaped_pat = pat.replace("?", r"\?")  # re.escape is too aggressive :(
        regexp = re.compile(MATCHER_REGEXP.sub(r"(?P<\1>.*)", escaped_pat))
        replacement_template = MATCHER_REGEXP.sub(r"{\1}", pat)
        default_values = {match[0]: match[-1] for match in replaceables if match[-1]}
        return Pattern(filename, pat, regexp, replacement_template, default_values)


class StringToTemplateCompressor:
    """Code that can translate from strings to templates and back"""

    @classmethod
    def from_directory(cls, path: T.Union[Path, str]):
        """Make a compressor from a directory of "tpl" files."""
        path = Path(path)
        raw_patterns = {f.name: f.read_text() for f in path.glob("*.tpl")}
        assert raw_patterns, f"Directory was empty {path}"
        return cls(raw_patterns)

    def __init__(self, raw_patterns: T.Dict[str, str]):
        self.patterns_by_filename = {
            filename: Pattern.parse(filename, pattern)
            for filename, pattern in raw_patterns.items()
        }
        self.patterns = self.patterns_by_filename.values()

    def string_to_template_if_possible(self, string: str):
        """Return a template dict if a template is matching.

        Else return the original string."""
        match = _find_match(self.patterns, string)
        if match:
            pattern, values = match
            return {"include_template": pattern.filename, "vars": values}
        else:
            return string

    def template_to_string(self, template: dict):
        """Reverse the templating process"""
        template_name = template["include_template"]
        template_vars = template["vars"]
        template = self.patterns_by_filename[template_name]
        return template.replacement_template.format(
            **{**template.default_values, **template_vars}
        )


def _expand(pattern, values):
    return pattern.replacement_template.format(**{**pattern.default_values, **values})


def _find_match(patterns, string):
    for pattern in patterns:
        match = pattern.regexp.match(string)
        if match:
            return pattern, {
                k: v
                for k, v in match.groupdict().items()
                if v != pattern.default_values.get(k)
            }
