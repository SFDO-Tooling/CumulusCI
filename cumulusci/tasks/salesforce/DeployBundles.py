import copy
import os

from cumulusci.tasks.salesforce import Deploy


deploy_options = copy.deepcopy(Deploy.task_options)
deploy_options["path"][
    "description"
] = "The path to the parent directory containing the metadata bundles directories"


class DeployBundles(Deploy):
    task_options = deploy_options

    def _run_task(self):
        path = self.options["path"]
        pwd = os.getcwd()

        path = os.path.join(pwd, path)

        self.logger.info("Deploying all metadata bundles in path {}".format(path))

        if not os.path.isdir(path):
            self.logger.warning("Path {} not found, skipping".format(path))
            return

        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if not os.path.isdir(item_path):
                continue

            self.logger.info(
                "Deploying bundle: {}/{}".format(self.options["path"], item)
            )

            self._deploy_bundle(item_path)

    def _deploy_bundle(self, path):
        api = self._get_api(path)
        return api()

    def freeze(self, step):
        ui_options = self.task_config.config.get("ui_options", {})
        path = self.options["path"]
        if not os.path.isdir(path):
            return []
        steps = []
        for i, item in enumerate(sorted(os.listdir(path)), 1):
            if not os.path.isdir(os.path.join(path, item)):
                continue
            name = os.path.basename(item)
            subpath = os.path.relpath(
                os.path.join(os.path.realpath(path), item),
                os.path.realpath(self.project_config.repo_root),
            ).replace(os.sep, "/")
            dependency = self.options.copy()
            dependency.pop("path")
            dependency.update(
                {
                    "repo_owner": self.project_config.repo_owner,
                    "repo_name": self.project_config.repo_name,
                    "ref": self.project_config.repo_commit,
                    "subfolder": subpath,
                }
            )
            task_config = {
                "options": {"dependencies": [dependency]},
                "checks": self.task_config.checks or [],
            }
            ui_step = {
                "name": "Deploy {}".format(subpath),
                "kind": "metadata",
                "is_required": True,
            }
            ui_step.update(ui_options.get(name, {}))
            ui_step.update(
                {
                    "path": "{}.{}".format(step.path, name),
                    "step_num": "{}.{}".format(step.step_num, i),
                    "task_class": "cumulusci.tasks.salesforce.UpdateDependencies",
                    "task_config": task_config,
                    "source": step.project_config.source.frozenspec,
                }
            )
            steps.append(ui_step)
        return steps
