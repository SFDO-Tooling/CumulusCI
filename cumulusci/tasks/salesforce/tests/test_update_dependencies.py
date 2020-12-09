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
    @mock.patch(
        "cumulusci.salesforce_api.metadata.ApiRetrieveInstalledPackages.__call__"
    )
    def test_run_task(self, ApiRetrieveInstalledPackages):
        project_config = create_project_config()
        project_config.get_github_api = mock.Mock()
        project_config.config["project"]["dependencies"] = PROJECT_DEPENDENCIES
        # Default options: allow_newer=True, allow_uninstalls=False
        task = create_task(UpdateDependencies, project_config=project_config)
        ApiRetrieveInstalledPackages.return_value = INSTALLED_PACKAGES
        task.api_class = mock.Mock()
        task._download_extract_github = make_fake_zipfile
        task._download_extract_zip = make_fake_zipfile
        # Beta needs to be uninstalled to upgrade, but uninstalls are not allowed
        with self.assertRaises(TaskOptionsError):
            task()

    @mock.patch(
        "cumulusci.salesforce_api.metadata.ApiRetrieveInstalledPackages.__call__"
    )
    def test_run_task_downgrade_allowed(self, ApiRetrieveInstalledPackages):
        project_config = create_project_config()
        project_config.get_github_api = mock.Mock()
        project_config.config["project"]["dependencies"] = PROJECT_DEPENDENCIES
        task = create_task(
            UpdateDependencies,
            {"allow_newer": False, "allow_uninstalls": True},
            project_config=project_config,
        )
        task.org_config._installed_packages = {}
        ApiRetrieveInstalledPackages.return_value = INSTALLED_PACKAGES
        task.api_class = mock.Mock()
        task._download_extract_github = make_fake_zipfile
        task._download_extract_zip = make_fake_zipfile
        task()
        self.assertEqual(
            [
                {"version": "1.1", "namespace": "upgradeddep"},
                {"version": "1.0", "namespace": "downgradeddep"},
                {"version": "1.0", "namespace": "newdep"},
                {
                    "repo_owner": "TestOwner",
                    "repo_name": "TestRepo",
                    "subfolder": "subfolder",
                    "ref": "ref",
                },
                {
                    "dependencies": [
                        {"version": "1.1", "namespace": "upgradeddep"},
                        {"version": "1.0", "namespace": "samedep"},
                        {"version": "1.0", "namespace": "downgradeddep"},
                        {"version": "1.0", "namespace": "newdep"},
                        {
                            "repo_owner": "TestOwner",
                            "repo_name": "TestRepo",
                            "subfolder": "subfolder",
                            "ref": "ref",
                        },
                    ],
                    "zip_url": "http://zipurl",
                    "subfolder": "src",
                    "namespace_tokenize": "ns",
                    "namespace_inject": "ns",
                    "namespace_strip": "ns",
                },
                {"version": "1.0 (Beta 2)", "namespace": "upgradedbeta"},
                {
                    "version": "1.0",
                    "namespace": "dependsonupgradedbeta",
                    "dependencies": [
                        {"version": "1.0 (Beta 2)", "namespace": "upgradedbeta"}
                    ],
                },
            ],
            task.install_queue,
        )
        self.assertEqual(
            [
                {
                    "version": "1.0",
                    "namespace": "dependsonupgradedbeta",
                    "dependencies": [
                        {"version": "1.0 (Beta 2)", "namespace": "upgradedbeta"}
                    ],
                },
                {"version": "1.0 (Beta 2)", "namespace": "upgradedbeta"},
                {"version": "1.0", "namespace": "downgradeddep"},
            ],
            task.uninstall_queue,
        )
        self.assertEqual(10, task.api_class.call_count)

    @mock.patch(
        "cumulusci.salesforce_api.metadata.ApiRetrieveInstalledPackages.__call__"
    )
    def test_run_task_downgrade_unneeded(self, ApiRetrieveInstalledPackages):
        project_config = create_project_config()
        project_config.get_github_api = mock.Mock()
        project_config.config["project"]["dependencies"] = (
            {"namespace": "package", "version": "1.0"},
        )

        task = create_task(
            UpdateDependencies,
            {"allow_newer": True, "allow_uninstalls": True},
            project_config=project_config,
        )
        ApiRetrieveInstalledPackages.return_value = {"package": "1.1"}

        task.api_class = mock.Mock()
        task._download_extract_github = make_fake_zipfile
        task._download_extract_zip = make_fake_zipfile
        task()
        self.assertEqual([], task.install_queue)
        self.assertEqual([], task.uninstall_queue)

    @mock.patch(
        "cumulusci.salesforce_api.metadata.ApiRetrieveInstalledPackages.__call__"
    )
    def test_run_task_downgrade_disallowed(self, ApiRetrieveInstalledPackages):
        project_config = create_project_config()
        project_config.get_github_api = mock.Mock()
        project_config.config["project"]["dependencies"] = (
            {"namespace": "package", "version": "1.0"},
        )

        task = create_task(
            UpdateDependencies,
            {"allow_newer": False, "allow_uninstalls": False},
            project_config=project_config,
        )
        ApiRetrieveInstalledPackages.return_value = {"package": "1.1"}

        task.api_class = mock.Mock()
        task._download_extract_github = make_fake_zipfile
        task._download_extract_zip = make_fake_zipfile
        with self.assertRaises(TaskOptionsError):
            task()

    def test_run_task__no_dependencies(self):
        task = create_task(UpdateDependencies)
        api = mock.Mock()
        task.api_class = mock.Mock(return_value=api)
        task()
        api.assert_not_called()

    @mock.patch(
        "cumulusci.salesforce_api.metadata.ApiRetrieveInstalledPackages.__call__"
    )
    def test_run_task__duplicate_dependencies(self, ApiRetrieveInstalledPackages):
        project_config = create_project_config()
        project_config.config["project"]["dependencies"] = (
            {"namespace": "package", "version": "1.0"},
        )
        project_config.get_github_api = mock.Mock()
        project_config.get_static_dependencies = mock.Mock()
        project_config.get_static_dependencies.return_value = [
            {
                "namespace": "dep1",
                "version": "1.1",
                "dependencies": [{"namespace": "dep2", "version": "1.1"}],
            },
            {"namespace": "dep2", "version": "1.1"},
        ]
        task = create_task(UpdateDependencies, project_config=project_config)
        ApiRetrieveInstalledPackages.return_value = INSTALLED_PACKAGES
        task.org_config.reset_installed_packages = mock.Mock()
        task._uninstall_dependencies = mock.Mock()
        task._install_dependencies = mock.Mock()

        task()

        assert task.install_queue == [
            {"namespace": "dep2", "version": "1.1"},
            {
                "dependencies": [{"namespace": "dep2", "version": "1.1"}],
                "namespace": "dep1",
                "version": "1.1",
            },
        ]

    def test_init_options__include_beta_with_persistent_org(self):
        project_config = create_project_config()
        project_config.config["project"]["dependencies"] = [{"namespace": "foo"}]
        org_config = mock.Mock(scratch=False)
        task = create_task(
            UpdateDependencies,
            {"include_beta": True},
            project_config=project_config,
            org_config=org_config,
        )
        assert not task.options["include_beta"]

    def test_dependency_no_package_zip(self):
        project_config = create_project_config()
        project_config.config["project"]["dependencies"] = [{"foo": "bar"}]
        task = create_task(UpdateDependencies, project_config=project_config)
        task.org_config = mock.Mock()
        task.org_config.save_if_changed.return_value.__enter__ = lambda *args: ...
        task.org_config.save_if_changed.return_value.__exit__ = lambda *args: ...

        with self.assertRaises(TaskOptionsError) as e:
            task()
        assert "Could not find package for" in str(e.exception)

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

    def test_run_task__metadata_bundle(self):
        project_config = create_project_config()
        project_config.get_github_api = mock.Mock()
        task = create_task(
            UpdateDependencies,
            {
                "dependencies": [
                    {
                        "repo_owner": "SFDO-Tooling",
                        "repo_name": "CumulusCI-Test",
                        "ref": "abcdef",
                        "subfolder": "src",
                        "namespace_tokenize": "ns",
                    }
                ]
            },
            project_config=project_config,
        )
        task._download_extract_github = make_fake_zipfile
        api = mock.Mock()
        task.api_class = mock.Mock(return_value=api)
        task()
        self.assertEqual(
            [
                {
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "abcdef",
                    "subfolder": "src",
                    "namespace_tokenize": "ns",
                }
            ],
            task.install_queue,
        )
        api.assert_called_once()

    def test_run_task__version_id(self):
        project_config = create_project_config()
        project_config.get_github_api = mock.Mock()
        task = create_task(
            UpdateDependencies,
            {"dependencies": [{"version_id": "04t"}]},
            project_config=project_config,
        )
        with mock.patch(
            "cumulusci.tasks.salesforce.update_dependencies.install_package_version"
        ) as api:
            task()
        api.assert_called_once()

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

    def test_flatten(self):
        dependencies = [
            {"namespace": "npe02", "dependencies": [{"namespace": "npe01"}]},
            {"namespace": "npe01"},
        ]
        task = create_task(UpdateDependencies)
        result = task._flatten(dependencies)
        self.assertEqual([{"namespace": "npe01"}, {"namespace": "npe02"}], result)
