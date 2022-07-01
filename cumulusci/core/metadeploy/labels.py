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


def update_plan_labels(plan_name: str, plan, labels_to_update):
    """Add specified fields from plan to a label category."""
    labels_to_update[f"plan:{plan_name}"].update(
        {
            name: {"message": plan[name], "description": description}
            for name, description in METADEPLOY_LABELS["plan"].items()
            if name in plan
        }
    )
    update_check_labels(plan, labels_to_update)


def update_product_labels(product, labels_to_update):
    """
    Mutates labels_to_update to add specified fields from obj to a label category.
    """
    if updates := {
        name: {"message": product[name], "description": description}
        for name, description in METADEPLOY_LABELS["product"].items()
        if name in product
    }:
        labels_to_update["product"].update(updates)


def update_step_labels(steps, labels_to_update):
    """Mutates labels_to_update
    Keyword Arguments:
    """
    for step in steps:
        # avoid separate labels for installing each package
        name = (
            "Install {product} {version}"
            if INSTALL_VERSION_RE.match(step["name"])
            else step["name"]
        )
        labels_to_update["steps"][name] = {
            "message": name,
            "description": METADEPLOY_LABELS["steps"]["name"],
        }
        if step.get("description"):
            description = step.get("description")
            labels_to_update["steps"][description] = {
                "message": description,
                "description": METADEPLOY_LABELS["steps"]["descripton"],
            }
        update_check_labels(step["task_config"], labels_to_update)


def update_check_labels(plan_or_step, labels_to_update):
    checks = plan_or_step.get("checks", [])
    updates = [
        {
            "message": check.get("message"),
            "description": METADEPLOY_LABELS["checks"]["message"],
        }
        for check in checks
        if check.get("message")
    ]
    for label in updates:
        msg = label["message"]
        labels_to_update["checks"][msg] = label
