from unittest import mock

import pytest

from cumulusci.core.dependencies.dependencies import (
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
)
from cumulusci.core.dependencies.resolvers import get_resolver_stack
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
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
        PackageInstallOptions(),
        retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
    )


@mock.patch("cumulusci.core.dependencies.dependencies.install_package_by_version_id")
def test_install_2gp(install_package_by_version_id):
    task = create_task(
        InstallPackageVersion, {"version": "04t000000000000", "version_number": "1.0"}
    )
    task.org_config._installed_packages = {}

    task._run_task()
    install_package_by_version_id.assert_called_once_with(
        task.project_config,
        task.org_config,
        "04t000000000000",
        PackageInstallOptions(),
        retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
    )


@mock.patch(
    "cumulusci.core.dependencies.dependencies.install_package_by_namespace_version"
)
@mock.patch("cumulusci.tasks.salesforce.install_package_version.click.confirm")
def test_install_interactive(confirm, install_package_by_namespace_version):
    confirm.return_value = True

    task = create_task(
        InstallPackageVersion,
        {"namespace": "test", "version": "1.0", "interactive": True},
    )
    task.org_config._installed_packages = {}

    task._run_task()
    install_package_by_namespace_version.assert_called_once_with(
        task.project_config,
        task.org_config,
        "test",
        "1.0",
        PackageInstallOptions(),
        retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
    )


@mock.patch(
    "cumulusci.core.dependencies.dependencies.install_package_by_namespace_version"
)
@mock.patch("cumulusci.tasks.salesforce.install_package_version.click.confirm")
def test_install_interactive__decline(confirm, install_package_by_namespace_version):
    confirm.return_value = False

    task = create_task(
        InstallPackageVersion,
        {"namespace": "test", "version": "1.0", "interactive": True},
    )
    task.org_config._installed_packages = {}

    with pytest.raises(CumulusCIException) as e:
        task._run_task()

    assert "canceled" in str(e)
    install_package_by_namespace_version.assert_not_called()


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
        activate_remote_site_settings=True, password="foo"
    )
    assert task.options["activate_remote_site_settings"] is True
    assert "activateRSS" not in task.options


