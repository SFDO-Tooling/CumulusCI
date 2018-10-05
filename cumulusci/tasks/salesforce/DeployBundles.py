import os

from cumulusci.tasks.salesforce import Deploy


deploy_options = Deploy.task_options.copy()
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
