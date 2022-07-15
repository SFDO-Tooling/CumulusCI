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
    update_step_labels,
)
from cumulusci.core.metadeploy.models import FrozenStep

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
    assert expected == result.strip()  # delete trailing newline


def test_update_step_labels():
    steps = [
        FrozenStep.parse_obj(
            {
                "is_recommended": True,
                "is_required": True,
                "kind": "managed",
                "message": None,
                "description": None,
                "name": "Install Test Product 1.0",
                "path": "install_prod.install_managed",
                "source": None,
                "step_num": "1/2",
                "task_class": "cumulusci.tasks.salesforce.InstallPackageVersion",
                "task_config": {
                    "options": {
                        "version": "1.0",
                        "namespace": "ns",
                        "interactive": False,
                        "base_package_url_format": "{}",
                    },
                    "checks": [],
                },
                "url": None,
            }
        ),
        FrozenStep.parse_obj(
            {
                "is_recommended": True,
                "is_required": True,
                "kind": "other",
                "message": None,
                "name": "util_sleep",
                "path": "util_sleep",
                "step_num": "2",
                "source": None,
                "task_class": "cumulusci.tasks.util.Sleep",
                "task_config": {
                    "options": {"seconds": 5},
                    "checks": [
                        {
                            "when": "False",
                            "action": "error",
                            "message": "Check failed 😭",
                        },
                        {"when": "False", "action": "error", "message": None},
                    ],
                },
                "url": None,
            }
        ),
    ]
    labels_to_update = defaultdict(dict)
    expected_dict = deepcopy(labels_to_update)
    expected_dict["steps"] = {
        "Install {product} {version}": {
            "message": "Install {product} {version}",
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
