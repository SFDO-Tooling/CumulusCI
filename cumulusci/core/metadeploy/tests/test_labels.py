import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import pytest

from cumulusci.core.metadeploy.labels import (
    METADEPLOY_DIR,
    METADEPLOY_LABELS,
    read_default_labels,
    read_label_files,
    save_default_labels,
    update_check_labels,
    update_plan_labels,
    update_product_labels,
    update_step_labels,
)

pytestmark = pytest.mark.metadeploy


def test_read_default_labels(tmp_path):
    label_path: Path = tmp_path / METADEPLOY_DIR
    label_path.mkdir(parents=True)
    label_file: Path = label_path / "labels_en.json"
    label_file.write_text(json.dumps(METADEPLOY_LABELS))

    result: dict = read_default_labels(labels_path=label_path)
    assert METADEPLOY_LABELS == result, "should match input"
    assert {} == result["missing_category"], "should be a default dict"


def test_read_default_labels_missing():
    result: dict = read_default_labels(labels_path="missing_dir")
    assert {} == result, "should be empty dict"
    assert {} == result["missing_category"], "should be a default dict"


def test_read_label_files(tmp_path):
    label_path: Path = tmp_path / METADEPLOY_DIR
    en_label_file: Path = label_path / "labels_en.json"
    fr_label_file: Path = label_path / "labels_fr.json"
    label_path.mkdir(parents=True)
    label = {"message": "message", "label": "label"}
    en_label_file.write_text(json.dumps(label))
    fr_label_file.write_text(json.dumps(label))

    expected_dict = {"fr": {"slug:message": "message", "slug:label": "label"}}

    result: dict = read_label_files(label_path, "slug")
    assert expected_dict == result


def test_save_labels(tmp_path):
    label_path: Path = tmp_path / METADEPLOY_DIR
    label_path.mkdir(parents=True)
    label_file: Path = label_path / "labels_en.json"
    expected = json.dumps(METADEPLOY_LABELS, indent=4)

    save_default_labels(label_path, METADEPLOY_LABELS)

    result = label_file.read_text()
    assert expected == result


def test_update_product_label():
    prod = {
        "title": "Foo",
        "short_description": "Integrated multi-platform functionality.",
    }
    labels_to_update = defaultdict(dict)
    expected_dict = deepcopy(labels_to_update)
    expected_dict["product"] = {
        "short_description": {
            "description": METADEPLOY_LABELS["product"]["short_description"],
            "message": "Integrated multi-platform functionality.",
        },
        "title": {
            "description": METADEPLOY_LABELS["product"]["title"],
            "message": "Foo",
        },
    }
    update_product_labels(prod, labels_to_update)
    assert expected_dict == labels_to_update


def test_update_plan_labels():
    plan = {
        "title": "Test Install",
        "error_message": "Your failure is complete.",
        "checks": [{"message": "check_msg"}, {"message": ""}],
    }
    labels_to_update = defaultdict(dict)
    expected_dict = deepcopy(labels_to_update)
    expected_dict.update(
        {
            "plan:slug": {
                "title": {
                    "message": "Test Install",
                    "description": METADEPLOY_LABELS["plan"]["title"],
                },
                "error_message": {
                    "message": "Your failure is complete.",
                    "description": METADEPLOY_LABELS["plan"]["error_message"],
                },
            },
            "checks": {
                "check_msg": {
                    "message": "check_msg",
                    "description": METADEPLOY_LABELS["checks"]["message"],
                }
            },
        }
    )
    update_plan_labels("slug", plan, labels_to_update)
    assert expected_dict == labels_to_update


def test_update_step_labels():
    steps = [
        {
            "name": "Install Test Product 1.0",
            "task_config": {
                "checks": [],
            },
        },
        {
            "name": "Update Admin Profile",
            "task_config": {
                "checks": [],
            },
        },
        {
            "name": "util_sleep",
            "task_config": {
                "checks": [
                    {"when": "False", "action": "error", "message": "Check failed 😭"}
                ]
            },
        },
    ]
    labels_to_update = defaultdict(dict)
    expected_dict = deepcopy(labels_to_update)
    expected_dict["steps"] = {
        "Install {product} {version}": {
            "message": "Install {product} {version}",
            "description": METADEPLOY_LABELS["steps"]["name"],
        },
        "Update Admin Profile": {
            "message": "Update Admin Profile",
            "description": METADEPLOY_LABELS["steps"]["name"],
        },
        "util_sleep": {
            "message": "util_sleep",
            "description": METADEPLOY_LABELS["steps"]["name"],
        },
    }
    expected_dict["checks"] = {
        "Check failed 😭": {
            "message": "Check failed 😭",
            "description": METADEPLOY_LABELS["checks"]["message"],
        }
    }
    update_step_labels(steps, labels_to_update)
    assert expected_dict == labels_to_update


def test_update_check_labels():
    plan_or_step = {"checks": [{"message": "check_msg"}, {"message": ""}]}
    labels_to_update = defaultdict(dict)
    labels_to_update["plan"] = {
        "title": "TITLE",
        "preflight_message": "PREFLIGHT_MESSAGE",
        "preflight_message_additional": "PREFLIGHT_MESSAGE_ADDITIONAL",
        "post_install_message": "POST_INSTALL_MESSAGE",
        "post_install_message_additional": "POST_INSTALL_MESSAGE_ADDITIONAL",
        "error_message": "ERROR_MESSAGE",
    }
    expected_dict = deepcopy(labels_to_update)
    expected_dict["checks"] = {
        "check_msg": {
            "message": "check_msg",
            "description": METADEPLOY_LABELS["checks"]["message"],
        }
    }
    update_check_labels(plan_or_step, labels_to_update)
    assert expected_dict == labels_to_update
