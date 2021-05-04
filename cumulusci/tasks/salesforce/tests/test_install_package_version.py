from cumulusci.core.config import OrgConfig
from unittest import mock

import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.flowrunner import StepSpec
from cumulusci.salesforce_api.package_install import (
    DEFAULT_PACKAGE_RETRY_OPTIONS,
    PackageInstallOptions,
)
from cumulusci.tasks.salesforce.install_package_version import InstallPackageVersion
from cumulusci.tests.util import create_project_config

from .util import create_task


@mock.patch(
    "cumulusci.core.dependencies.dependencies.install_package_by_namespace_version"
)
def test_install_1gp(install_package_by_namespace_version):

    task = create_task(InstallPackageVersion, {"namespace": "test", "version": "1.0"})
    task.org_config._installed_packages = {}

    task._run_task()
    install_package_by_namespace_version.assert_called_once_with(
        task.project_config,
        task.org_config,
        "test",
        "1.0",
        PackageInstallOptions(activate_remote_site_settings=False),
        retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
    )


@mock.patch("cumulusci.core.dependencies.dependencies.install_package_by_version_id")
def test_install_2gp(install_package_by_version_id):
    task = create_task(InstallPackageVersion, {"version": "04t000000000000"})
    task.org_config._installed_packages = {}

    task._run_task()
    install_package_by_version_id.assert_called_once_with(
        task.project_config,
        task.org_config,
        "04t000000000000",
        PackageInstallOptions(activate_remote_site_settings=False),
        retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
    )


def test_init_options():
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"
    task = create_task(
        InstallPackageVersion,
        {
            "version": "04t000000000000",
            "retries": 20,
            "retry_interval": 50,
            "retry_interval_add": 100,
            "password": "foo",
            "activateRSS": True,
            "name": "bar",
            "security_type": "PUSH",
        },
        project_config=project_config,
    )

    assert task.options["namespace"] == "ns"
    assert task.retry_options == {
        "retries": 20,
        "retry_interval": 50,
        "retry_interval_add": 100,
    }
    assert task.install_options == PackageInstallOptions(
        activate_remote_site_settings=True, password="foo", security_type="PUSH"
    )


def test_init_options__dynamic_versions():
    project_config = create_project_config()
    project_config.get_latest_version = mock.Mock(side_effect=["2.0", "2.0 Beta 1"])
    project_config.get_previous_version = mock.Mock(return_value="1.0")
    project_config.config["project"]["package"]["namespace"] = "ns"

    task = create_task(
        InstallPackageVersion,
        {"version": "latest"},
        project_config=project_config,
    )
    assert task.options["version"] == "2.0"

    task = create_task(
        InstallPackageVersion,
        {"version": "latest_beta"},
        project_config=project_config,
    )
    assert task.options["version"] == "2.0 Beta 1"

    task = create_task(
        InstallPackageVersion,
        {"version": "previous"},
        project_config=project_config,
    )
    assert task.options["version"] == "1.0"


def test_init_options__name_inference():
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"
    project_config.config["project"]["package"]["name"] = "Test"

    task = create_task(
        InstallPackageVersion,
        {"version": "04t000000000000"},
        project_config=project_config,
    )

    assert task.options["name"] == "Package"

    task = create_task(
        InstallPackageVersion,
        {"version": "1.0"},
        project_config=project_config,
    )

    assert task.options["name"] == "Test"

    task = create_task(
        InstallPackageVersion,
        {"version": "1.0", "namespace": "foo"},  # Not this project's NS
        project_config=project_config,
    )
    assert task.options["name"] == "foo"


def test_run_task__bad_security_type():
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"
    with pytest.raises(TaskOptionsError):
        create_task(
            InstallPackageVersion,
            {"version": "1.0", "security_type": "BOGUS"},
            project_config,
        )


def test_freeze():
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"
    project_config.config["project"]["package"]["name"] = "Test"
    task = create_task(
        InstallPackageVersion,
        {
            "version": "1.0",
        },
        project_config=project_config,
    )
    step = StepSpec(1, "test_task", task.task_config.config, None, task.project_config)
    steps = task.freeze(step)

    assert steps == [
        {
            "is_required": True,
            "kind": "managed",
            "name": "Install Test 1.0",
            "path": "test_task",
            "step_num": "1",
            "source": None,
            "task_class": None,
            "task_config": {
                "options": {
                    "version": "1.0",
                    "namespace": "ns",
                    "security_type": "FULL",
                },
                "checks": [],
            },
        },
    ]
