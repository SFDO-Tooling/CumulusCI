from cumulusci.core.dependencies.dependencies import (
    GitHubDynamicDependency,
    ManagedPackageDependency,
    UnmanagedDependency,
    get_resolver_stack,
    DependencyResolutionStrategy,
)
import io
import logging
from unittest import mock
import zipfile
import pytest
import pydantic
from cumulusci.core.exceptions import TaskOptionsError, DependencyParseError
from cumulusci.core.flowrunner import StepSpec
from cumulusci.tasks.salesforce.update_dependencies import UpdateDependencies
from cumulusci.tests.util import create_project_config
from .util import create_task


def make_fake_zipfile(*args, **kw):
    return zipfile.ZipFile(io.BytesIO(), "w")


def test_init_options_base():
    project_config = create_project_config()

    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "namespace": "ns",
                    "version": "1.0",
                },
                {"version_id": "04t000000000000"},
                {"github": "https://github.com/Test/TestRepo"},
            ],
            "resolution_strategy": "production",
        },
        project_config=project_config,
    )

    assert task.dependencies == [
        ManagedPackageDependency(namespace="ns", version="1.0"),
        ManagedPackageDependency(version_id="04t000000000000"),
        GitHubDynamicDependency(github="https://github.com/Test/TestRepo"),
    ]
    assert task.resolution_strategy == get_resolver_stack(project_config, "production")


def test_init_options_error_bad_dependencies():
    with pytest.raises(DependencyParseError):
        create_task(
            UpdateDependencies,
            {
                "dependencies": [
                    {
                        "namespace": "ns",
                        "version_id": "04t000000000000",
                    }
                ]
            },
        )


def test_init_options_warns_deprecated_options(caplog):
    with caplog.at_level(logging.INFO):
        create_task(
            UpdateDependencies,
            {
                "dependencies": [
                    {
                        "namespace": "ns",
                        "version": "1.0",
                    }
                ],
                "allow_uninstalls": False,
                "include_beta": True,
            },
        )

        assert "no longer supported" in caplog.text
        assert "Use resolution strategies instead" in caplog.text


def test_init_options_error_bad_ignore_dependencies():
    with pytest.raises(TaskOptionsError):
        create_task(
            UpdateDependencies,
            {
                "dependencies": [
                    {
                        "namespace": "ns",
                        "version": "1.0",
                    }
                ],
                "ignore_dependencies": [{"foo": "bar"}],
            },
        )


def test_init_options_removes_beta_resolver_for_include_beta_false():
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "namespace": "ns",
                    "version": "1.0",
                }
            ],
            "resolution_strategy": "include_beta",
            "include_beta": False,
        },
    )

    assert (
        DependencyResolutionStrategy.STRATEGY_BETA_RELEASE_TAG
        not in task.resolution_strategy
    )


def test_init_options_removes_2gp_resolver_for_prefer_2gp_false():
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "namespace": "ns",
                    "version": "1.0",
                }
            ],
            "resolution_strategy": "include_beta",
            "prefer_2gp_from_release_branch": False,
        },
    )

    assert (
        DependencyResolutionStrategy.STRATEGY_2GP_RELEASE_BRANCH
        not in task.resolution_strategy
    )


def test_init_options_removes_unsafe_resolvers_persistent_org():
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "namespace": "ns",
                    "version": "1.0",
                }
            ],
            "resolution_strategy": "include_beta",
        },
    )
    task.org_config = mock.Mock()
    task.org_config.scratch = False

    assert (
        DependencyResolutionStrategy.STRATEGY_BETA_RELEASE_TAG
        not in task.resolution_strategy
    )
    assert (
        DependencyResolutionStrategy.STRATEGY_2GP_RELEASE_BRANCH
        not in task.resolution_strategy
    )


def test_run_task_gets_static_dependencies_and_installs():
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "namespace": "ns",
                    "version": "1.0",
                },
                {"version_id": "04t000000000000"},
            ],
            "resolution_strategy": "production",
            "ignore_dependencies": [{"github": "https://github.com/Test/TestRepo"}],
            "security_type": "PUSH",
        },
    )

    task._install_dependency = mock.Mock()
    task()

    task._install_dependency.assert_has_calls(
        [
            mock.call(ManagedPackageDependency(namespace="ns", version="1.0")),
            mock.call(ManagedPackageDependency(version_id="04t000000000000")),
        ]
    )


def test_run_task_exits_no_dependencies():
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [],
            "resolution_strategy": "production",
            "ignore_dependencies": [{"github": "https://github.com/Test/TestRepo"}],
            "security_type": "PUSH",
        },
    )

    task._install_dependency = mock.Mock()
    task()

    task._install_dependency.assert_not_called()


