import json
import os
import pickle
from io import StringIO
from logging import Logger
from typing import Any, Dict, List, Optional
from rich import box
from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.text import Text
from cumulusci.utils.compare import compare_nested_structures
from cumulusci.utils.serialization import encode_value, decode_dict, json_dumps
from cumulusci.utils.yaml.render import dump_yaml

# Delay saving as JSON for a few CumulusCI releases because
# people might downgrade a release and then their
# CCI can't parse their JSON orgfiles
#
# Thus we roll out the ability to parse JSON configs a bit
# ahead of the write behaviour.
SHOULD_SAVE_AS_JSON = os.environ.get("SHOULD_SAVE_AS_JSON", "False") != "False"


def load_config_from_json_or_pickle(b: bytes) -> dict:
    """Input should be plaintext JSON or Pickle"""
    assert isinstance(b, bytes)

    try:
        data = try_load_config_from_json_or_pickle(b)
    except pickle.PickleError as e:
        # we use ValueError because Pickle and Crypto both do too
        raise ValueError(str(e)) from e

    return data


def try_load_config_from_json_or_pickle(data: bytes) -> dict:
    """Load JSON or Pickle into a dict"""
    try:
        config = json.loads(data.decode("utf-8"), object_hook=decode_dict)
        # remove this debugging tool after transition
        config["serialization_format"] = "json"
        return config
    except ValueError as e1:
        try:
            # first byte in a Pickle must be part of
            # OPCODE Proto == \x80 == 128
            # https://github.com/python/cpython/blob/1b293b60067f6f4a95984d064ce0f6b6d34c1216/Lib/pickletools.py#L2124
            if data[0] != 128:
                raise ValueError("Decryption error")
            config = pickle.loads(data, encoding="bytes")
            # remove this debugging tool after transition
            config["serialization_format"] = "pickle"
            return config
        except pickle.UnpicklingError as e2:
            raise ValueError(f"{e1}\n{e2}")


def report_error(msg: str, e: Exception, logger: Logger):
    logger.error(
        "\n".join(
            (
                msg,
                str(e),
                "Please report it to the CumulusCI team.",
                "For now this is just a warning. By January 2023 it may become a real error.",
                "When you report it to the CumulusCI team, they will investigate",
                "whether the error is in your config or in CumulusCI",
            )
        )
    )


def report_diffs(diffs: List[Dict[str, Any]]) -> str:
    """
    Create a rich Table to display the differences.

    Args:
    differences (List[Dict[str, Any]]): List of differences from compare_nested_structures

    Returns:
    Table: A rich Table object containing the formatted differences
    """
    # table = Table(title="Differences", show_lines=True)
    # table.add_column("Path", style="cyan", no_wrap=True)
    # table.add_column("Type", style="magenta")
    # table.add_column("Base Value", style="green")
    # table.add_column("Compare Value", style="yellow")

    console = Console(width=200, file=StringIO())
    report = Text("OrgConfig JSON Roundtrip Differences", style="bold underline")

    for diff in diffs:
        path = diff["path"]
        diff_type = diff["type"]
        base_value = diff.get("base_value")
        compare_value = diff.get("compare_value")
        base_type = f" [{type(base_value).__name__}]" if base_value is not None else ""
        compare_type = (
            f" [{type(compare_value).__name__}]" if compare_value is not None else ""
        )
        console.print(Text(f"{diff_type}: {path}", style="bold"))
        base_value = (
            dump_yaml(base_value, indent=4) if base_value is not None else "N/A"
        )
        compare_value = (
            dump_yaml(compare_value, indent=4) if compare_value is not None else "N/A"
        )
        base_line = f"Base Value{base_type}: {base_value}"
        compare_line = f"Compare Value{compare_type}: {compare_value}"

        pad = (0, 0, 0, 2)
        if diff_type == "value_difference":
            console.print(
                Padding(Text(base_line, style="green"), pad=pad),
            )
            console.print(
                Padding(Text(compare_line, style="yellow"), pad=pad),
            )
        elif diff_type == "missing_in_base":
            console.print(
                Padding(Text(base_line, style="red"), pad=pad),
            )
            console.print(
                Padding(Text(compare_line, style="yellow"), pad=pad),
            )
        elif diff_type == "missing_in_compare":
            console.print(
                Padding(Text(base_line, style="green"), pad=pad),
            )
            console.print(
                Padding(Text(compare_line, style="red"), pad=pad),
            )
        console.print()

    # console.print(table)
    return console.file.getvalue()


def check_round_trip(data: dict, logger: Logger) -> Optional[bytes]:
    """Return JSON bytes if possible, else None"""
    try:
        as_json_text = json_dumps(data).encode("utf-8")
    except Exception as e:
        raise e from e
        import pdb

        pdb.set_trace()
        report_error("CumulusCI found an unusual datatype in your config:", e, logger)
        return None
    diffs = []
    try:
        test_load = load_config_from_json_or_pickle(as_json_text)
        base_data = _simplify_config(data)
        compare_data = _simplify_config(test_load)
        diffs = compare_nested_structures(base_data, compare_data)
        assert diffs == [], f"JSON did not round-trip cleanly\n"
    except Exception as e:  # pragma: no cover
        if diffs:
            report = report_diffs(diffs)
            logger.warning(
                f"JSON did not round-trip cleanly:\n {report}\n\n Please report this warning to the CumulusCI team for investigation."
            )
        else:
            report_error("CumulusCI found a problem saving your config:", e, logger)
        return None
    assert isinstance(as_json_text, bytes)
    return as_json_text


def _simplify_config(config: dict):
    return {k: v for k, v in config.items() if k != "serialization_format"}


def serialize_config_to_json_or_pickle(config: dict, logger: Logger) -> bytes:
    """Serialize a dict to JSON if possible or Pickle otherwise"""
    as_json_text = check_round_trip(config, logger)
    if as_json_text and SHOULD_SAVE_AS_JSON:
        assert isinstance(as_json_text, bytes)
        return as_json_text
    else:
        return pickle.dumps(config, protocol=2)