def test_init_options__float_version():
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"
    task = create_task(
        InstallPackageVersion,
        {
            "version": 1.0,
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

    assert task.options["version"] == "1.0"


@mock.patch(
    "cumulusci.tasks.salesforce.install_package_version.GitHubDynamicDependency"
)
def test_init_options__dynamic_version_latest(mock_GitHubDynamicDependency):
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"

    mock_GitHubDynamicDependency.return_value.package_dependency = (
        PackageNamespaceVersionDependency(namespace="ns", version="2.0")
    )

    task = create_task(
        InstallPackageVersion,
        {"version": "latest"},
        project_config=project_config,
    )
    assert task.options["version"] == "2.0"

    mock_GitHubDynamicDependency.assert_called_once_with(github=project_config.repo_url)
    mock_GitHubDynamicDependency.return_value.resolve.assert_called_once_with(
        project_config, get_resolver_stack(project_config, "production")
    )


@mock.patch(
    "cumulusci.tasks.salesforce.install_package_version.GitHubDynamicDependency"
)
def test_init_options__dynamic_version_latest__2gp(mock_GitHubDynamicDependency):
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"

    mock_GitHubDynamicDependency.return_value.package_dependency = (
        PackageVersionIdDependency(
            version_id="04t000000000000", package_name="Test", version_number="2.0"
        )
    )

    task = create_task(
        InstallPackageVersion,
        {"version": "latest"},
        project_config=project_config,
    )
    assert task.options["version"] == "04t000000000000"
    assert task.options["version_number"] == "2.0"

    mock_GitHubDynamicDependency.assert_called_once_with(github=project_config.repo_url)
    mock_GitHubDynamicDependency.return_value.resolve.assert_called_once_with(
        project_config, get_resolver_stack(project_config, "production")
    )


@mock.patch(
    "cumulusci.tasks.salesforce.install_package_version.GitHubDynamicDependency"
)
def test_init_options__dynamic_version_latest_beta(mock_GitHubDynamicDependency):
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"

    mock_GitHubDynamicDependency.return_value.package_dependency = (
        PackageNamespaceVersionDependency(namespace="ns", version="2.0 Beta 1")
    )

    task = create_task(
        InstallPackageVersion,
        {"version": "latest_beta"},
        project_config=project_config,
    )
    assert task.options["version"] == "2.0 Beta 1"

    mock_GitHubDynamicDependency.assert_called_once_with(github=project_config.repo_url)
    mock_GitHubDynamicDependency.return_value.resolve.assert_called_once_with(
        project_config, get_resolver_stack(project_config, "include_beta")
    )


@mock.patch(
    "cumulusci.tasks.salesforce.install_package_version.GitHubDynamicDependency"
)
@mock.patch("cumulusci.tasks.salesforce.install_package_version.find_previous_release")
def test_init_options__dynamic_version_previous(
    mock_find_previous_release, mock_GitHubDynamicDependency
):
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"

    mock_find_previous_release.return_value.tag_name = "release/1.0"
    mock_GitHubDynamicDependency.return_value.package_dependency = (
        PackageNamespaceVersionDependency(namespace="ns", version="1.0")
    )
    project_config.get_repo = mock.Mock()

    task = create_task(
        InstallPackageVersion,
        {"version": "previous"},
        project_config=project_config,
    )
    assert task.options["version"] == "1.0"

    mock_find_previous_release(
        project_config.get_repo.return_value,
        project_config.project__git__prefix_release,
    )
    mock_GitHubDynamicDependency.assert_called_once_with(
        github=project_config.repo_url, tag="release/1.0"
    )
    mock_GitHubDynamicDependency.return_value.resolve.assert_called_once_with(
        project_config, get_resolver_stack(project_config, "production")
    )


@mock.patch(
    "cumulusci.tasks.salesforce.install_package_version.GitHubDynamicDependency"
)
def test_init_options__dynamic_version_no_managed_release(mock_GitHubDynamicDependency):
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"

    mock_GitHubDynamicDependency.return_value.package_dependency = None

    with pytest.raises(CumulusCIException, match="does not identify"):
        create_task(
            InstallPackageVersion,
            {"version": "latest_beta"},
            project_config=project_config,
        )


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
                    "interactive": False,
                    "base_package_url_format": "{}",
                },
                "checks": [],
            },
        },
    ]


def test_freeze__2gp():
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"
    project_config.config["project"]["package"]["name"] = "Test"
    task = create_task(
        InstallPackageVersion,
        {
            "version": "04t000000000000",
            "version_number": "1.0",
        },
        project_config=project_config,
    )
    step = StepSpec(1, "test_task", task.task_config.config, None, task.project_config)
    steps = task.freeze(step)

    # Note: because we directly specified the 04t rather than resolving a version,
    # we don't persist the package name ("Package" below).
    # This is as designed.
    assert steps == [
        {
            "is_required": True,
            "kind": "managed",
            "name": "Install Package 1.0",
            "path": "test_task",
            "step_num": "1",
            "source": None,
            "task_class": None,
            "task_config": {
                "options": {
                    "version": "04t000000000000",
                    "version_number": "1.0",
                    "namespace": "ns",
                    "interactive": False,
                    "base_package_url_format": "{}",
                },
                "checks": [],
            },
        },
    ]


def test_tooling_with_push():
    project_config = create_project_config()
    project_config.config["project"]["package"]["namespace"] = "ns"
    project_config.config["project"]["package"]["name"] = "Test"

    with pytest.raises(TaskOptionsError):
        create_task(
            InstallPackageVersion,
            {"version": "04t000000000000", "security_type": "PUSH"},
            project_config=project_config,
        )