@mock.patch("cumulusci.core.dependencies.dependencies.install_1gp_package_version")
def test_install_dependency_installs_managed_package(install_1gp_package_version):
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "namespace": "ns",
                    "version": "1.0",
                }
            ]
        },
    )
    task.org_config = mock.Mock()
    task.org_config.installed_packages = {}
    task.org_config.has_minimum_package_version.return_value = False

    task._install_dependency(task.dependencies[0])
    install_1gp_package_version.assert_called_once_with(
        task.project_config,
        task.org_config,
        "ns",
        "1.0",
        mock.ANY,
        retry_options=mock.ANY,  # Ignore the options
    )


@mock.patch("cumulusci.core.dependencies.dependencies.install_1gp_package_version")
def test_install_dependency_no_op_already_installed(install_1gp_package_version):
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "namespace": "ns",
                    "version": "1.0",
                }
            ]
        },
    )
    task.org_config = mock.Mock()
    task.org_config.installed_packages = {"ns": "1.0"}
    task.org_config.has_minimum_package_version.return_value = True

    task._install_dependency(task.dependencies[0])
    install_1gp_package_version.assert_not_called()


@mock.patch("cumulusci.core.dependencies.dependencies.install_1gp_package_version")
def test_install_dependency_already_installed__newer_beta(install_1gp_package_version):
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "namespace": "ns",
                    "version": "1.0 Beta 4",
                }
            ]
        },
    )
    task.org_config = mock.Mock()
    task.org_config.installed_packages = {"ns": "1.0"}
    task.org_config.has_minimum_package_version.return_value = False

    task._install_dependency(task.dependencies[0])
    task.org_config.has_minimum_package_version.assert_called_once_with("ns", "1.0b4")
    install_1gp_package_version.assert_called_once_with(
        task.project_config,
        task.org_config,
        "ns",
        "1.0 Beta 4",
        mock.ANY,
        retry_options=mock.ANY,  # Ignore the options
    )


def test_install_dependency_installs_unmanaged():
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "zip_url": "http://example.com/foo",
                }
            ]
        },
    )
    task.dependencies[0].__config__.extra = pydantic.Extra.allow
    task.dependencies[0].install = mock.Mock()
    task.org_config = mock.Mock()

    task._install_dependency(task.dependencies[0])
    task.dependencies[0].install.assert_called_once_with(
        task.project_config, task.org_config
    )


def test_run_task__bad_security_type():
    with pytest.raises(TaskOptionsError):
        create_task(
            UpdateDependencies,
            {
                "security_type": "BOGUS",
                "dependencies": [
                    {
                        "namespace": "ns",
                        "version": "1.0",
                    },
                ],
            },
        )


@mock.patch("cumulusci.tasks.salesforce.update_dependencies.get_static_dependencies")
def test_freeze(get_static_dependencies):
    get_static_dependencies.return_value = [
        ManagedPackageDependency(namespace="ns", version="1.0"),
        UnmanagedDependency(
            github="https://github.com/SFDO-Tooling/CumulusCI-Test",
            ref="abcdef",
            subfolder="src",
        ),
    ]
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "namespace": "ns",
                    "version": "1.0",
                },
                {
                    "github": "https://github.com/SFDO-Tooling/CumulusCI-Test",
                    "ref": "abcdef",
                    "subfolder": "src",
                },
            ]
        },
    )
    step = StepSpec(1, "test_task", task.task_config, None, task.project_config)
    steps = task.freeze(step)

    assert [
        {
            "is_required": True,
            "kind": "managed",
            "name": "Install ns 1.0",
            "path": "test_task.1",
            "step_num": "1.1",
            "source": None,
            "task_class": None,
            "task_config": {
                "options": {
                    "dependencies": [{"namespace": "ns", "version": "1.0"}],
                    "security_type": "FULL",
                },
                "checks": [],
            },
        },
        {
            "is_required": True,
            "kind": "metadata",
            "name": "Deploy CumulusCI-Test/src",
            "path": "test_task.2",
            "step_num": "1.2",
            "source": None,
            "task_class": None,
            "task_config": {
                "options": {
                    "dependencies": [
                        {
                            "ref": "abcdef",
                            "github": "https://github.com/SFDO-Tooling/CumulusCI-Test",
                            "repo_name": "CumulusCI-Test",
                            "repo_owner": "SFDO-Tooling",
                            "subfolder": "src",
                        }
                    ],
                    "security_type": "FULL",
                },
                "checks": [],
            },
        },
    ] == steps
