import io
import logging
import zipfile
from unittest import mock

import pydantic
import pytest

from cumulusci.core.dependencies.dependencies import (
    GitHubDynamicDependency,
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
    UnmanagedGitHubRefDependency,
)
from cumulusci.core.dependencies.resolvers import (
    DependencyResolutionStrategy,
    get_resolver_stack,
)
from cumulusci.core.exceptions import (
    CumulusCIException,
    DependencyParseError,
    TaskOptionsError,
)
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
        PackageNamespaceVersionDependency(namespace="ns", version="1.0"),
        PackageVersionIdDependency(version_id="04t000000000000"),
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


def test_init_options_uses_include_beta_strategy_for_include_beta_true():
    org_config = mock.Mock()
    org_config.scratch = True

    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "namespace": "ns",
                    "version": "1.0",
                }
            ],
            "include_beta": True,
            "resolution_strategy": "production",
        },
        org_config=org_config,
    )

    assert DependencyResolutionStrategy.BETA_RELEASE_TAG in task.resolution_strategy


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

    assert DependencyResolutionStrategy.BETA_RELEASE_TAG not in task.resolution_strategy


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
        DependencyResolutionStrategy.COMMIT_STATUS_RELEASE_BRANCH
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

    assert DependencyResolutionStrategy.BETA_RELEASE_TAG not in task.resolution_strategy
    assert (
        DependencyResolutionStrategy.COMMIT_STATUS_RELEASE_BRANCH
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
            mock.call(PackageNamespaceVersionDependency(namespace="ns", version="1.0")),
            mock.call(PackageVersionIdDependency(version_id="04t000000000000")),
        ]
    )


@mock.patch("cumulusci.tasks.salesforce.update_dependencies.click.confirm")
def test_run_task_gets_static_dependencies_and_installs__interactive(confirm):
    confirm.return_value = True

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
            "interactive": True,
        },
    )

    task._install_dependency = mock.Mock()
    task()

    task._install_dependency.assert_has_calls(
        [
            mock.call(PackageNamespaceVersionDependency(namespace="ns", version="1.0")),
            mock.call(PackageVersionIdDependency(version_id="04t000000000000")),
        ]
    )

    with pytest.raises(CumulusCIException) as e:
        task._install_dependency.reset_mock()
        confirm.return_value = False
        task()

    task._install_dependency.assert_not_called()
    assert "canceled" in str(e)


def test_run_task_gets_static_dependencies_and_installs__packages_only():
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [
                {
                    "namespace": "ns",
                    "version": "1.0",
                },
                {
                    "github": "https://github.com/TestRepo/Test",
                    "ref": "aaaa",
                    "subfolder": "foo",
                },
            ],
            "resolution_strategy": "production",
            "security_type": "PUSH",
            "packages_only": True,
        },
    )

    task._install_dependency = mock.Mock()
    task()

    assert task._install_dependency.call_count == 1
    task._install_dependency.assert_has_calls(
        [
            mock.call(PackageNamespaceVersionDependency(namespace="ns", version="1.0")),
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


@mock.patch(
    "cumulusci.core.dependencies.dependencies.install_package_by_namespace_version"
)
def test_install_dependency_installs_managed_package(
    install_package_by_namespace_version,
):
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
    install_package_by_namespace_version.assert_called_once_with(
        task.project_config,
        task.org_config,
        "ns",
        "1.0",
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


@mock.patch("cumulusci.tasks.salesforce.update_dependencies.get_static_dependencies")
def test_freeze(get_static_dependencies):
    get_static_dependencies.return_value = [
        PackageNamespaceVersionDependency(namespace="ns", version="1.0"),
        UnmanagedGitHubRefDependency(
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
                    "packages_only": False,
                    "interactive": False,
                    "base_package_url_format": "{}",
                },
                "checks": [],
            },
        },
        {
            "is_required": True,
            "kind": "metadata",
            "name": "Deploy https://github.com/SFDO-Tooling/CumulusCI-Test",
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
                            "subfolder": "src",
                        },
                    ],
                    "packages_only": False,
                    "interactive": False,
                    "base_package_url_format": "{}",
                },
                "checks": [],
            },
        },
    ] == steps


@mock.patch("cumulusci.tasks.salesforce.update_dependencies.get_static_dependencies")
def test_freeze__packages_only(get_static_dependencies):
    get_static_dependencies.return_value = [
        PackageNamespaceVersionDependency(namespace="ns", version="1.0"),
        UnmanagedGitHubRefDependency(
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
            ],
            "packages_only": True,
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
                    "packages_only": True,
                    "interactive": False,
                    "base_package_url_format": "{}",
                },
                "checks": [],
            },
        }
    ] == steps


def test_freeze__interactive_exception():
    task = create_task(
        UpdateDependencies,
        {
            "dependencies": [],
            "interactive": True,
        },
    )
    step = StepSpec(1, "test_task", task.task_config, None, task.project_config)
    with pytest.raises(CumulusCIException) as e:
        task.freeze(step)

    assert "cannot be frozen" in str(e)
