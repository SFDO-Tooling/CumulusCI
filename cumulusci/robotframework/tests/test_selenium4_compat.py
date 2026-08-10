import re
from pathlib import Path

import cumulusci

CCI_ROOT = Path(cumulusci.__file__).parent

DEPRECATED_FINDER_RE = re.compile(r"find_elements?_by_")

FILES_TO_CHECK = [
    CCI_ROOT / "robotframework" / "Salesforce.py",
    CCI_ROOT / "robotframework" / "pageobjects" / "BasePageObjects.py",
    CCI_ROOT / "robotframework" / "form_handlers.py",
    CCI_ROOT / "robotframework" / "tests" / "salesforce" / "forms.robot",
]


def test_no_deprecated_selenium_finder_methods():
    """Selenium 4.3 removed find_element_by_* / find_elements_by_*.

    They must use the generic find_element(By.X, value) form, which works on
    both Selenium 3 and 4.
    """
    offenders = []
    for path in FILES_TO_CHECK:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if DEPRECATED_FINDER_RE.search(line):
                offenders.append(f"{path}:{lineno}: {line.strip()}")
    assert not offenders, "Deprecated Selenium finder methods remain:\n" + "\n".join(
        offenders
    )
