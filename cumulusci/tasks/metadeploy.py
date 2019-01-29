import json
import requests

from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.tasks import BaseTask
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.utils import download_extract_github
from cumulusci.utils import temporary_dir


class BaseMetaDeployTask(BaseTask):
    """Base class for tasks that talk to MetaDeploy's API."""

    def _init_task(self):
        metadeploy_service = self.project_config.keychain.get_service("metadeploy")
        self.base_url = metadeploy_service.url
        self.api = requests.Session()
        self.api.headers["Authorization"] = "token {}".format(metadeploy_service.token)

    def _call_api(self, method, path, collect_pages=False, **kwargs):
        next_url = self.base_url + path
        results = []
        while next_url is not None:
            response = self.api.request(method, next_url, **kwargs)
            if response.status_code == 400:
                raise requests.exceptions.HTTPError(response.content)
            response.raise_for_status()
            response = response.json()
            if "links" in response and collect_pages:
                results.extend(response["data"])
                next_url = response["links"]["next"]
            else:
                return response
        return results


class Publish(BaseMetaDeployTask):
    """Publishes an installation plan to MetaDeploy.
    """

    task_options = {
        "flow": {"description": "Name of flow to publish", "required": True},
        "product_id": {
            "description": "Id of the product in MetaDeploy",
            "required": True,
        },
        "tag": {"description": "Name of git tag to publish", "required": True},
        "title": {"description": "Title of the installation plan.", "required": True},
        "description": {
            "description": "Description of the version.",
            "required": False,
        },
        "slug": {
            "description": "URL slug for the installation plan.",
            "required": True,
        },
        "tier": {
            "description": "UI tier of MetaDeploy plan (primary/secondary/additional)",
            "required": True,
        },
        "preflight_message": {
            "description": "Message displayed before installation (markdown)",
            "required": True,
        },
        "post_install_message": {
            "description": "Message displayed after installation (markdown)",
            "required": True,
        },
    }

    def _run_task(self):
        tag = self.options["tag"]

        repo_owner = self.project_config.repo_owner
        repo_name = self.project_config.repo_name
        gh = self.project_config.get_github_api()
        repo = gh.repository(repo_owner, repo_name)
        commit_sha = repo.ref("tags/{}".format(tag)).object.sha
        self.logger.info(
            "Downloading commit {} of {}/{} from GitHub".format(
                commit_sha, repo_owner, repo_name
            )
        )
        zf = download_extract_github(gh, repo_owner, repo_name, ref=commit_sha)
        with temporary_dir() as project_dir:
            zf.extractall(project_dir)
            project_config = BaseProjectConfig(
                self.project_config.global_config_obj,
                repo_info={
                    "root": project_dir,
                    "owner": repo_owner,
                    "name": repo_name,
                    "url": self.project_config.repo_url,
                    "branch": tag,
                    "commit": commit_sha,
                },
            )
            project_config.set_keychain(self.project_config.keychain)
            steps = self._freeze_steps(project_config)
        self.logger.debug("Publishing steps:\n", json.dumps(steps, indent=4))

        import pdb

        pdb.set_trace()
        # create version (not listed yet)
        product_url = self.base_url + "/products/{}".format(self.options["product_id"])
        label = self.project_config.get_version_for_tag(tag)
        version = self._call_api(
            "POST",
            "/versions",
            json={
                "product": product_url,
                "label": label,
                "description": self.options["description"],
                "is_production": True,
                "commit_ish": self.project_config.repo_commit,
                "is_listed": False,
            },
        )
        self.logger.info("Created {}".format(version["url"]))

        # create plan
        plan = self._call_api(
            "POST",
            "/plans",
            json={
                "title": self.options["title"],
                "version": version["url"],
                "preflight_message": self.options["preflight_message"],
                "tier": self.options["tier"],
                "post_install_message": self.options["post_install_message"],
                "steps": steps,
            },
        )
        self.logger.info("Created Plan {}".format(plan["url"]))

        # create plan slug
        planslug = self._call_api(
            "POST",
            "/planslug",
            json={"parent": plan["url"], "slug": self.options["slug"]},
        )
        self.logger.info("Created PlanSlug {}".format(planslug["url"]))

        # update version to set is_listed=True
        self._call_api(
            "PATCH", "/versions/{}".format(version["id"]), json={"is_listed": True}
        )
        self.logger.info("Published Version {}".format(version["url"]))

    def _freeze_steps(self, project_config):
        flow_name = self.options["flow"]
        flow_config = self.project_config.get_flow(flow_name)
        flow = FlowCoordinator(self.project_config, flow_config, name=flow_name)
        steps = []
        for step in flow.steps:
            task = step.task_class(
                project_config, TaskConfig(step.task_config), name=step.task_name
            )
            steps.extend(task.freeze(step))
        return steps
