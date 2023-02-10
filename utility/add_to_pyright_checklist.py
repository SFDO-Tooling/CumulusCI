import json
import subprocess
import sys
from pathlib import Path
from typing import List, Set

import tomli


def remove_bad_files(json_data: dict, filenames: Set[str]) -> None:
    for item in json_data["generalDiagnostics"]:
        file = item["file"]
        if file in filenames:  # filenames show up multiple times
            print(file, "has type errors. Ignoring them for now.", item["message"])
            filenames.remove(file)


def filter_out_bad_files(files: Set[str]) -> List[str]:
    files = set(str(Path(file).absolute()) for file in files)
    result = subprocess.run(
        ["pyright", "--outputjson", *sorted(files)],
        capture_output=True,
        text=True,
    )
    results = json.loads(result.stdout)
    remove_bad_files(results, files)
    return sorted(files)


def relativize_path(fn: str, root: Path):
    return str(Path(fn).relative_to(root.absolute()))


def main(staged_files: List[str]) -> bool:
    root = Path(__file__).parent.parent
    with (root / "pyproject.toml").open("rb") as f:
        pyproject_data = tomli.load(f)
        already_valid_files = pyproject_data["tool"]["pyright"]["include"]
        excludes = pyproject_data["tool"]["pyright"]["exclude"]
    staged_files = [
        fn
        for fn in staged_files
        if not any(Path(fn).match(pattern) for pattern in excludes)
    ]
    maybe_valid = set(staged_files).difference(set(already_valid_files))

    newly_valid_files = filter_out_bad_files(maybe_valid)
    if newly_valid_files:
        newly_valid_files = [relativize_path(file, root) for file in newly_valid_files]
        print(
            "Congratulations! These files can be added to pyproject.toml: [tool.pyright].include.\nPlease add them to continue.\n",
            newly_valid_files,
        )

        return False
    return True


if __name__ == "__main__":
    staged_files = sys.argv[1:]
    print(staged_files)
    success = main(staged_files)
    return_code = 0 if success else 1
    sys.exit(return_code)
