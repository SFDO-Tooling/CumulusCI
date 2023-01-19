"""
Update the history file.
"""
from pathlib import Path

START_MARKER = "<!-- latest-start -->"
STOP_MARKER = "<!-- latest-stop -->"

history = Path("docs/history.md").read_text()
latest = Path("changelog.md").read_text()
updated = history.replace(f"{STOP_MARKER}\n\n", "").replace(
    f"{START_MARKER}\n\n", f"{START_MARKER}\n\n{latest}\n\n{STOP_MARKER}\n\n"
)

Path("docs/history.md").write_text(updated)
