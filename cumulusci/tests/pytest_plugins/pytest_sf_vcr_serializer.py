"""This module compresses VCR files on save using two techniques.

1.  It looks in a small database of "known" request/response pairs to
    reuse them. If it finds a hit, it creates an include_file reference.

2.  It looks in a small database of "known" string patterns (mostly) XML
    responses and replaces matching strings with references and variables.

3.  It looks for duplication within a single YAML file and uses YAML
    references to de-duplicate.
"""

import typing as T
from pathlib import Path

import yaml

from .vcr_string_compressor import StringToTemplateCompressor


class RequestResponseReplacement(T.NamedTuple):
    """For the database of 'known' request/response pairs"""

    request: dict
    response: dict
    replacement_file: str


class CompressionVCRSerializer:
    """A VCR serializer which compresses VCR files."""

    def __init__(self, path: T.Union[Path, str]):
        path = Path(path)
        self.saved_responses, self.include_files = _read_include_files(path)
        self.compressible_strings = StringToTemplateCompressor.from_directory(
            path / "vcr_string_templates"
        )
        assert self.compressible_strings.patterns

    def deserialize(self, cassette_string: str) -> dict:
        data = yaml.safe_load(cassette_string)
        walk_yaml(data, ExpandStringTemplates(self.compressible_strings))
        return _expand_external_references(data, self.include_files)

    def serialize(self, cassette_dict: dict) -> str:
        compressed_data = _compress_in_place(
            cassette_dict, self.saved_responses, self.compressible_strings
        )
        return yaml.dump(compressed_data, sort_keys=False)


def _read_include_files(path: Path) -> T.Tuple[dict, dict]:
    """Read canned responses from disk."""
    saved_responses = {}
    include_files = {}
    for file in tuple(path.glob("*.yaml")) + tuple(path.glob("*.yml")):
        request_response = yaml.safe_load(file.read_text())
        rrr = RequestResponseReplacement(
            request_response["request"], request_response["response"], file.name
        )
        saved_responses[repr(rrr.request)] = rrr
        include_files[rrr.replacement_file] = rrr
    return saved_responses, include_files


def _expand_external_references(d: dict, include_files: dict):
    """Expand external references on deserialization"""
    interactions = [
        _expand_reference(interaction, include_files)
        for interaction in d["interactions"]
    ]
    return {"interactions": interactions, "version": d["version"]}


def _expand_reference(possible_reference, include_files: dict):
    """Expand an external reference on deserialization"""
    if isinstance(possible_reference, dict) and "include_file" in possible_reference:
        filename = possible_reference["include_file"]
        replacement_rrr = include_files[filename]
        return {
            "request": replacement_rrr.request,
            "response": replacement_rrr.response,
        }
    else:
        return possible_reference


def _replace_interaction_if_possible(
    interaction: dict, replacements: T.Dict[str, RequestResponseReplacement]
) -> dict:
    """Try to replace an interaction with a canned one.

    Otherwise just return the interaction.
    """
    replacement = replacements.get(repr(interaction["request"]))
    if replacement:
        return {"include_file": replacement.replacement_file}
    return interaction


def _compress_in_place(d: dict, saved_responses: dict, sc: StringToTemplateCompressor):
    """First replace canned interactions. Then compress repetitive data."""
    d["interactions"] = [
        _replace_interaction_if_possible(interaction, saved_responses)
        for interaction in d["interactions"]
    ]
    walk_yaml(d, VCRCompressor(sc))
    return d


def walk_yaml(d: dict, mutator):
    """Visit each node in a dict/list tree datastructure"""
    if isinstance(d, (dict, list)):
        if isinstance(d, dict):
            items = d.items()
        else:
            items = enumerate(d)
        for key, value in items:
            walk_yaml(value, mutator)
            value = mutator(value)
            d[key] = value


class VCRCompressor:
    """Callable that replaces strings with templates and de-dupes structures"""

    def __init__(self, string_compressor):
        self.mappings = {}
        self.string_compressor = string_compressor

    def __call__(self, value):
        return self.compress(value)

    def compress(self, value):
        lookup = repr(value)
        if isinstance(value, str):
            value = self.string_compressor.string_to_template_if_possible(value)
            assert value is not None
        elif lookup in self.mappings:
            value = self.mappings[lookup]
        elif isinstance(value, (dict, list)):
            self.mappings[lookup] = value
        return value


class ExpandStringTemplates:
    """Callable that replaces templates with strings

    De-duping isn't necessary, because a DAG is as good as a tree for our purposes."""

    def __init__(self, string_compressor):
        self.string_compressor = string_compressor

    def __call__(self, value):
        return self.decompress(value)

    def decompress(self, value):
        if isinstance(value, dict) and "include_template" in value:
            value = self.string_compressor.template_to_string(value)
        return value
