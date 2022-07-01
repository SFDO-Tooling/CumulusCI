import pytest

from cumulusci.core.config import ServiceConfig
from cumulusci.core.metadeploy.plans import get_frozen_steps
from cumulusci.tests.util import create_project_config

pytestmark = pytest.mark.metadeploy


def test_freeze_steps():
    project_config = create_project_config()
    project_config.config["flows"] = {
        "customer_org": {
            "steps": {
                1: {
                    "task": "install_managed",
                    "options": {
                        "version": "1.0",
                        "namespace": "ns",
                        "name": "Test Product",
                    },
                },
            }
        }
    }
    plan_config = {
        "title": "Test Install",
        "slug": "install",
        "tier": "primary",
        "steps": {
            1: {"flow": "customer_org"},
            2: {
                "task": "util_sleep",
                "checks": [{"when": "False", "action": "error"}],
            },
        },
        "checks": [{"when": "False", "action": "error"}],
        "allowed_org_providers": ["user", "devhub"],
    }
    steps = get_frozen_steps(project_config, plan_config)
    assert [
        {
            "is_required": True,
            "kind": "managed",
            "name": "Install Test Product 1.0",
            "path": "customer_org.install_managed",
            "source": None,
            "step_num": "1/1",
            "task_class": "cumulusci.tasks.salesforce.InstallPackageVersion",
            "task_config": {
                "checks": [],
                "options": {
                    "version": "1.0",
                    "namespace": "ns",
                    "interactive": False,
                    "base_package_url_format": "{}",
                },
            },
        },
        {
            "is_required": True,
            "kind": "other",
            "name": "util_sleep",
            "path": "util_sleep",
            "step_num": "2",
            "source": None,
            "task_class": "cumulusci.tasks.util.Sleep",
            "task_config": {
                "options": {"seconds": 5},
                "checks": [{"when": "False", "action": "error"}],
            },
        },
    ] == steps


def test_freeze_steps__skip():
    project_config = create_project_config()
    project_config.keychain.set_service(
        "metadeploy",
        "test_alias",
        ServiceConfig({"url": "https://metadeploy", "token": "TOKEN"}),
    )
    project_config.keychain.set_service(
        "github",
        "test_alias",
        ServiceConfig({"username": "foo", "token": "bar", "email": "foo@example.com"}),
    )
    plan_config = {
        "title": "Test Install",
        "slug": "install",
        "tier": "primary",
        "steps": {1: {"task": "None"}},
    }
    steps = get_frozen_steps(project_config, plan_config)
    assert steps == []
