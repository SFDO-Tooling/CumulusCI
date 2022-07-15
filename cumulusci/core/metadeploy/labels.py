"""
Functions for creating/modifying MetaDeploy translation labels.
"""
import contextlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Mapping, Union

LabelMap = Mapping[str, Mapping[str, str]]

INSTALL_VERSION_RE = re.compile(r"^Install .*\d$")
METADEPLOY_DIR: str = "metadeploy"
METADEPLOY_LABELS: LabelMap = {
    "checks": {"message": "shown if validation fails"},
    "plan": {
        "title": "title of installation plan",
        "preflight_message": "shown before user starts installation (markdown)",
        "preflight_message_additional": "shown before user starts installation (markdown)",
        "post_install_message": "shown after successful installation (markdown)",
        "post_install_message_additional": "shown after successful installation (markdown)",
        "error_message": "shown after failed installation (markdown)",
    },
    "product": {
        "title": "name of product",
        "short_description": "tagline of product",
        "description": "shown on product detail page (markdown)",
        "click_through_agreement": "legal text shown in modal dialog",
        "error_message": "shown after failed installation (markdown)",
    },
    "steps": {
        "name": "title of installation step",
        "description": "description of installation step",
    },
}


def read_default_labels(labels_path: Union[Path, str] = METADEPLOY_DIR) -> dict:
    """Load existing English labels from disk."""
    labels: dict = defaultdict(dict)
    with contextlib.suppress(FileNotFoundError):
        labels_file: Path = Path(labels_path, "labels_en.json")
        labels.update(json.loads(labels_file.read_text()))
    return labels


def read_label_files(labels_path: Union[Path, str], slug: str) -> Dict[str, dict]:
    """
    Load all tranlations from disk, returning prefixed labels keyed by language.

    Keyword Arguments:
    labels_path -- Path containing files to read
    slug        -- Prepended to each label's key
    """
    prefixed_labels = {}
    for path in Path(labels_path).glob("*.json"):
        lang = path.stem.split("_")[-1].lower()
        if lang in ("en", "en-us"):
            continue
        orig_labels = json.loads(path.read_text())
        prefixed_labels[lang] = {
            f"{slug}:{context}": labels for context, labels in orig_labels.items()
        }
    return prefixed_labels


def save_default_labels(labels_path: Union[Path, str], labels_to_save: dict):
    """Save updates to English labels."""
    with contextlib.suppress(FileNotFoundError):
        labels_file: Path = Path(labels_path, "labels_en.json")
        labels_file.write_text(f"{json.dumps(labels_to_save, indent=4)}\n")


def update_step_labels(steps, labels_to_update):
    """Mutates labels_to_update
    Keyword Arguments:
    """
    for step in steps:
        labels_to_update["steps"].update(step.get_labels())
        labels_to_update["checks"].update(step.task_config.get_labels())
