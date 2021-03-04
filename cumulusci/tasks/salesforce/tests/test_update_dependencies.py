import io
from unittest import mock
import unittest
import zipfile

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.flowrunner import StepSpec
from cumulusci.tasks.salesforce.update_dependencies import UpdateDependencies
from cumulusci.tests.util import create_project_config
from .util import create_task


PROJECT_DEPENDENCIES = [
    {
        "zip_url": "http://zipurl",
        "subfolder": "src",
        "namespace_tokenize": "ns",
        "namespace_inject": "ns",
        "namespace_strip": "ns",
        "dependencies": [
            {"namespace": "upgradeddep", "version": "1.1"},
            {"namespace": "samedep", "version": "1.0"},
            {"namespace": "downgradeddep", "version": "1.0"},
            {"namespace": "newdep", "version": "1.0"},
            {
                "repo_owner": "TestOwner",
                "repo_name": "TestRepo",
                "subfolder": "subfolder",
                "ref": "ref",
            },
        ],
    },
    {
        "namespace": "dependsonupgradedbeta",
        "version": "1.0",
        "dependencies": [{"namespace": "upgradedbeta", "version": "1.0 (Beta 2)"}],
    },
]

INSTALLED_PACKAGES = {
    "upgradeddep": "1.0",
    "samedep": "1.0",
    "downgradeddep": "1.1",
    "removeddep": "1.0",
    "upgradedbeta": "1.0 (Beta 1)",
    "dependsonupgradedbeta": "1.0",
}


def make_fake_zipfile(*args, **kw):
    return zipfile.ZipFile(io.BytesIO(), "w")


class TestUpdateDependencies(unittest.TestCase):
    def test_init_options_base(self):
        pass

    def test_init_options_requires_dependencies(self):
        pass

    def test_init_options_warns_deprecated_options(self):
        pass

    def test_init_options_error_bad_ignore_dependencies(self):
        pass

    def test_init_options_removes_beta_resolver_for_include_beta_false(self):
        pass

    def test_init_options_removes_2gp_resolver_for_prefer_2gp_false(self):
        pass

    def test_init_options_removes_unsafe_resolvers_persistent_org(self):
        pass

    def test_run_task_gets_static_dependencies_and_installs(self):
        pass

    def test_install_dependency_installs_managed_package(self):
        pass

    def test_install_dependency_no_op_already_installed(self):
        pass

    def test_install_dependency_installs_unmanaged(self):
        pass

    def test_freeze(self):
        pass

    def test_run_task__bad_security_type(self):
        project_config = create_project_config()
        project_config.config["project"]["dependencies"] = PROJECT_DEPENDENCIES
        with self.assertRaises(TaskOptionsError):
            create_task(
                UpdateDependencies,
                {"security_type": "BOGUS"},
                project_config,
                mock.Mock(),
            )

    def test_run_task__bad_ignore_dependencies(self):
        project_config = create_project_config()
        project_config.config["project"]["dependencies"] = PROJECT_DEPENDENCIES
        with self.assertRaises(TaskOptionsError):
            create_task(
                UpdateDependencies,
                {"ignore_dependencies": [{"version": "1.3"}, {"namespace": "foo"}]},
                project_config,
                mock.Mock(),
            )

    def test_freeze(self):
        task = create_task(
            UpdateDependencies,
            {
                "dependencies": [
                    {
                        "name": "Install Test Product",
                        "namespace": "ns",
                        "version": "1.0",
                    },
                    {
                        "repo_owner": "SFDO-Tooling",
                        "repo_name": "CumulusCI-Test",
                        "ref": "abcdef",
                        "subfolder": "src",
                    },
                ]
            },
        )
        step = StepSpec(1, "test_task", task.task_config, None, task.project_config)
        steps = task.freeze(step)
        self.maxDiff = None
        self.assertEqual(
            [
                {
                    "is_required": True,
                    "kind": "managed",
                    "name": "Install Test Product",
                    "path": "test_task.1",
                    "step_num": "1.1",
                    "source": None,
                    "task_class": None,
                    "task_config": {
                        "options": {
                            "dependencies": [{"namespace": "ns", "version": "1.0"}],
                            "include_beta": False,
                            "prefer_2gp_from_release_branch": False,
                            "purge_on_delete": True,
                            "allow_newer": True,
                            "allow_uninstalls": False,
                            "security_type": "FULL",
                        },
                        "checks": [],
                    },
                },
                {
                    "is_required": True,
                    "kind": "metadata",
                    "name": "Deploy src",
                    "path": "test_task.2",
                    "step_num": "1.2",
                    "source": None,
                    "task_class": None,
                    "task_config": {
                        "options": {
                            "dependencies": [
                                {
                                    "ref": "abcdef",
                                    "repo_name": "CumulusCI-Test",
                                    "repo_owner": "SFDO-Tooling",
                                    "subfolder": "src",
                                }
                            ],
                            "include_beta": False,
                            "prefer_2gp_from_release_branch": False,
                            "purge_on_delete": True,
                            "allow_newer": True,
                            "allow_uninstalls": False,
                            "security_type": "FULL",
                        },
                        "checks": [],
                    },
                },
            ],
            steps,
        )
