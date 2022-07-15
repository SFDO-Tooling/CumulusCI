from typing import Dict

import pytest
from pydantic import ValidationError

from cumulusci.core.metadeploy.labels import METADEPLOY_LABELS
from cumulusci.core.metadeploy.models import (
    FrozenStep,
    MetaDeployPlan,
    PreflightCheck,
    PublisherOptions,
    SupportedOrgs,
)

pytestmark = pytest.mark.metadeploy


@pytest.mark.parametrize(
    "input,expected",
    zip(
        [
            ["user", "devhub"],
            ["user"],
            ["devhub"],
        ],
        list(SupportedOrgs),
    ),
)
def test_supported_orgs_validation_map(input, expected, simple_plan_dict):
    del simple_plan_dict["supported_orgs"]
    result = MetaDeployPlan(supported_orgs=input, **simple_plan_dict)
    assert expected == result.supported_orgs


def test_supported_orgs_validation_empty(simple_plan_dict):
    del simple_plan_dict["supported_orgs"]
    persistent = MetaDeployPlan(supported_orgs=None, **simple_plan_dict)
    assert persistent.supported_orgs == SupportedOrgs.PERSISTENT

    empty = MetaDeployPlan(supported_orgs=[], **simple_plan_dict)
    assert empty.supported_orgs == SupportedOrgs.PERSISTENT


def test_publisher_options_tag_validation():
    with pytest.raises(
        ValidationError, match="You must specify either the tag or commit option."
    ):
        PublisherOptions(plan="slug", dry_run=True, publish=True)


def test_publisher_options_no_publish_on_dry_run():
    opts: PublisherOptions = PublisherOptions(
        plan="slug", dry_run=True, publish=True, tag="v2.0"
    )
    assert not opts.publish


def test_product_get_labels(product_model):
    expected: Dict[str, dict] = {
        "short_description": {
            "description": METADEPLOY_LABELS["product"]["short_description"],
            "message": product_model.short_description,
        },
        "title": {
            "description": METADEPLOY_LABELS["product"]["title"],
            "message": product_model.title,
        },
        "description": {
            "description": METADEPLOY_LABELS["product"]["description"],
            "message": product_model.description,
        },
        "click_through_agreement": {
            "description": METADEPLOY_LABELS["product"]["click_through_agreement"],
            "message": product_model.click_through_agreement,
        },
        "error_message": {
            "description": METADEPLOY_LABELS["product"]["error_message"],
            "message": product_model.error_message,
        },
    }
    actual = product_model.get_labels()
    assert expected == actual


def test_preflight_get_labels():
    empty_check: PreflightCheck = PreflightCheck(
        when="when 'foo' in tasks.get_stuff()", action="skip"
    )
    assert not empty_check.get_labels()

    msg = "Scary warning message"
    check: PreflightCheck = PreflightCheck(
        when="when 'foo' in tasks.get_stuff()",
        action="warn",
        message=msg,
    )
    expected = {
        msg: {
            "message": msg,
            "description": METADEPLOY_LABELS["checks"]["message"],
        }
    }
    assert expected == check.get_labels()


def test_plan_labels(plan_model):
    plan_model.slug = "slug"
    print(plan_model)
    expected_dict = {
        "plan:slug": {
            "title": {
                "message": plan_model.title,
                "description": METADEPLOY_LABELS["plan"]["title"],
            },
            "post_install_message": {
                "message": plan_model.post_install_message,
                "description": "shown after successful installation (markdown)",
            },
            "preflight_message": {
                "message": plan_model.preflight_message,
                "description": "shown before user starts installation (markdown)",
            },
        },
    }
    labels = plan_model.get_labels()
    assert expected_dict == labels

    plan_model.preflight_checks = [
        PreflightCheck(
            when="when 'foo' in tasks.get_stuff()",
            action="warn",
            message="check_msg",
        )
    ]
    expected_dict["checks"] = {
        "check_msg": {
            "message": "check_msg",
            "description": METADEPLOY_LABELS["checks"]["message"],
        }
    }
    labels_with_checks = plan_model.get_labels()
    assert expected_dict == labels_with_checks


def test_update_step_labels():
    step: FrozenStep = FrozenStep.parse_obj(
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
                    {"when": "False", "action": "warn", "message": "check_msg"},
                    {"when": "False", "action": "error", "message": None},
                ],
            },
            "url": None,
        }
    )
    expected_dict = {
        "util_sleep": {
            "message": "util_sleep",
            "description": METADEPLOY_LABELS["steps"]["name"],
        }
    }
    labels = step.get_labels()
    assert expected_dict == labels


def test_update_step_labels_regex():
    step: FrozenStep = FrozenStep.parse_obj(
        {
            "is_recommended": True,
            "is_required": True,
            "kind": "managed",
            "message": None,
            "description": "Step description",
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
        }
    )
    expected_dict = {
        "Install {product} {version}": {
            "message": "Install {product} {version}",
            "description": METADEPLOY_LABELS["steps"]["name"],
        },
        "Step description": {
            "message": "Step description",
            "description": METADEPLOY_LABELS["steps"]["description"],
        },
    }
    labels = step.get_labels()
    assert expected_dict == labels
