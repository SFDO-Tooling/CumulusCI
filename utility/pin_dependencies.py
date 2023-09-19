import re
from pathlib import Path

import tomli
import tomli_w


def main(toml_filename: Path, requirements_txt: Path):
    with open(toml_filename, "rb") as f:
        data = tomli.load(f)

    with open(requirements_txt) as f:
        requirements = re.findall(r".*==.*", f.read())

    pin_dependencies(data, requirements)

    with open(toml_filename, "wb") as f:
        tomli_w.dump(data, f)


def pin_dependencies(data: dict, requirements: str):
    data["project"]["dependencies"] = requirements


root = Path(__file__).parent.parent
requirements = root / "requirements"
main(root / "pyproject.toml", requirements / "prod.txt")
print("Updated ", root / "pyproject.toml")
