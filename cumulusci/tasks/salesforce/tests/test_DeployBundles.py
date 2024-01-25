import os
from unittest import mock

from cumulusci.core.flowrunner import StepSpec
from cumulusci.tasks.salesforce import DeployBundles
from cumulusci.utils import temporary_dir

from .util import create_task


class TestDeployBundles:
    def test_run_task(self):
        with temporary_dir() as path:
            os.mkdir("src")
            with open(os.path.join(path, "file"), "w"):
                pass
            task = create_task(DeployBundles, {"path": path})
            task._get_api = mock.Mock()
            task()
            task._get_api.assert_called_once()

    def test_run_task__path_not_found(self):
        with temporary_dir() as path:
            pass
        task = create_task(DeployBundles, {"path": path})
        task._get_api = mock.Mock()
        task()
        task._get_api.assert_not_called()

    def test_freeze(self):
        self.maxDiff = None
        with temporary_dir() as path:
            os.mkdir(".git")
            os.makedirs("unpackaged/test")
            task = create_task(DeployBundles, {"path": path + "/unpackaged"})
            step = StepSpec(
                step_num=1,
                task_name="deploy_bundles",
                task_config=task.task_config,
                task_class=None,
                project_config=task.project_config,
            )

            steps = task.freeze(step)
            print(steps)
            assert [
                {
                    "is_required": True,
                    "kind": "metadata",
                    "name": "Deploy unpackaged/test",
                    "path": "deploy_bundles.test",
                    "source": None,
                    "step_num": "1.1",
                    "task_class": "cumulusci.tasks.salesforce.UpdateDependencies",
                    "task_config": {
                        "options": {
                            "dependencies": [
                                {
                                    "ref": task.project_config.repo_commit,
                                    "github": "https://github.com/TestOwner/TestRepo",
                                    "subfolder": "unpackaged/test",
                                    "collision_check": False,
                                    "namespace_inject": None,
                                }
                            ]
                        },
                        "checks": [],
                    },
                }
            ] == steps

    def test_freeze__bad_path(self):
        task = create_task(DeployBundles, {"path": "/bogus"})
        step = StepSpec(1, "deploy_bundles", task.task_config, None, None)
        steps = task.freeze(step)
        assert [] == steps
