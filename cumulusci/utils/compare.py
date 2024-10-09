import json
from typing import Any, Callable, Dict, List
from cumulusci.utils.version_strings import LooseVersion


def compare_nested_structures(
    base: Any, compare: Any, path: str = ""
) -> List[Dict[str, Any]]:
    """
    Recursively compare two potentially nested structures and return a list of granular differences.
    """
    diffs = []

    if isinstance(base, dict) and isinstance(compare, dict):
        all_keys = set(base.keys()) | set(compare.keys())
        key_serializer: Callable = str
        # # For keys that are a mix of strings and numbers, sort them by version number
        # if any(isinstance(key, str) for key in all_keys) and any(
        #     isinstance(key, (int, float)) for key in all_keys
        # ):
        #     key_serializer = lambda key: LooseVersion(str(key))
        for key in sorted(all_keys, key=key_serializer):
            current_path = f"{path}.{key}" if path else key
            if key not in base:
                diffs.append(
                    {
                        "path": current_path,
                        "type": "missing_in_base",
                        "compare_value": compare[key],
                    }
                )
            elif key not in compare:
                diffs.append(
                    {
                        "path": current_path,
                        "type": "missing_in_compare",
                        "base_value": base[key],
                    }
                )
            else:
                diffs.extend(
                    compare_nested_structures(base[key], compare[key], current_path)
                )
    elif isinstance(base, list) and isinstance(compare, list):
        for i in range(max(len(base), len(compare))):
            current_path = f"{path}[{i}]"
            if i < len(base) and i < len(compare):
                diffs.extend(
                    compare_nested_structures(base[i], compare[i], current_path)
                )
            elif i < len(base):
                diffs.append(
                    {
                        "path": current_path,
                        "type": "missing_in_compare",
                        "base_value": base[i],
                    }
                )
            else:
                diffs.append(
                    {
                        "path": current_path,
                        "type": "missing_in_base",
                        "compare_value": compare[i],
                    }
                )
    elif base != compare:
        diffs.append(
            {
                "path": path,
                "type": "value_difference",
                "base_value": base,
                "compare_value": compare,
            }
        )

    return diffs


def truncate_value(value: Any, max_length: int = 100) -> str:
    """
    Truncate a value if it's too long for display.
    """
    str_value = json.dumps(value, default=str)
    if len(str_value) > max_length:
        return str_value[:max_length] + "..."
    return str_value


# Example usage
if __name__ == "__main__":
    # Sample nested structures (you would replace these with your actual data)
    base_data = json.loads(
        """
    {
        "history": {
            "actions": [
                {
                    "sf_command": {
                        "command": "sf force:org:create --json  -f orgs/unmanaged.json -w 120 --targetdevhubusername MuseLabPBO -n --durationdays 7 -a Oh-Snap__dev adminEmail=jason@muselab.com",
                        "hash": "8af631b1",
                        "return_code": 0,
                        "output": "...",
                        "stderr": " ›   Warning: @salesforce/cli update available from 2.58.7 to 2.59.6.\n"
                    },
                    "timestamp": 1727695692.566693,
                    "repo": "git@github.com:muselab-d2x/oh-snap",
                    "branch": "main",
                    "commit": "f71197ea4481c72b1c12547db7fab6c8fd024040"
                }
            ]
        }
    }
    """
    )

    compare_data = json.loads(
        """
    {
        "history": {
            "actions": [
                {
                    "sf_command": {
                        "command": "sf force:org:create --json  -f orgs/unmanaged.json -w 120 --targetdevhubusername MuseLabPBO -n --durationdays 7 -a Oh-Snap__dev adminEmail=jason@muselab.com",
                        "hash": "8af631b1",
                        "return_code": 0,
                        "output": "...",
                        "stderr": " ›   Warning: @salesforce/cli update available from 2.58.7 to 2.59.7.\n"
                    },
                    "timestamp": 1727695692.566693,
                    "repo": "git@github.com:muselab-d2x/oh-snap",
                    "branch": "main",
                    "commit": "f71197ea4481c72b1c12547db7fab6c8fd024040"
                },
                {
                    "additional_action": "This is a new action in the compare data"
                }
            ]
        }
    }
    """
    )

    # Compare the structures
    diffs = compare_nested_structures(base_data, compare_data)

    # Print the differences
    for diff in diffs:
        print(f"Path: {diff['path']}")
        print(f"Type of difference: {diff['type']}")
        if diff["type"] == "value_difference":
            print(f"Base value: {diff['base_value']}")
            print(f"Compare value: {diff['compare_value']}")
        elif diff["type"] == "missing_in_base":
            print(f"Compare value: {diff['compare_value']}")
        elif diff["type"] == "missing_in_compare":
            print(f"Base value: {diff['base_value']}")
        print()
