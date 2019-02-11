import io
import mock
import unittest
import zipfile

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.flowrunner import StepSpec
from cumulusci.tasks.salesforce import UpdateDependencies
from cumulusci.tests.util import create_project_config
from .util import create_task


class TestUpdateDependencies(unittest.TestCase):
    @mock.patch(
        "cumulusci.salesforce_api.metadata.ApiRetrieveInstalledPackages.__call__"
    )
    def test_run_task(self, ApiRetrieveInstalledPackages):
        project_config = create_project_config()
        project_config.get_github_api = mock.Mock()
        project_config.config["project"]["dependencies"] = [
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
                "dependencies": [
                    {"namespace": "upgradedbeta", "version": "1.0 (Beta 2)"}
                ],
            },
        ]
        task = create_task(UpdateDependencies, project_config=project_config)
        ApiRetrieveInstalledPackages.return_value = {
            "upgradeddep": "1.0",
            "samedep": "1.0",
            "downgradeddep": "1.1",
            "removeddep": "1.0",
            "upgradedbeta": "1.0 (Beta 1)",
            "dependsonupgradedbeta": "1.0",
        }
        task.api_class = mock.Mock()
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        task._download_extract_github = mock.Mock(return_value=zf)
        task._download_extract_zip = mock.Mock(return_value=zf)
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

    def test_run_task__no_dependencies(self):
        task = create_task(UpdateDependencies)
        api = mock.Mock()
        task.api_class = mock.Mock(return_value=api)
        task()
        api.assert_not_called()

    def test_update_dependency_latest_option_err(self):
        project_config = create_project_config()
        project_config.config["project"]["dependencies"] = [{"namespace": "foo"}]
        task = create_task(UpdateDependencies, project_config=project_config)
        task.options["include_beta"] = True
        task.org_config = mock.Mock()

        with self.assertRaises(TaskOptionsError):
            task()

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
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        task._download_extract_github = mock.Mock(return_value=zf)
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
        step = StepSpec(1, "test_task", task.task_config, None)
        steps = task.freeze(step)
        self.assertEqual(
            [
                {
                    "is_required": True,
                    "kind": "managed",
                    "name": "Install Test Product",
                    "path": "test_task.1",
                    "step_num": "1.1",
                    "task_class": None,
                    "task_config": {
                        "options": {
                            "dependencies": [{"namespace": "ns", "version": "1.0"}],
                            "include_beta": False,
                            "namespaced_org": False,
                            "purge_on_delete": True,
                        }
                    },
                },
                {
                    "is_required": True,
                    "kind": "metadata",
                    "name": "Deploy src",
                    "path": "test_task.2",
                    "step_num": "1.2",
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
                            "namespaced_org": False,
                            "purge_on_delete": True,
                        }
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

    maxDiff = None
