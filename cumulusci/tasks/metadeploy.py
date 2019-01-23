import json
import requests

from cumulusci.core.tasks import BaseTask
from cumulusci.core.flowrunner import FlowCoordinator


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
        label = self.project_config.get_version_for_tag(tag)
        # @@@ handle checkout/publish from a release tag instead of current commit
        steps = self._freeze_steps()

        # create version (not listed yet)
        product_url = self.base_url + "/products/{}".format(self.options["product_id"])
        version = self._call_api(
            "POST",
            "/versions",
            json={
                "product": product_url,
                "label": label,
                "description": tag,  # @@@ make it not required
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
        # @@@ link to metadeploy frontend

    def _freeze_steps(self):
        flow_name = self.options["flow"]
        flow_config = self.project_config.get_flow(flow_name)
        flow = FlowCoordinator(self.project_config, flow_config, name=flow_name)
        return [
            {
                "name": step.task_name,
                "is_required": True,
                "path": step.path,
                "step_num": str(step.step_num),
                "task_class": ".".join(
                    [step.task_class.__module__, step.task_class.__name__]
                ),
                "task_config": json.dumps(step.task_config),
                # @@@ `kind`
            }
            for step in flow.steps
        ]
        # @@@ Decompose update_dependencies/deploy_pre/deploy_post
