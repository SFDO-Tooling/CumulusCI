"""This module compresses VCR files on save using two techniques.

1.  It looks in a small database of "known" request/response pairs to
    reuse them. If it finds a hit, it creates an include_file reference.

2.  It looks for duplication within a single YAML file and uses YAML
    references to de-duplicate.
"""

import typing as T
from pathlib import Path

import yaml


class RequestResponseReplacement(T.NamedTuple):
    """For the database of 'known' request/response pairs"""

    request: dict
    response: dict
    replacement_file: str


class CompressionVCRSerializer:
    """A VCR serializer which compresses VCR files."""

    def __init__(self, path: Path):
        self.saved_responses, self.include_files = _read_include_files(path)

    def deserialize(self, cassette_string: str) -> dict:
        data = yaml.safe_load(cassette_string)
        return _expand_external_references(data, self.include_files)

    def serialize(self, cassette_dict: dict) -> str:
        return yaml.dump(
            _compress(cassette_dict, self.saved_responses), sort_keys=False
        )


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
    interaction: dict, replacements: dict[str:RequestResponseReplacement]
) -> dict:
    """Try to replace an interaction with a canned one.

    Otherwise just return the interaction.
    """
    replacement = replacements.get(repr(interaction["request"]))
    if replacement:
        return {"include_file": replacement.replacement_file}
    return interaction


def _compress(d: dict, saved_responses: dict):
    """First replace canned interactions. Then compress repetitive data."""
    d["interactions"] = [
        _replace_interaction_if_possible(interaction, saved_responses)
        for interaction in d["interactions"]
    ]
    _compress_recursive(d, {})
    return d


def _compress_recursive(d: dict, mappings: dict):
    """Compress repetitive data in a YAML structure"""
    if isinstance(d, (dict, list)):
        if isinstance(d, dict):
            items = d.items()
        else:
            items = enumerate(d)
        for key, value in items:
            lookup = repr(value)
            if lookup in mappings:
                value = mappings[lookup]
            else:
                _compress_recursive(value, mappings)
                mappings[lookup] = value
            d[key] = value
